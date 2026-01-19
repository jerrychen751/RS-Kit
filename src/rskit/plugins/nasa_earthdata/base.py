from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from ...auth.credential_manager import CredentialManager
from ...contracts.plugin import DataSourcePlugin
from ...core.query import Query
from ...utils.downloads import ensure_downloads_directory
from .cmr import CmrClient, CollectionInfo
from .harmony import HarmonyClient
from .subset import subset_granule, SubsettingParams

@dataclass
class GranuleSearchParams:
    collection_id: str
    temporal: Tuple[str, str]
    bbox: Tuple[float, float, float, float]
    cloud_cover: Optional[Tuple[int, int]]
    sort_key: Optional[str]
    limit: Optional[int]



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
            )
        return self._harmony_client

    # --- NASA Harmony Support ---
    def list_harmony_capabilities(
        self,
        collection_concept_id: str,
    ) -> Dict[str, bool]:
        """Return Harmony capability flags advertised in CMR metadata."""
        try:
            collection_info = self.get_collection_info(collection_concept_id)
        except (ValueError, requests.RequestException):
            return {}

        if not collection_info:
            return {}

        service_features = collection_info[0].get("service_features") or {}
        harmony_features = service_features.get("harmony") or {}
        if not harmony_features:
            return {}

        return {
            key: bool(harmony_features.get(key, False))
            for key in (
                "has_formats",
                "has_variables",
                "has_transforms",
                "has_combine",
                "has_spatial_subsetting",
                "has_temporal_subsetting",
            )
        }

    def supports_harmony(self, collection_concept_id: str) -> bool:
        """Check if a collection advertises Harmony support in CMR metadata."""
        capabilities = self.list_harmony_capabilities(collection_concept_id)
        return any(capabilities.values())

    def supports_harmony_format_conversions(self, collection_concept_id: str) -> bool:
        """Check if a collection advertises Harmony format conversions."""
        capabilities = self.list_harmony_capabilities(collection_concept_id)
        return bool(capabilities.get("has_formats"))

    def supports_harmony_transforms(self, collection_concept_id: str) -> bool:
        """Check if a collection advertises Harmony reprojections, resampling, or interpolation."""
        capabilities = self.list_harmony_capabilities(collection_concept_id)
        return bool(capabilities.get("has_transforms"))

    def supports_harmony_combine(self, collection_concept_id: str) -> bool:
        """Check if a collection advertises Harmony support for merging multiple files into one."""
        capabilities = self.list_harmony_capabilities(collection_concept_id)
        return bool(capabilities.get("has_combine"))

    def supports_harmony_variable_subsetting(self, collection_concept_id: str) -> bool:
        """Check if a collection advertises Harmony variable subsetting."""
        capabilities = self.list_harmony_capabilities(collection_concept_id)
        return bool(capabilities.get("has_variables"))        

    def supports_harmony_spatial_subsetting(self, collection_concept_id: str) -> bool:
        """Check if a collection advertises Harmony spatial subsetting."""
        capabilities = self.list_harmony_capabilities(collection_concept_id)
        return bool(capabilities.get("has_spatial_subsetting"))

    def supports_harmony_temporal_subsetting(self, collection_concept_id: str) -> bool:
        """Check if a collection advertises Harmony temporal subsetting."""
        capabilities = self.list_harmony_capabilities(collection_concept_id)
        return bool(capabilities.get("has_temporal_subsetting"))

    # --- Collection Metadata ---
    def get_collection_concept_id(
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

    def get_collection_info(self, collection_concept_id: str) -> List[CollectionInfo]:
        """
        Returns CMR collection metadata for a concept ID.

        Args:
            collection_concept_id (str): CMR collection concept ID.
        
        Returns:
            List of collection metadata dictionaries.

        Raises:
            ValueError: If collection_concept_id is missing or no collection is found.
        """
        if not collection_concept_id:
            raise ValueError("collection_concept_id is required to fetch collection info.")

        return self._client.get_collection_info(
            collection_concept_id=collection_concept_id,
        )

    # --- Data Granule Metadata ---


    def get_collection_variables(
        self,
        collection_concept_id: str,
    ) -> List[Dict[str, Any]]:
        """List supported variables for a NASA Earthdata collection.
        
        Queries the CMR Variables API to return raw UMM metadata for all
        science variables available in the specified collection.
        
        Args:
            collection_concept_id: CMR collection concept ID.
            
        Returns:
            List of raw UMM metadata dictionaries for variables in the collection.
                
        Raises:
            ValueError: If collection_concept_id is missing.
                
        Example:
            >>> plugin = NasaEarthdata()
            >>> collection_id = plugin.resolve_collection_concept_id(
            ...     doi="10.5067/SWOT-L2_HR_PIXC-2.0"
            ... )
            >>> variables = plugin.get_data_variables(collection_id)
            >>> variables[:1]
        """
        variables = self._client.get_collection_variables(
            collection_concept_id=collection_concept_id,
        )
        
        return variables

    def contains_variable(
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
        variables = self.get_collection_variables(collection_concept_id)
        target = variable.lower()
        return any(v.get("Name", "").lower().split("/")[-1] == target for v in variables)

    def estimate_granule_size(self, query: Query) -> Optional[int]:
        # TODO: implement size estimation once consistent granule sizing metadata is available.
        return None

    # --- Actions ---
    
    def download_data(
        self,
        query: Query,
        destination: Optional[Path] = None,
        *,
        limit: Optional[int] = None,
        skip_existing: bool = True,
    ) -> List[str]:
        """
        Downloads and saves data granules based on the query parameters.
        
        Note: This will download the full data granules without subsetting. Any data granule containing data within the defined query spatial and temporal extends will be downloaded.

        Args:
            query (Query): Query with spatial/temporal extents and params.
            destination (Optional[Path]): Absolute path to the directory to save downloaded files. If None, uses the user's Downloads directory under the rskit-nasa_earthdata folder.
            skip_existing (bool): Skip files that already exist in the destination directory. If false, will overwrite existing files.
            limit (Optional[int]): Maximum number of granules to download and process.
        """
        params = self._normalize_granule_search_params(query, limit)
        destination = self._resolve_downloads_directory(destination)
        _, download_urls = self._search_granules(params)

        if not download_urls:
            return []
                
        downloaded = self._client.download_granules(
            download_urls,
            destination,
            limit=params.limit,
            skip_existing=skip_existing,
        )
        return [str(fp) for fp in downloaded]

    def download_subsetted_data(
        self,
        query: Query,
        destination: Optional[Path] = None,
        *,
        limit: Optional[int] = None,
        skip_existing: bool = True,
        mask_out_of_bounds: bool = False,
    ) -> List[str]:
        """
        Downloads, subsets, and saves data granules based on the query parameters.

        Prefers to use server-side subsetting via NASA Harmony when the collection supports it. If Harmony is not available, after downloading each granule, an attempt will be made to subset data locally using the query parameters.

        Args:
            query (Query): Query with spatial/temporal extents and params.
            destination (Optional[Path]): Absolute path to the directory to save downloaded files. If None, uses the user's Downloads directory under the rskit-nasa_earthdata folder.
            skip_existing (bool): Skip files that already exist in the destination directory. If false, will overwrite existing files.
            limit (Optional[int]): Maximum number of granules to download and process.
            mask_out_of_bounds (bool): If longitude and latitude within the dataset are 2D, the default behavior is to keep the entire row/col as long as at least 1 value is inside of specified spatial extents. If enabled to True, the row/col will still be kept but out-of-bounds data will use the fill value specified in the original dataset's encoding.

        Returns:
            List[Path]: List of filepaths of downloaded files. Empty if no data granules patching query spatial/temporal extents were found using CMR API.

        Raises:

        """
        params = self._normalize_granule_search_params(query, limit)
        destination = self._resolve_downloads_directory(destination)
        collection_id = query.params.get("collection_concept_id")
        if not collection_id:
            raise ValueError("Missing collection concept id in query params")
        
        # Try subsetting with NASA Harmony API
        if self.supports_harmony_spatial_subsetting(collection_id) and self.supports_harmony_temporal_subsetting(collection_id):
            try:
                downloaded = self.harmony.subset_and_download(
                    params,
                    destination,
                )
                return [str(fp) for fp in downloaded]
            except Exception as e:
                import warnings
                print(e)
                warnings.warn("Harmony subsetting failed, attemping to subset locally.")

        # Otherwise use CMR API to find granules and manually download and subset
        _, download_urls = self._search_granules(params)
        if not download_urls:
            return []

        spatial_extent, temporal_extent = query.require_extents()
        subsetting_params = SubsettingParams(
            temporal=temporal_extent,
            spatial=spatial_extent,
        )
        
        # Upon any failed subsetting, an error will be raised and this function will stop immediately
        umm = self._client.get_collection_variables(collection_id)

        downloaded: List[Path] = []
        for url in download_urls:
            filepath = self._client.download_granule(url, destination, skip_existing)
            subset_granule(
                filepath,
                subsetting_params,
                umm,
                mask_out_of_bounds=mask_out_of_bounds,
            )  # if unsuccessful, an error will be raised
            downloaded.append(filepath)
        return [str(fp) for fp in downloaded]

    # Private helper methods
    def _normalize_granule_search_params(
        self,
        query: Query,
        limit: Optional[int],
    ) -> GranuleSearchParams:
        spatial_extent, temporal_extent = query.require_extents()

        temporal = (
            self._format_datetime(temporal_extent.start),
            self._format_datetime(temporal_extent.end),
        )
        bbox = (
            float(spatial_extent.lon_min),
            float(spatial_extent.lat_min),
            float(spatial_extent.lon_max),
            float(spatial_extent.lat_max),
        )

        params = query.params
        collection_id = params.get("collection_concept_id")
        if not collection_id:
            raise ValueError(
                "NASA Earthdata queries require `collection_concept_id`. "
                "Obtain it first using `NasaEarthdata.get_collection_concept_id()` "
                "and pass it via Query.with_params(collection_concept_id=...)."
            )

        resolved_limit = limit or params.get("max_granules")

        cloud_cover = params.get("cloud_cover")
        if cloud_cover and len(cloud_cover) != 2:
            raise ValueError("cloud_cover must be a tuple of (min_percent, max_percent).")

        sort_key = params.get("sort_key")

        return GranuleSearchParams(
            collection_id,
            temporal,
            bbox,
            cloud_cover,
            sort_key,
            resolved_limit,
        )

    def _search_granules(
        self,
        params: GranuleSearchParams,
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

    def _resolve_downloads_directory(
        self,
        destination: Optional[Path],
    ) -> Path:
        """Ensures the existence of the downloads directory for data granules."""
        if destination:
            destination = Path(destination).expanduser().resolve()
            destination.mkdir(parents=True, exist_ok=True)
            return destination

        # Default to user's Downloads directory
        user_downloads_dir = ensure_downloads_directory()
        downloads_dir = user_downloads_dir / self._DEFAULT_FOLDER
        downloads_dir.mkdir(parents=True, exist_ok=True)
        return downloads_dir

    @staticmethod
    def _format_datetime(value: datetime) -> str:
        if value.tzinfo:
            value = value.astimezone(timezone.utc)
        else:
            value = value.replace(tzinfo=timezone.utc)
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
