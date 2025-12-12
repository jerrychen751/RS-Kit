"""Utilities for subsetting NASA Earthdata datasets."""

from __future__ import annotations

from typing import Iterable, Optional

import xarray as xr

from ...models.extents import SpatialExtent, TemporalExtent


def subset_dataset(
    dataset: xr.Dataset,
    spatial_extent: Optional[SpatialExtent],
    temporal_extent: Optional[TemporalExtent],
    *,
    drop_nan_lines: bool = True,
    lon_names: Iterable[str] = ("lon", "longitude"),
    lat_names: Iterable[str] = ("lat", "latitude"),
) -> xr.Dataset:
    """Subset dataset by spatial and temporal extents."""
    result = dataset

    if temporal_extent and "time" in result.coords:
        result = result.sel(
            time=slice(temporal_extent.start, temporal_extent.end)
        )

    if spatial_extent:
        lon_data = _select_coordinate(result, lon_names)
        lat_data = _select_coordinate(result, lat_names)

        if lon_data is not None and lat_data is not None:
            lon_mask = (lon_data >= spatial_extent.lon_min) & (
                lon_data <= spatial_extent.lon_max
            )
            lat_mask = (lat_data >= spatial_extent.lat_min) & (
                lat_data <= spatial_extent.lat_max
            )
            combined_mask = lon_mask & lat_mask

            result = result.where(combined_mask, drop=False)

            if drop_nan_lines and lat_data.dims:
                lat_dim = lat_data.dims[-1]
                if lat_dim in result.dims:
                    result = result.dropna(dim=lat_dim, how="all")

    return result


def _select_coordinate(
    dataset: xr.Dataset,
    candidates: Iterable[str],
) -> Optional[xr.DataArray]:
    for name in candidates:
        if name in dataset.coords:
            return dataset.coords[name]
        if name in dataset:
            return dataset[name]
    return None

