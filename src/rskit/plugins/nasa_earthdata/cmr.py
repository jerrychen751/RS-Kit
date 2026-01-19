"""
Utilities for interacting with NASA's Common Metadata Repository (CMR) API.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import requests

CollectionInfo = Dict[str, Any]


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

    # --- Collection Metadata ---
    def resolve_collection_concept_id(
        self,
        doi: Optional[str] = None,
        short_name: Optional[str] = None,
        version: Optional[str] = None,
    ) -> str:
        """
        Resolve collection identifiers (some combination of DOI, short_name, version) to a concept ID.

        Args:
            doi: Collection DOI (optional).
            short_name: Collection short name (optional).
            version: Collection version (optional).

        Returns:
            Collection concept ID string.

        Raises:
            ValueError: If no identifiers are provided, results are ambiguous, or no collections are found.
        """
        params: Dict[str, str] = {}
        if doi:
            params["doi"] = self._normalize_doi(doi)
        if short_name:
            params["short_name"] = short_name
        if version:
            params["version"] = str(version)
        if not params:
            raise ValueError(
                "At least one of doi, short_name, or version must be provided to identify a collection."
            )

        entries = self._search_collections(params)

        if not entries:
            raise ValueError("No collection results returned for provided identifiers.")

        if len(entries) > 1:
            collection_names = [entry.get("title", entry.get("id", "Unknown")) for entry in entries]
            raise ValueError(
                "Multiple collections found matching the search criteria. "
                f"Matches: {collection_names}. "
                "Refine your identifiers (e.g., use a more specific DOI or version)."
            )

        concept_id = entries[0].get("id", "")
        if not concept_id:
            raise ValueError("Collection concept ID not found in CMR response.")

        return concept_id

    def get_collection_info(
        self,
        collection_concept_id: str,
    ) -> List[CollectionInfo]:
        """
        Fetch collection metadata for a specific concept ID. Assumes valid concept ID is provided.

        Args:
            collection_concept_id (str): CMR collection concept ID.

        Returns:
            List of collection metadata dictionaries.

        Raises:
            ValueError: If no collection is found.
        """
        entries = self._search_collections({"concept_id": collection_concept_id})
        if not entries:
            raise ValueError(
                f"No collection results returned for concept_id '{collection_concept_id}'."
            )

        return entries

    # --- Data Granule Metadata ---        

    def search_granules(
        self,
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

    def get_collection_variables(
        self,
        collection_concept_id: str,
    ) -> List[dict]:
        """
        Get raw UMM metadata for variables associated with a collection.

        Args:
            collection_concept_id: CMR collection concept ID.

        Returns:
            List of raw UMM metadata dictionaries.
        """
        if not collection_concept_id:
            raise ValueError("collection_concept_id is required to fetch collection variables.")

        # Get variable concept IDs from collection associations
        variable_concept_ids = self._get_collection_variable_concept_ids(collection_concept_id)

        if not variable_concept_ids:
            return []

        collected: List[dict] = []

        for var_id in variable_concept_ids:
            try:
                url = f"https://cmr.earthdata.nasa.gov/search/concepts/{var_id}"
                headers = {"Accept": "application/vnd.nasa.cmr.umm+json"}
                response = self._session.get(url, headers=headers, timeout=self._timeout)
                response.raise_for_status()
                meta = response.json()
                if meta:
                    collected.append(meta)
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
    
    def download_granule(
        self,
        url: str,
        destination: Path,
        skip_existing: bool = False,
    ) -> Path:
        """
        Download a granule to the destination directory, creating it if it does not exist.
        """
        destination.mkdir(parents=True, exist_ok=True)
        filename = url.split("/")[-1]
        target = destination / filename
        if skip_existing and target.exists():
            return target

        response = self._session.get(url, stream=True, timeout=self._timeout)
        response.raise_for_status()

        with open(target, "wb") as file_obj:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file_obj.write(chunk)
        
        return target

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
        downloaded: List[Path] = []

        for idx, url in enumerate(urls, start=1):
            if limit and idx > limit:
                break
            path = self.download_granule(url, destination, skip_existing)
            downloaded.append(path)

        return downloaded

    # Private helper methods
    def _search_collections(self, params: Dict[str, str]) -> List[CollectionInfo]:
        """
        Search for collections using a set of CMR API parameters. Returns a list of collection metadata dictionaries from the CMR API response.

        Args:
            params (Dict[str, str]): CMR API parameters.

        Returns:
            List of collection metadata dictionaries.

        Raises:
            requests.RequestException: If the request fails.
        """
        response = self._session.get(
            self.COLLECTIONS_URL,
            params=params,
            timeout=self._timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("feed", {}).get("entry", [])

    def _normalize_doi(self, doi: str) -> str:
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
