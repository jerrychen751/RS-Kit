"""
Utilities for interacting with NASA's Common Metadata Repository (CMR) API.
"""

from __future__ import annotations

import re
import warnings
from pathlib import Path
from urllib.parse import urlparse
from typing import Iterable, List, Optional, Sequence, Tuple

import requests

CollectionInfo = Tuple[str, dict]


class CmrClient:
    """
    Client for the NASA CMR API.
    """

    COLLECTIONS_URL = "https://cmr.earthdata.nasa.gov/search/collections.json"
    GRANULES_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
    VARIABLES_URL = "https://cmr.earthdata.nasa.gov/search/variables.json"

    def __init__(
        self,
        token: Optional[str] = None,
        session: Optional[requests.Session] = None,
        timeout: int = 30,
    ) -> None:
        self._session = session or requests.Session()
        self._timeout = timeout
        self._token = token

        if token:
            self._session.headers.update({"Authorization": f"Bearer {token}"})

    # Public API methods
    def get_collection_info(
        self,
        *,
        doi: Optional[str] = None,
        short_name: Optional[str] = None,
        version: Optional[str] = None,
    ) -> CollectionInfo:
        """
        Resolve collection identifiers (DOI or short_name+version) to concept ID and metadata.
        
        Args:
            doi: Collection DOI
            short_name: Collection short name
            version: Collection version
            
        Returns:
            Tuple[str, dict]: (concept_id, collection_metadata)
            
        Raises:
            ValueError: If neither doi nor both short_name and version are provided, or if no collections are found.
        """
        # Build params dictionary
        params = {}
        if doi:
            params["doi"] = CmrClient._normalize_doi(doi)
        elif short_name and version:
            params["short_name"] = short_name
            params["version"] = str(version)
        else:
            raise ValueError(
                "Either doi or both short_name and version must be provided to identify a collection."
            )

        # Make HTTP GET request
        response = self._session.get(
            self.COLLECTIONS_URL,
            params=params,
            timeout=self._timeout,
        )
        response.raise_for_status()
        data = response.json()
        entries = data.get("feed", {}).get("entry", [])

        if not entries:
            raise ValueError("No collection results returned for provided identifiers.")

        if len(entries) > 1:
            collection_names = [entry.get("title", entry.get("id", "Unknown")) for entry in entries]
            warnings.warn(
                f"Multiple collections ({len(entries)}) found matching the search criteria. "
                f"Using the first match: '{collection_names[0]}'. "
                f"Other matches: {collection_names[1:]}. "
                "Consider refining your search criteria (e.g., using a more specific DOI or version).",
                UserWarning,
                stacklevel=2,
            )

        collection = entries[0]
        return collection.get("id", ""), collection

    def search_granules(
        self,
        *,
        collection_concept_id: str,
        temporal: Tuple[str, str],
        bbox: Tuple[float, float, float, float],
        page_size: int = 2000,
        limit: Optional[int] = None,
        cloud_cover: Optional[Tuple[int, int]] = None,
        sort_key: Optional[str] = None,
    ) -> List[dict]:
        """Return granule metadata entries for the requested search parameters."""
        params = {
            "collection_concept_id": collection_concept_id,
            "temporal": "{},{}".format(*temporal),
            "bounding_box": ",".join(str(float(value)) for value in bbox),
            "page_size": page_size,
        }

        if cloud_cover and len(cloud_cover) == 2:
            params["cloud_cover"] = f"{cloud_cover[0]},{cloud_cover[1]}"

        if sort_key:
            params["sort_key"] = sort_key

        collected: List[dict] = []
        headers = {}

        while True:
            response = self._session.get(
                self.GRANULES_URL,
                params=params,
                headers=headers,
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload = response.json()
            entries = payload.get("feed", {}).get("entry", [])

            if not entries:
                break

            collected.extend(entries)
            if limit and len(collected) >= limit:
                collected = collected[:limit]
                break

            search_after = response.headers.get("CMR-Search-After")
            if not search_after:
                break

            headers["CMR-Search-After"] = search_after

        return collected

    @staticmethod
    def extract_download_urls(granules: Sequence[dict]) -> List[str]:
        """Return list of download URLs from granule metadata entries."""
        urls: List[str] = []
        for granule in granules:
            links = granule.get("links", [])
            for link in links:
                href = link.get("href")
                rel = link.get("rel", "")
                title = link.get("title", "")

                if (
                    href
                    and "data#" in rel
                    and "download" in title.lower()
                ):
                    urls.append(href)

        urls.sort()
        return urls

    def search_variables(
        self,
        *,
        doi: Optional[str] = None,
        short_name: Optional[str] = None,
        version: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> List[dict]:
        """
        Search for variables associated with a collection and their metadata.
        """
        # Resolve collection to get concept ID
        collection_concept_id, collection_meta = self.get_collection_info(
            doi=doi, short_name=short_name, version=version
        )
        
        # Get variable concept IDs from collection associations
        variable_concept_ids = self._get_collection_variable_concept_ids(collection_concept_id)
        
        if not variable_concept_ids:
            return []
        
        # Fetch metadata for each variable using variable concept ids
        collected: List[dict] = []
        
        for var_id in variable_concept_ids:
            try:
                var_meta = self._fetch_variable_metadata(var_id)
                if var_meta:
                    # Apply keyword filter if provided
                    if keyword:
                        keyword_lower = keyword.lower()
                        name_match = keyword_lower in var_meta.get("name", "").lower()
                        long_name_match = keyword_lower in var_meta.get("long_name", "").lower()
                        definition_match = keyword_lower in var_meta.get("definition", "").lower()
                        
                        if not (name_match or long_name_match or definition_match):
                            continue
                    
                    collected.append(var_meta)
            except requests.RequestException:
                # Skip variables that fail to fetch
                continue
        
        return collected
    
    def _get_collection_variable_concept_ids(self, collection_concept_id: str) -> List[str]:
        """
        Get variable concept IDs associated with a collection.
        """
        url = "https://cmr.earthdata.nasa.gov/search/collections.umm_json"
        params = {"concept_id": collection_concept_id}
        
        response = self._session.get(url, params=params, timeout=self._timeout)
        response.raise_for_status()
        
        data = response.json()
        items = data.get("items", [])
        
        if not items:
            return []
        
        meta = items[0].get("meta", {})
        associations = meta.get("associations", {})
        return associations.get("variables", [])
    
    def _fetch_variable_metadata(self, variable_concept_id: str) -> Optional[dict]:
        """
        Fetch metadata for a single variable.
        """
        url = f"https://cmr.earthdata.nasa.gov/search/concepts/{variable_concept_id}"
        headers = {"Accept": "application/vnd.nasa.cmr.umm+json"}
        
        response = self._session.get(url, headers=headers, timeout=self._timeout)
        response.raise_for_status()
        
        meta = response.json()
        
        return {
            "concept_id": variable_concept_id,
            "name": meta.get("Name", ""),
            "long_name": meta.get("LongName", ""),
            "definition": meta.get("Definition", ""),
            "units": meta.get("Units", ""),
            "data_type": meta.get("DataType", ""),
            "dimensions": [
                d.get("Name", "") 
                for d in meta.get("Dimensions", [])
            ],
            "scale": meta.get("Scale"),
            "offset": meta.get("Offset"),
            "fill_value": meta.get("FillValues", [{}])[0].get("Value") if meta.get("FillValues") else None,
        }

    def get_variable_names(
        self,
        *,
        doi: Optional[str] = None,
        short_name: Optional[str] = None,
        version: Optional[str] = None,
    ) -> List[str]:
        """
        Get list of variable names for a collection.
        """
        variables = self.search_variables(doi=doi, short_name=short_name, version=version)
        return [v["name"] for v in variables if v["name"]]

    def download_granules(
        self,
        urls: Iterable[str],
        destination: Path,
        limit: Optional[int] = None,
        skip_existing: bool = True,
    ) -> List[Path]:
        """
        Download granules to the destination directory.
        """
        destination.mkdir(parents=True, exist_ok=True)
        downloaded: List[Path] = []

        for idx, url in enumerate(urls, start=1):
            if limit and idx > limit:
                break

            filename = url.split("/")[-1]
            target = destination / filename

            if skip_existing and target.exists():
                downloaded.append(target)
                continue

            response = self._session.get(url, stream=True, timeout=self._timeout)
            response.raise_for_status()

            with open(target, "wb") as file_obj:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file_obj.write(chunk)

            downloaded.append(target)

        return downloaded

    # Private helper methods
    @staticmethod
    def _normalize_doi(doi: str) -> str:
        """
        Return DOI value without URL prefix.
        """
        s = doi.strip()
        if "://" in s:
            u = urlparse(s)
            host = (u.netloc or "").lower()

            if host == "doi.org" or host.endswith(".doi.org"):
                doi = u.path.lstrip("/")
                return doi.strip()
        return s
