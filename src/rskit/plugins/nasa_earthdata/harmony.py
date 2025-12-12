"""Client for NASA Harmony API for server-side data subsetting."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests


@dataclass
class HarmonyJob:
    """Represents a Harmony processing job."""
    
    job_id: str
    status: str
    message: str
    progress: int
    links: List[Dict[str, str]]
    created_at: str
    updated_at: str
    
    @property
    def is_complete(self) -> bool:
        return self.status in ("successful", "complete", "complete_with_errors")
    
    @property
    def is_failed(self) -> bool:
        return self.status in ("failed", "canceled")
    
    @property
    def is_running(self) -> bool:
        return self.status in ("running", "accepted", "running_with_errors")
    
    @property
    def output_urls(self) -> List[str]:
        """Extract data output URLs from job links."""
        return [
            link["href"] 
            for link in self.links 
            if link.get("rel") == "data"
        ]


class HarmonyClient:
    """Client for NASA Harmony server-side subsetting API.
    
    Harmony provides cloud-based processing for NASA Earthdata collections,
    enabling spatial, temporal, and variable subsetting before download.
    
    Example:
        client = HarmonyClient(token="your_earthdata_token")
        
        # Check if a collection supports Harmony subsetting
        caps = client.get_capabilities("C1234567890-PROVIDER")
        if caps.get("variableSubset"):
            # Collection supports variable subsetting
            pass
        
        # Submit a subset request
        job = client.subset(
            collection_id="C1234567890-PROVIDER",
            bbox=(-180, -90, 180, 90),
            temporal=("2023-01-01T00:00:00Z", "2023-12-31T23:59:59Z"),
            variables=["ssha", "mdt"],
            granule_ids=["G1234567890-PROVIDER"],
        )
        
        # Wait for completion and get results
        result = client.wait_for_job(job.job_id)
        urls = result.output_urls
    """
    
    BASE_URL = "https://harmony.earthdata.nasa.gov"
    
    def __init__(
        self,
        token: str,
        session: Optional[requests.Session] = None,
        timeout: int = 60,
        skip_preview: bool = True,
    ) -> None:
        """Initialize Harmony client.
        
        Args:
            token: NASA Earthdata bearer token.
            session: Optional requests session for connection pooling.
            timeout: Request timeout in seconds.
            skip_preview: If True, skip preview for large requests (>300 granules).
                         Defaults to True for automation use cases.
        """
        self._token = token
        self._session = session or requests.Session()
        self._timeout = timeout
        self._skip_preview = skip_preview
        
        self._session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        })
    
    def get_capabilities(self, collection_id: str) -> Dict[str, Any]:
        """Get Harmony capabilities for a collection.
        
        Args:
            collection_id: CMR collection concept ID.
            
        Returns:
            Dictionary with capability flags:
                - variableSubset: bool - supports variable selection
                - bboxSubset: bool - supports bounding box subsetting
                - shapeSubset: bool - supports shapefile subsetting  
                - concatenate: bool - supports output concatenation
                - outputFormats: List[str] - supported output formats
        """
        url = f"{self.BASE_URL}/capabilities"
        params = {"collectionId": collection_id}
        
        response = self._session.get(url, params=params, timeout=self._timeout)
        response.raise_for_status()
        
        return response.json()
    
    def supports_harmony(self, collection_id: str) -> bool:
        """Check if a collection is configured for Harmony processing.
        
        Args:
            collection_id: CMR collection concept ID.
            
        Returns:
            True if the collection supports at least one Harmony capability.
        """
        try:
            caps = self.get_capabilities(collection_id)
            return any([
                caps.get("variableSubset", False),
                caps.get("bboxSubset", False),
                caps.get("shapeSubset", False),
            ])
        except requests.HTTPError:
            return False
    
    def subset(
        self,
        collection_id: str,
        *,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        temporal: Optional[Tuple[str, str]] = None,
        variables: Optional[List[str]] = None,
        granule_ids: Optional[List[str]] = None,
        granule_names: Optional[List[str]] = None,
        output_format: Optional[str] = None,
        concatenate: bool = False,
        max_results: Optional[int] = None,
    ) -> HarmonyJob:
        """Submit a subsetting request to Harmony.
        
        Uses the OGC Coverages API for subsetting requests.
        
        Args:
            collection_id: CMR collection concept ID.
            bbox: Bounding box as (west, south, east, north) in degrees.
            temporal: Time range as (start, end) ISO 8601 strings.
            variables: List of variable names to include in output.
            granule_ids: Specific granule concept IDs to process.
            granule_names: Specific granule names/filenames to process.
            output_format: Desired output format (e.g., "application/netcdf4").
            concatenate: If True, concatenate outputs into single file.
            max_results: Maximum number of granules to process.
            
        Returns:
            HarmonyJob with job status and metadata.
        """
        # Build the variable path for OGC Coverages API
        if variables:
            variable_path = ",".join(variables)
        else:
            variable_path = "all"
        
        url = (
            f"{self.BASE_URL}/{collection_id}/ogc-api-coverages/1.0.0/"
            f"collections/{variable_path}/coverage/rangeset"
        )
        
        # Build query parameters
        params: Dict[str, Any] = {}
        
        if bbox:
            west, south, east, north = bbox
            params["subset"] = [
                f"lon({west}:{east})",
                f"lat({south}:{north})",
            ]
        
        if temporal:
            start, end = temporal
            if "subset" not in params:
                params["subset"] = []
            params["subset"].append(f'time("{start}":"{end}")')
        
        if granule_ids:
            params["granuleId"] = granule_ids
        
        if granule_names:
            params["granuleName"] = granule_names
        
        if output_format:
            params["format"] = output_format
        
        if concatenate:
            params["concatenate"] = "true"
        
        if max_results:
            params["maxResults"] = max_results
        
        if self._skip_preview:
            params["skipPreview"] = "true"
        
        # Submit request
        response = self._session.get(url, params=params, timeout=self._timeout)
        response.raise_for_status()
        
        return self._parse_job_response(response.json())
    
    def get_job_status(self, job_id: str) -> HarmonyJob:
        """Get current status of a Harmony job.
        
        Args:
            job_id: Harmony job ID.
            
        Returns:
            HarmonyJob with current status.
        """
        url = f"{self.BASE_URL}/jobs/{job_id}"
        
        response = self._session.get(url, timeout=self._timeout)
        response.raise_for_status()
        
        return self._parse_job_response(response.json())
    
    def wait_for_job(
        self,
        job_id: str,
        poll_interval: float = 5.0,
        max_wait: float = 3600.0,
    ) -> HarmonyJob:
        """Wait for a Harmony job to complete.
        
        Args:
            job_id: Harmony job ID.
            poll_interval: Seconds between status checks.
            max_wait: Maximum seconds to wait before timeout.
            
        Returns:
            HarmonyJob with final status.
            
        Raises:
            TimeoutError: If job doesn't complete within max_wait.
            RuntimeError: If job fails.
        """
        start_time = time.time()
        
        while True:
            job = self.get_job_status(job_id)
            
            if job.is_complete:
                return job
            
            if job.is_failed:
                raise RuntimeError(
                    f"Harmony job {job_id} failed: {job.message}"
                )
            
            elapsed = time.time() - start_time
            if elapsed >= max_wait:
                raise TimeoutError(
                    f"Harmony job {job_id} did not complete within {max_wait} seconds"
                )
            
            time.sleep(poll_interval)
    
    def download_results(
        self,
        job: HarmonyJob,
        destination: str,
        skip_existing: bool = True,
    ) -> List[str]:
        """Download output files from a completed Harmony job.
        
        Args:
            job: Completed HarmonyJob.
            destination: Local directory to save files.
            skip_existing: Skip files that already exist locally.
            
        Returns:
            List of downloaded file paths.
        """
        from pathlib import Path
        
        dest_path = Path(destination)
        dest_path.mkdir(parents=True, exist_ok=True)
        
        downloaded = []
        
        for url in job.output_urls:
            filename = url.split("/")[-1].split("?")[0]
            local_path = dest_path / filename
            
            if skip_existing and local_path.exists():
                downloaded.append(str(local_path))
                continue
            
            response = self._session.get(url, stream=True, timeout=self._timeout)
            response.raise_for_status()
            
            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            downloaded.append(str(local_path))
        
        return downloaded
    
    def _parse_job_response(self, data: Dict[str, Any]) -> HarmonyJob:
        """Parse Harmony API response into HarmonyJob."""
        return HarmonyJob(
            job_id=data.get("jobID", ""),
            status=data.get("status", "unknown"),
            message=data.get("message", ""),
            progress=data.get("progress", 0),
            links=data.get("links", []),
            created_at=data.get("createdAt", ""),
            updated_at=data.get("updatedAt", ""),
        )
