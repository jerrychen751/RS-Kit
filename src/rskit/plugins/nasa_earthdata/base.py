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
from .cmr import CMRClient
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


class NasaEarthdata(DataSourcePlugin):
    """NASA Earthdata plugin leveraging the CMR API for discovery and downloads."""

    CREDENTIAL_SCHEMA = {
        "required_fields": ["username", "password", "token"],
        "field_descriptions": {
            "username": "NASA Earthdata username",
            "password": "NASA Earthdata password",
            "token": "Bearer token to access application services integrated with the Earthdata Login system",
        },
    }

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
        self._client = CMRClient(token=credentials["token"])
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
    def discover(
        self,
        *,
        doi: Optional[str] = None,
        short_name: Optional[str] = None,
        version: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Discover available variables for a NASA Earthdata collection.
        
        Queries the CMR Variables API to return metadata about all science
        variables available in the specified collection.
        
        Args:
            doi: Collection DOI (e.g., "10.5067/SWOT-L2_HR_PIXC-2.0"). This alone
                is sufficient to identify a collection.
            short_name: Collection short name (e.g., "SWOT_L2_HR_PIXC_2.0").
                Requires version to be specified.
            version: Collection version (e.g., "2.0"). Required with short_name.
            keyword: Optional keyword to filter variables by name or description.
            
        Returns:
            List of variable metadata dictionaries containing:
                - concept_id: CMR variable concept ID
                - name: Variable name (e.g., "/pixel_cloud/ssha")
                - long_name: Human-readable description
                - definition: Detailed variable definition
                - units: Measurement units
                - data_type: Data type (e.g., "float32")
                - dimensions: List of dimension names
                - scale: Scale factor if applicable
                - offset: Offset value if applicable
                - fill_value: Fill/missing value
                
        Raises:
            ValueError: If neither doi nor both short_name and version are provided.
                
        Example:
            >>> plugin = NasaEarthdata()
            >>> # Using DOI (preferred - found in Earthdata Search)
            >>> variables = plugin.discover(doi="10.5067/SWOT-L2_HR_PIXC-2.0")
            >>> 
            >>> # Using short_name + version
            >>> variables = plugin.discover(short_name="SWOT_L2_HR_PIXC_2.0", version="2.0")
            >>> 
            >>> for var in variables[:5]:
            ...     print(f"{var['name']}: {var['long_name']}")
        """
        variables = self._client.search_variables(
            doi=doi,
            short_name=short_name,
            version=version,
            keyword=keyword,
        )
        
        return variables

    def supports_variable(
        self,
        variable: str,
        *,
        doi: Optional[str] = None,
        short_name: Optional[str] = None,
        version: Optional[str] = None,
    ) -> bool:
        """Check if a collection supports a specific variable.
        
        Args:
            variable: Variable name to check (e.g., "ssha", "ssh_karin").
            doi: Collection DOI (e.g., "10.5067/SWOT-L2_HR_PIXC-2.0").
            short_name: Collection short name (requires version).
            version: Collection version (requires short_name).
            
        Returns:
            True if the variable is available in the collection.
            
        Raises:
            ValueError: If neither doi nor both short_name and version are provided.
        """
        variable_names = self._client.get_variable_names(
            doi=doi, short_name=short_name, version=version
        )
        return variable.lower() in [v.lower() for v in variable_names]
    
    def supports_harmony(self, collection_concept_id: str) -> bool:
        """Check if a collection supports Harmony server-side subsetting.
        
        Args:
            collection_concept_id: CMR collection concept ID.
            
        Returns:
            True if Harmony subsetting is available for the collection.
        """
        return self.harmony.supports_harmony(collection_concept_id)

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
        use_harmony: Optional[bool] = None,
        variables: Optional[List[str]] = None,
    ) -> xr.Dataset:
        """Return an xarray.Dataset for granules matching the query.
        
        Supports server-side subsetting via NASA Harmony when available,
        with automatic fallback to client-side subsetting.
        
        Args:
            query: Query with spatial/temporal extents and options.
            destination: Directory to save downloaded files.
            limit: Maximum number of granules to process.
            skip_existing: Skip files that already exist locally.
            use_harmony: Force Harmony usage (True), disable (False), or auto-detect (None).
            variables: List of variable names to subset (Harmony only).
            
        Returns:
            xarray.Dataset containing the requested data.
        """
        params = self._prepare_search_parameters(query, destination, limit)
        
        # Determine whether to use Harmony
        should_use_harmony = self._should_use_harmony(
            use_harmony,
            params.collection_id,
            variables,
        )
        
        if should_use_harmony:
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
    
    def _should_use_harmony(
        self,
        use_harmony: Optional[bool],
        collection_id: str,
        variables: Optional[List[str]],
    ) -> bool:
        """Determine whether to use Harmony for subsetting."""
        # Explicit user preference
        if use_harmony is not None:
            return use_harmony
        
        # Auto-detect: use Harmony if collection supports it and variables requested
        if variables:
            return self.supports_harmony(collection_id)
        
        # Default to client-side for backward compatibility
        return False
    
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

        options = query.options
        collection_id = options.get("collection_concept_id")
        if not collection_id:
            collection_id = self._resolve_collection_concept_id(options)

        resolved_limit = limit or options.get("max_granules")

        cloud_cover = options.get("cloud_cover")
        if cloud_cover and len(cloud_cover) != 2:
            raise ValueError("cloud_cover must be a tuple of (min_percent, max_percent).")

        sort_key = options.get("sort_key")

        destination_path = self._resolve_destination(destination, options.get("download_dir"))

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

    def _resolve_collection_concept_id(self, options: Dict[str, Any]) -> str:
        doi = options.get("collection_doi")
        short_name = options.get("collection_short_name")
        version = options.get("collection_version")

        concept_id, _ = self._client.resolve_collection(
            doi=doi,
            short_name=short_name,
            version=version,
        )
        if not concept_id:
            raise ValueError(
                "Unable to resolve collection concept ID. Provide either "
                "`collection_concept_id`, `collection_doi`, or both "
                "`collection_short_name` and `collection_version` in query options."
            )
        return concept_id

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
        drop_nan_lines = query.options.get("drop_nan_lines", True)
        return subset_dataset(
            dataset,
            query.spatial_extent,
            query.temporal_extent,
            drop_nan_lines=drop_nan_lines,
        )
