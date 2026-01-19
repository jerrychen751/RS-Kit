"""Utilities for subsetting NASA Earthdata datasets."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from datetime import timezone
import numpy as np
import numpy.typing as npt
import xarray as xr
import netCDF4 as nc
import cf_xarray as cf

from ...models.extents import SpatialExtent, TemporalExtent

Indexer = npt.NDArray[np.int_]
Indexers = dict[str, Indexer] # {dimension: Indexer}
SpatialMask = xr.DataArray

# TemporalExtent and SpatialExtent guarantee extent bounds are valid
@dataclass
class SubsettingParams:
    temporal: TemporalExtent
    spatial: SpatialExtent

# --- Subsetting and Downloads ---
def subset_granule(
    filepath: Path,
    params: SubsettingParams,
    variable_umms: list[dict[str, Any]],
    *,
    mask_out_of_bounds: bool = False,
) -> Path:
    """
    Subset a dataset file in place using SubsettingParams. Subsets data variables which have the same dimensions as spatial/temporal extents and leaving the rest of the data variables. Although spatial extents provided by SubsettingParams are from -180 to 180, the actual dataset will be returned using its original longitude convention.

    If mask_out_of_bounds is True, any out-of-bounds lon/lat cells are set to
    null after subsetting while preserving the 2D grid structure. Uses each
    variable's encoded _FillValue when present, otherwise falls back to NaN
    (or NaT for datetime/timedelta variables).
    """
    if not filepath.exists():
        raise FileNotFoundError(f"Dataset file not found: {filepath}")

    temp_path = filepath.with_name(f"{filepath.name}.subset.tmp")
    if temp_path.exists():
        temp_path.unlink()

    groups = _list_groups(filepath)

    # Validate that required coordinates exist in at some group
    has_lon = has_lat = has_time = False
    for gpath in groups:
        with xr.open_dataset(filepath, group=gpath) as ds:
            has_lon = has_lon or _find_coord(ds, "longitude", "lon", "longitude") is not None
            has_lat = has_lat or _find_coord(ds, "latitude", "lat", "latitude") is not None
            has_time = has_time or _find_coord(ds, "time", "time", "datetime") is not None
        if has_lon and has_lat and has_time:
            break

    if not has_lon:
        raise ValueError("Unable to find a lon or longitude data variable upon iterating through each group in dataset")
    if not has_lat:
        raise ValueError("Unable to find a lat or latitude data variable upon iterating through each group in dataset")
    if not has_time:
        raise ValueError("Unable to find a time data or datetime variable upon iterating through each group in dataset")

    # Ensure longitude runs from -180 to 180 for subsetting calculations
    lon_convention = _determine_lon_convention(variable_umms, filepath, groups)

    spatial_indexers: Indexers | None = None
    spatial_mask: SpatialMask | None = None
    if mask_out_of_bounds:
        for gpath in groups:
            with xr.open_dataset(filepath, group=gpath) as ds:
                lon = _find_coord(ds, "longitude", "lon", "longitude")
                lat = _find_coord(ds, "latitude", "lat", "latitude")
                if lon is None or lat is None:
                    continue
                lon_for_index = _convert_lon(lon, True) if lon_convention == "360" else lon
                spatial_indexers, spatial_mask = _build_spatial_indexer(lon_for_index, lat, params)
                break

    is_first = True # used when writing out to a file
    try:
        for gpath in groups:
            with xr.open_dataset(filepath, group=gpath) as ds:
                if mask_out_of_bounds and spatial_indexers is not None:
                    indexers: Indexers = {}
                    indexers = _merge_indexers(indexers, spatial_indexers)
                    time = _find_coord(ds, "time", "time", "datetime")
                    if time is not None:
                        indexers = _merge_indexers(indexers, _build_time_indexer(time, params))
                else:
                    indexers, spatial_mask = _build_indexers_for_group(
                        ds,
                        params,
                        lon_convention=lon_convention,
                    )

                # Applies indexer mapping across each xr.DataArray in container
                # Default behavior is to raise if some group doesn't contain dim
                subset = ds.isel(indexers, missing_dims='ignore') if indexers else ds
                if mask_out_of_bounds:
                    if spatial_mask is None:
                        print(f"[subset_granule] No spatial mask for group '{gpath}', skipping mask.")
                    else:
                        mask_indexers = {dim: idx for dim, idx in indexers.items() if dim in spatial_mask.dims}
                        mask_to_apply = spatial_mask
                        if mask_indexers:
                            mask_to_apply = spatial_mask.isel(mask_indexers)
                        print(
                            "[subset_granule] Applying spatial mask for group "
                            f"'{gpath}' dims={tuple(mask_to_apply.dims)}"
                        )
                        subset = _apply_spatial_mask(subset, ds, mask_to_apply)
                group = None if gpath in ('/', '') else gpath.lstrip('/')
                encoding = _build_encoding(ds, subset)
                subset.to_netcdf(
                    path=temp_path,
                    mode='w' if is_first else 'a',
                    group=group,
                    engine='netcdf4',
                    encoding=encoding,
                )
                is_first = False

        return temp_path.replace(filepath)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise

_NETCDF4_ENCODING_KEYS = {
    "szip_coding",
    "significant_digits",
    "shuffle",
    "contiguous",
    "fletcher32",
    "zlib",
    "chunksizes",
    "szip_pixels_per_block",
    "dtype",
    "blosc_shuffle",
    "least_significant_digit",
    "compression",
    "quantize_mode",
    "_FillValue",
    "complevel",
    "endian",
}

def _build_encoding(source: xr.Dataset, subset: xr.Dataset) -> dict[str, dict[str, Any]]:
    """
    Build the encoding to save/write the subsetted dataset back to original filepath. Preserves the original encodings wherever possible.

    Args:
        source: A dataset object without any groups from the original downloaded .nc file (base level).
        subset: A subsetted dataset object to be written back to disk.
    
    Returns:
        Mapping of variable names to their corresponding encoding dictionary.
    """
    encoding: dict[str, dict[str, Any]] = {}
    for name in subset.variables:
        enc = source[name].encoding.copy()
        enc = {key: value for key, value in enc.items() if key in _NETCDF4_ENCODING_KEYS}
        if "_FillValue" not in enc:
            subset_fill = subset[name].encoding.get("_FillValue")
            if subset_fill is not None:
                enc["_FillValue"] = subset_fill
        if "chunksizes" in enc:
            var = subset[name]
            chunks = enc.get("chunksizes")
            if not _is_valid_chunksizes(var, chunks):
                enc.pop("chunksizes", None)
        encoding[str(name)] = enc
    return encoding

def _is_valid_chunksizes(var: xr.Variable, chunks: Any) -> bool:
    if not isinstance(chunks, (tuple, list)):
        return False
    if len(chunks) != var.ndim:
        return False
    for idx, size in enumerate(chunks):
        if not isinstance(size, int) or size <= 0:
            return False
        dim_size = var.shape[idx]
        if dim_size is not None and size > dim_size:
            return False
    return True

# --- xr.Dataset Navigation ---
def _list_groups(filepath: Path) -> list[str]:
    """
    Recursively traverse a .nc dataset and return group paths.

    Args:
        filepath: Path to the NetCDF file to inspect.

    Returns:
        List of group names using a filepath-like form where "/" is the root.
    """
    groups: list[str] = []

    with nc.Dataset(filepath) as root:
        # Recursively walk through groups
        def dfs(ds: nc.Dataset) -> None:
            groups.append(ds.path)
            for child in ds.groups.values():
                dfs(child)
        
        dfs(root)

    return groups

def _require_1d_dim(coord: xr.DataArray, label: str) -> str:
    """
    Ensure an xr.DataArray is 1D and return its dimension name.
    
    Args:
        coord: Data array to check its number of dimensions.
        label: Name for the data array to return to caller when an error is raised. Does not have to be the name of the dimension.

    Returns:
        Dimension name for the data array.

    Raises:
        ValueError: If the data array is not 1D.
    """
    if coord.ndim != 1:
        raise ValueError(f"Expected {label} to have 1 dimension in dataset")
    return str(coord.dims[0])

def _require_coord(
    ds: xr.Dataset,
    cf_key: str,
    *names: str,
) -> xr.DataArray | None:
    """
    Return a coordinate xr.DataArray from cf_xarray or a list of fallback names. Computes and returns a copy from the lazily-loaded xr.Dataset

    Args:
        ds: Dataset to search.
        cf_key: CF coordinate key to resolve via cf_xarray (e.g., "longitude").
        *names: Fallback variable names to search with ds.get.

    Returns:
        Coordinate xr.DataArray matching the CF key or fallback names.

    Raises:
        ValueError: If no matching coordinate is found.
    """
    coord = _find_coord(ds, cf_key, *names)
    if coord is None:
        names_label = ", ".join((cf_key, *names))
        raise ValueError(
            f"Unable to find {cf_key} coordinate using cf key '{cf_key}' or names: {names_label}."
        )

    return coord.compute()

def _find_coord(
    ds: xr.Dataset,
    cf_key: str,
    *names: str,
) -> xr.DataArray | None:
    """
    Return a coordinate xr.DataArray from cf_xarray or a list of fallback names.

    Args:
        ds: Dataset to search.
        cf_key: CF coordinate key to resolve via cf_xarray (e.g., "longitude").
        *names: Fallback variable names to search with ds.get.

    Returns:
        Coordinate DataArray matching the CF key or fallback names, or None.
    """
    coord = ds.cf.get(cf_key)
    if coord is None:
        for name in names:
            coord = ds.get(name)
            if coord is not None:
                break

    return coord

# --- xr.Dataset Subsetting ---
def _build_indexers_for_group(
    ds: xr.Dataset,
    params: SubsettingParams,
    *,
    lon_convention: Literal["180", "360"],
) -> tuple[Indexers, SpatialMask | None]:
    """
    Build indexers for a group dataset, skipping missing coordinates.

    Args:
        ds: Dataset to subset.
        params: Subsetting parameters including spatial and temporal extents.
        lon_convention: Longitude convention for the dataset (180 or 360).

    Returns:
        Tuple of (indexers, spatial mask). The spatial mask is None if lon/lat
        are missing in the group.
    """
    indexers: Indexers = {}
    spatial_mask: SpatialMask | None = None
    lon = _find_coord(ds, "longitude", "lon", "longitude")
    lat = _find_coord(ds, "latitude", "lat", "latitude")
    if lon is not None and lat is not None:
        lon_for_index = _convert_lon(lon, True) if lon_convention == "360" else lon
        spatial_indexers, spatial_mask = _build_spatial_indexer(lon_for_index, lat, params)
        indexers = _merge_indexers(indexers, spatial_indexers)
    time = _find_coord(ds, "time", "time", "datetime")
    if time is not None:
        indexers = _merge_indexers(indexers, _build_time_indexer(time, params))
    return indexers, spatial_mask

def _merge_indexers(base: Indexers, new: Indexers) -> Indexers:
    """Merge two indexers by dimension name, taking the intersection the two if they share the same dimension."""
    merged: Indexers = base
    for dim, idx in new.items():
        if dim not in merged:
            merged[dim] = idx
        else:
            merged[dim] = np.intersect1d(merged[dim], idx)

    return merged

def _build_time_indexer(
    time: xr.DataArray,
    params: SubsettingParams,
) -> Indexers:
    """
    Build the time indexer for .isel() based on the requested temporal extent.

    Args:
        time: Time coordinate DataArray.
        params: Subsetting parameters containing the requested temporal extent.

    Returns:
        Mapping of time dimension name to a slice or integer index array.

    Raises:
        ValueError: If the time coordinate is not 1D or not datetime-like.
    """
    t_dim = _require_1d_dim(time, "time")

    t_vals = time.to_numpy() # 1D array
    if not np.issubdtype(t_vals.dtype, np.datetime64):
        raise ValueError("Cannot process a time DataArray which is not of type datetime")

    t_start, t_end = np.datetime64(params.temporal.start.astimezone(timezone.utc).replace(tzinfo=None)), np.datetime64(params.temporal.end.astimezone(timezone.utc).replace(tzinfo=None))
    mask = (t_vals >= t_start) & (t_vals <= t_end)
    idx_to_keep = np.where(mask)[0].astype(np.int64) # .where() returns tuple of arrays, one array per dimension

    return {t_dim: idx_to_keep}

def _build_spatial_indexer(
    lon: xr.DataArray,
    lat: xr.DataArray,
    params: SubsettingParams,
) -> tuple[Indexers, SpatialMask]:
    """
    Build spatial indexers for .isel() using the requested spatial extent.

    Args:
        lon: Longitude coordinate DataArray (assumed -180 to 180 convention).
        lat: Latitude coordinate DataArray.
        params: Subsetting parameters containing the requested spatial extent.

    Returns:
        Tuple of (indexers, spatial mask).

    Raises:
        ValueError: If lon/lat are not numeric or mask is not 1D/2D.
    """
    if not np.issubdtype(lon.dtype, np.number):
        raise ValueError("Cannot process a lon DataArray which does not contain numerical data types")
    if not np.issubdtype(lat.dtype, np.number):
        raise ValueError("Cannot process a lat DataArray which does not contain numerical data types")

    lon_start, lon_end = params.spatial.lon_min, params.spatial.lon_max
    lat_start, lat_end = params.spatial.lat_min, params.spatial.lat_max
    lon_mask = (lon >= lon_start) & (lon <= lon_end)
    lat_mask = (lat >= lat_start) & (lat <= lat_end)
    try:
        mask = lon_mask & lat_mask
    except Exception:
        raise ValueError("Longitude and latitude do not have the same dimensions.")

    if mask is None or mask.ndim < 1:
        raise ValueError("Longitude/latitude must have at least one dimension")
    if mask.ndim > 2:
        raise ValueError("Longitude/latitude must be 1D or 2D")

    dims = tuple(str(dim) for dim in mask.dims)
    mask_vals = mask.to_numpy()

    if mask.ndim == 1:
        idx_to_keep = np.where(mask_vals)[0].astype(np.int64)
        return {dims[0]: idx_to_keep}, mask

    indexers: Indexers = {}
    for axis, dim in enumerate(dims):
        other_axes = tuple(idx for idx in range(mask_vals.ndim) if idx != axis)
        idx_to_keep = np.where(mask_vals.any(axis=other_axes))[0].astype(np.int64)
        indexers[dim] = idx_to_keep

    return indexers, mask


def _apply_spatial_mask(
    subset: xr.Dataset,
    source: xr.Dataset,
    spatial_mask: SpatialMask,
) -> xr.Dataset:
    """
    Used to convert out-of-bounds values into either their specified encoding _FillValue or into NaN/NaT.
    """
    masked = subset.copy()
    mask_dims = set(spatial_mask.dims)
    for name, var in subset.variables.items():
        if not mask_dims.issubset(var.dims):
            continue
        fill_value = source[name].encoding.get("_FillValue")
        if fill_value is None:
            fill_value = _default_fill_value(var) # type: ignore
        masked_var = var.where(spatial_mask, other=fill_value)
        if source[name].encoding.get("_FillValue") is None and _should_set_fill_value(var, fill_value):
            masked_var.encoding["_FillValue"] = fill_value
        if name in subset.coords:
            masked = masked.assign_coords({name: masked_var})
        else:
            masked[name] = masked_var
    return masked


def _default_fill_value(var: xr.DataArray) -> Any:
    if np.issubdtype(var.dtype, np.datetime64):
        return np.datetime64("NaT")
    if np.issubdtype(var.dtype, np.timedelta64):
        return np.timedelta64("NaT")
    if np.issubdtype(var.dtype, np.bool_):
        return False
    if np.issubdtype(var.dtype, np.integer):
        return np.iinfo(var.dtype).min
    return np.nan


def _should_set_fill_value(var: xr.DataArray, fill_value: Any) -> bool:
    if np.issubdtype(var.dtype, np.integer) and not np.issubdtype(var.dtype, np.bool_):
        return True
    return False

# --- Spatial and Temporal Extent Helpers ---
def _determine_lon_convention(
    variable_umms: list[dict[str, Any]], 
    filepath: Path, 
    groups: list[str]
) -> Literal['180'] | Literal['360']:
    """
    Determine whether a dataset uses -180 to 180 or 0 to 360 longitude convention.

    The function first searches the CMR variable UMM metadata for a longitude
    variable and its ValidRanges. If that fails, it inspects the dataset’s
    groups, looking for a longitude coordinate and infers its range from
    attributes or from the data values.

    Args:
        variable_umms: List of CMR variable UMM dicts to inspect for longitude
            metadata (e.g., Name, ValidRanges).
        filepath: Path to the NetCDF file to inspect when UMM metadata is absent.
        groups: List of NetCDF group paths to search for longitude coordinates.

    Returns:
        '180' if the inferred longitude range is centered around -180 to 180,
        otherwise '360' for 0 to 360.

    Raises:
        ValueError: If the longitude convention cannot be determined from UMM
            metadata or dataset inspection.
    """    
    lon_umm = None
    for umm in variable_umms:
        name = umm.get("Name")
        if not name:
            continue
        normalized_name = name.split("/")[-1].lower().strip()
        if normalized_name in ("lon", "longitude"):
            lon_umm = umm
            break

    lon_min: float | None = None
    lon_max: float | None = None
    if lon_umm is not None: # use variable umm
        ranges: list[dict[str, float]] | None = lon_umm.get("ValidRanges")
        if ranges is not None and isinstance(ranges, list) and len(ranges) > 0:
            lon_min = ranges[0].get("Min")
            lon_max = ranges[0].get("Max")
    else: # check dataset metadata
        for gpath in groups:
            with xr.open_dataset(filepath, group=gpath) as ds:
                try:
                    lon = _require_coord(ds, "longitude", "lon", "longitude")
                except ValueError:
                    lon = None

                if lon is None:
                    continue

                if lon.attrs:
                    lon_min = lon.attrs.get("valid_min")
                    lon_max = lon.attrs.get("valid_max")
                else:
                    lon_min = float(lon.min().compute())
                    lon_max = float(lon.max().compute())

            if lon_min is not None and lon_max is not None:
                break
    
    if lon_min is None or lon_max is None:
        raise NotImplementedError("Unable to determine the longitude conventions for this dataset using NASA CMR API's UMM or through inspection of the dataset's groups' data variables.")

    if lon_min < 0 and lon_max < 180:
        return '180'
    else:
        return '360'

def _convert_lon(lon: xr.DataArray, to_180: bool) -> xr.DataArray:
    """
    Convert longitude values between 0..360 and -180..180 conventions.

    Args:
        lon: Longitude coordinate values to convert.
        to_180: True to convert to -180..180, False to convert to 0..360.

    Returns:
        Converted longitude DataArray.
    """
    if to_180:
        return ((lon + 180) % 360) - 180
    else: # to 360
        return lon % 360
