from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import xarray as xr

from ...auth.credential_manager import CredentialManager
from ...contracts.plugin import DataSourcePlugin
from ...core.query import Query
from ...utils.downloads import ensure_downloads_directory
from .cmr import CmrClient
from .harmony import HarmonyClient, HarmonyJob
from .subset import subset_dataset


@dataclass
class SearchParameters:
    collection_id: str
    temporal: Tuple[str, str]
    bbox: Tuple[float, float, float, float]
    cloud_cover: Optional[Tuple[int, int]]
    sort_key: Optional[str]
    limit: Optional[int]
    destination: Path


class NasaEarthdataCollection:
    """Bound helper for interacting with a single NASA Earthdata collection."""

    def __init__(self, plugin: "NasaEarthdata", collection_concept_id: str) -> None:
        if not collection_concept_id:
            raise ValueError("collection_concept_id is required to bind a collection.")
        self._plugin = plugin
        self.collection_concept_id = collection_concept_id

    def list_supported_variables(
        self,
        *,
        keyword: Optional[str] = None,
        umm: bool = False,
    ) -> List[Dict[str, Any]]:
        return self._plugin.list_supported_variables(
            self.collection_concept_id,
            keyword=keyword,
            umm=umm,
        )

    def supports_variable(self, variable: str) -> bool:
        return self._plugin.supports_variable(
            self.collection_concept_id,
            variable,
        )

    def supports_harmony(self) -> bool:
        return self._plugin.supports_harmony(self.collection_concept_id)

    def get_harmony_capabilities(self) -> Dict[str, Any]:
        return self._plugin.get_harmony_capabilities(self.collection_concept_id)

    def get_collection_info(self) -> Dict[str, Any]:
        return self._plugin.get_collection_info(self.collection_concept_id)


class NasaEarthdata(DataSourcePlugin):
    """NASA Earthdata plugin leveraging the CMR API for discovery and downloads."""

    _DEFAULT_FOLDER = "rskit-nasa_earthdata"

    def __init__(self) -> None:
        credentials = CredentialManager.get_credential("nasa_earthdata")
        if not credentials:
            raise ValueError(
                "No credentials found for 'nasa_earthdata'. "
                "Please add credentials using: "
                "rs.auth.add_credential('nasa_earthdata', username='...', password='...', token='...')"
            )

        self._credentials = credentials
        self._client = CmrClient(token=credentials["token"])
        self._harmony_client: Optional[HarmonyClient] = None
    
    @property
    def harmony(self) -> HarmonyClient:
        """Lazy-initialize Harmony client."""
        if self._harmony_client is None:
            self._harmony_client = HarmonyClient(
                token=self._credentials["token"],
                skip_preview=True,
            )
        return self._harmony_client

    # Public API methods
    def list_supported_variables(
        self,
        collection_concept_id: str,
        *,
        keyword: Optional[str] = None,
        umm: bool = False,
    ) -> List[Dict[str, Any]]:
        """List supported variables for a NASA Earthdata collection.
        
        Queries the CMR Variables API to return metadata about all science
        variables available in the specified collection.
        
        Args:
            collection_concept_id: CMR collection concept ID.
            keyword: Optional keyword filters to include in CMR API call.
            umm: When True, return raw UMM variable metadata.
            
        Returns:
            When umm is False, list of variable metadata dictionaries containing:
                - name: Variable name (e.g., "/pixel_cloud/ssha")
                - long_name: Human-readable description
                - definition: Detailed variable definition
                - units: Measurement units
                - data_type: Data type (e.g., "float32")
                - dimensions: List of dimension names
                - scale: Scale factor if applicable
                - offset: Offset value if applicable
                - fill_value: Fill/missing value
                - concept_id: CMR variable concept ID
            When umm is True, a list of raw UMM metadata dictionaries.
                
        Raises:
            ValueError: If collection_concept_id is missing.
                
        Example:
            >>> plugin = NasaEarthdata()
            >>> collection_id = plugin.resolve_collection_concept_id(
            ...     doi="10.5067/SWOT-L2_HR_PIXC-2.0"
            ... )
            >>> variables = plugin.list_supported_variables(collection_id)
            >>> 
            >>> for var in variables[:5]:
            ...     print(f"{var['name']}: {var['long_name']}")
        """
        variables = self._client.get_collection_variables(
            collection_concept_id=collection_concept_id,
            keyword=keyword,
            umm=umm,
        )
        
        return variables

    def supports_variable(
        self,
        collection_concept_id: str,
        variable: str,
    ) -> bool:
        """Check if a collection supports a specific variable.
        
        Args:
            collection_concept_id: CMR collection concept ID.
            variable: Variable name to check (e.g., "ssha", "ssh_karin").
            
        Returns:
            True if the variable is available in the collection.
            
        Raises:
            ValueError: If collection_concept_id is missing.
        """
        variables = self.list_supported_variables(collection_concept_id)
        target = variable.lower()
        return any(v.get("name", "").lower().split('/')[-1] == target for v in variables)

    def resolve_collection_concept_id(
        self,
        *,
        doi: Optional[str] = None,
        short_name: Optional[str] = None,
        version: Optional[str] = None,
    ) -> str:
        """Resolve any of DOI, short_name, or version to a CMR collection concept ID."""
        return self._client.resolve_collection_concept_id(
            doi=doi,
            short_name=short_name,
            version=version,
        )

    def get_collection_info(self, collection_concept_id: str) -> Dict[str, Any]:
        """Fetch CMR collection metadata for a concept ID."""
        return self._client.get_collection_info(
            collection_concept_id=collection_concept_id,
        )

    def collection(self, collection_concept_id: str) -> NasaEarthdataCollection:
        """Return a collection-scoped helper for repeated lookups."""
        return NasaEarthdataCollection(self, collection_concept_id)
    
    def supports_harmony(self, collection_concept_id: str) -> bool:
        """Check if a collection supports Harmony server-side subsetting.
        
        Args:
            collection_concept_id: CMR collection concept ID.
            
        Returns:
            True if Harmony subsetting is available for the collection.
        """
        return self.harmony.supports_collection(collection_concept_id)

    def get_harmony_capabilities(self, collection_concept_id: str) -> Dict[str, Any]:
        """Get Harmony capabilities for a collection.
        
        Args:
            collection_concept_id: CMR collection concept ID.
            
        Returns:
            Dictionary with capability flags (variableSubset, bboxSubset, etc.).
        """
        return self.harmony.get_capabilities(collection_concept_id)

    def estimate_size(self, query: Query) -> Optional[int]:
        # TODO: implement size estimation once consistent granule sizing metadata is available.
        return None

    def download(
        self,
        query: Query,
        destination: Optional[Path] = None,
        *,
        limit: Optional[int] = None,
        skip_existing: bool = True,
    ) -> List[Path]:
        """Download granules matching the query parameters."""
        params = self._prepare_search_parameters(query, destination, limit)
        _, urls = self._search_granules(params)

        if not urls:
            return []

        return self._client.download_granules(
            urls,
            params.destination,
            limit=params.limit,
            skip_existing=skip_existing,
        )

    def fetch(
        self,
        query: Query,
        destination: Optional[Path] = None,
        *,
        limit: Optional[int] = None,
        skip_existing: bool = True,
        variables: Optional[List[str]] = None,
    ) -> xr.Dataset:
        """Return an xarray.Dataset for granules matching the query.
        
        Uses server-side subsetting via NASA Harmony when the collection supports it,
        with automatic fallback to client-side subsetting.
        
        Args:
            query: Query with spatial/temporal extents and params.
            destination: Directory to save downloaded files.
            limit: Maximum number of granules to process.
            skip_existing: Skip files that already exist locally.
            variables: List of variable names to subset (Harmony only).
            
        Returns:
            xarray.Dataset containing the requested data.
        """
        params = self._prepare_search_parameters(query, destination, limit)
        
        if self.supports_harmony(params.collection_id):
            try:
                return self._fetch_via_harmony(params, query, variables, skip_existing)
            except Exception as e:
                # Fall back to client-side if Harmony fails
                import warnings
                warnings.warn(
                    f"Harmony subsetting failed ({e}), falling back to client-side processing.",
                    UserWarning,
                    stacklevel=2,
                )
        
        # Client-side approach: download full granules then subset locally
        _, urls = self._search_granules(params)

        if not urls:
            return xr.Dataset()

        file_paths = self._client.download_granules(
            urls,
            params.destination,
            limit=params.limit,
            skip_existing=skip_existing,
        )

        dataset = self._load_dataset(file_paths)
        return self._subset_dataset(dataset, query)
    
    def _fetch_via_harmony(
        self,
        params: SearchParameters,
        query: Query,
        variables: Optional[List[str]],
        skip_existing: bool,
    ) -> xr.Dataset:
        """Fetch data using Harmony server-side subsetting."""
        # Build Harmony request
        bbox = None
        if query.spatial_extent:
            bbox = (
                float(query.spatial_extent.lon_min),
                float(query.spatial_extent.lat_min),
                float(query.spatial_extent.lon_max),
                float(query.spatial_extent.lat_max),
            )
        
        temporal = None
        if query.temporal_extent:
            temporal = (
                self._format_datetime(query.temporal_extent.start),
                self._format_datetime(query.temporal_extent.end),
            )
        
        # Submit Harmony job
        job = self.harmony.subset(
            collection_id=params.collection_id,
            bbox=bbox,
            temporal=temporal,
            variables=variables,
            max_results=params.limit,
        )
        
        # Wait for completion
        completed_job = self.harmony.wait_for_job(job.job_id)
        
        # Download results
        file_paths = self.harmony.download_results(
            completed_job,
            str(params.destination),
            skip_existing=skip_existing,
        )
        
        # Load into xarray
        return self._load_dataset([Path(p) for p in file_paths])

    # Private helper methods
    def _prepare_search_parameters(
        self,
        query: Query,
        destination: Optional[Path],
        limit: Optional[int],
    ) -> SearchParameters:
        if not query.temporal_extent:
            raise ValueError("NASA Earthdata queries require a temporal extent.")

        if not query.spatial_extent:
            raise ValueError("NASA Earthdata queries require a spatial extent.")

        temporal = (
            self._format_datetime(query.temporal_extent.start),
            self._format_datetime(query.temporal_extent.end),
        )
        bbox = (
            float(query.spatial_extent.lon_min),
            float(query.spatial_extent.lat_min),
            float(query.spatial_extent.lon_max),
            float(query.spatial_extent.lat_max),
        )

        params = query.params
        collection_id = params.get("collection_concept_id")
        if not collection_id:
            raise ValueError(
                "NASA Earthdata queries require `collection_concept_id`. "
                "Resolve it first using `NasaEarthdata.resolve_collection_concept_id(...)` "
                "and pass it via Query.with_params(collection_concept_id=...)."
            )

        resolved_limit = limit or params.get("max_granules")

        cloud_cover = params.get("cloud_cover")
        if cloud_cover and len(cloud_cover) != 2:
            raise ValueError("cloud_cover must be a tuple of (min_percent, max_percent).")

        sort_key = params.get("sort_key")

        destination_path = self._resolve_destination(destination, params.get("download_dir"))

        return SearchParameters(
            collection_id,
            temporal,
            bbox,
            cloud_cover,
            sort_key,
            resolved_limit,
            destination_path,
        )

    def _search_granules(
        self,
        params: SearchParameters,
    ) -> Tuple[List[dict], List[str]]:
        granules = self._client.search_granules(
            collection_concept_id=params.collection_id,
            temporal=params.temporal,
            bbox=params.bbox,
            limit=params.limit,
            cloud_cover=params.cloud_cover,
            sort_key=params.sort_key,
        )
        urls = self._client.extract_download_urls(granules)
        if params.limit:
            urls = urls[: params.limit]
        return granules, urls

    def _resolve_destination(
        self,
        destination: Optional[Path],
        option_destination: Optional[str],
    ) -> Path:
        if destination:
            return Path(destination).expanduser().resolve()

        if option_destination:
            return Path(option_destination).expanduser().resolve()

        downloads_dir = ensure_downloads_directory()
        target = downloads_dir / self._DEFAULT_FOLDER
        target.mkdir(parents=True, exist_ok=True)
        return target

    @staticmethod
    def _format_datetime(value: datetime) -> str:
        if value.tzinfo:
            value = value.astimezone(timezone.utc)
        else:
            value = value.replace(tzinfo=timezone.utc)
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _load_dataset(self, file_paths: List[Path]) -> xr.Dataset:
        if not file_paths:
            return xr.Dataset()

        # Filter to only include NetCDF files (exclude .md5, .xml, etc.)
        nc_files = [p for p in file_paths if p.suffix in ('.nc', '.nc4', '.hdf', '.h5')]
        
        if not nc_files:
            return xr.Dataset()

        datasets = xr.open_mfdataset(
            [str(path) for path in nc_files],
            combine="by_coords",
            parallel=False,
        )
        return datasets

    def _subset_dataset(self, dataset: xr.Dataset, query: Query) -> xr.Dataset:
        drop_nan_lines = query.params.get("drop_nan_lines", True)
        return subset_dataset(
            dataset,
            query.spatial_extent,
            query.temporal_extent,
            drop_nan_lines=drop_nan_lines,
        )
