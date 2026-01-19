"""Client for NASA Harmony API for server-side data subsetting."""

from __future__ import annotations

import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from .base import GranuleSearchParams


@dataclass
class ProcessingJob:
    """Represents a Harmony processing job."""
    
    job_id: str
    status: str
    message: str
    progress: int
    links: List[Dict[str, str]]
    created_at: str
    updated_at: str
    username: str = ""
    request_url: str = ""
    data_expiration: str = ""
    num_input_granules: Optional[int] = None
    labels: List[str] = field(default_factory=list)
    
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
            if link.get("rel") == "data" and link.get("href")
        ]

    def get_link(self, rel: str) -> Optional[Dict[str, str]]:
        """Return the first link dictionary with the given rel."""
        for link in self.links:
            if link.get("rel") == rel:
                return link
        return None

    @property
    def cancel_url(self) -> Optional[str]:
        link = self.get_link("canceler")
        return link.get("href") if link else None

    @property
    def pause_url(self) -> Optional[str]:
        link = self.get_link("pauser")
        return link.get("href") if link else None


@dataclass
class DownloadProgress:
    """Represents progress for a single download URL."""

    url: str
    path: str
    bytes_downloaded: int
    total_bytes: Optional[int]
    done: bool = False
    skipped: bool = False


class HarmonyClient:
    
    BASE_URL = "https://harmony.earthdata.nasa.gov"
    
    def __init__(
        self,
        token: str,
        session: Optional[requests.Session] = None,
        timeout: int = 60,
    ) -> None:
        """Initialize Harmony client.
        
        Args:
            token: NASA Earthdata bearer token.
            session: Optional requests session for connection pooling.
            timeout: Request timeout in seconds.
        """
        self._token = token
        self._session = session or requests.Session()
        self._timeout = timeout
        
        self._session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        })

    def subset_and_download(
        self,
        params: GranuleSearchParams,
        destination: Path,
        *,
        poll_interval: float = 5.0,
        max_wait: float = 3600.0,
        skip_existing: bool = True,
        on_job_update: Optional[Callable[[ProcessingJob], None]] = None,
        on_download_progress: Optional[Callable[[DownloadProgress], None]] = None,
    ) -> List[Path]:
        job = self._request_subset(
            collection_id=params.collection_id,
            bbox=params.bbox,
            temporal=params.temporal,
        )
        
        if on_job_update:
            on_job_update(job)
        
        completed_job = self._await_job_completion(
            job.job_id,
            poll_interval=poll_interval,
            max_wait=max_wait,
            on_job_update=on_job_update,
        )
        
        return self.download_results(
            completed_job,
            str(destination),
            skip_existing=skip_existing,
            on_download_progress=on_download_progress,
        )        
    
    def _request_subset(
        self,
        collection_id: str,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        temporal: Optional[Tuple[str, str]] = None,
    ) -> ProcessingJob:
        """
        Submit a subsetting request to Harmony. Assumes the collection supports Harmony subsetting.
        
        Uses the OGC Coverages API for subsetting requests.
        
        Args:
            collection_id: CMR collection concept ID.
            bbox: Bounding box as (west, south, east, north) in degrees.
            temporal: Time range as (start, end) ISO 8601 strings.
            
        Returns:
            HarmonyJob with job status and metadata.
        """
        variables = "all" # comma-separated variables or "all"
        url = (
            f"{self.BASE_URL}/{collection_id}/ogc-api-coverages/1.0.0/"
            f"collections/{variables}/coverage/rangeset"
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
        
        
        # Submit request
        response = self._session.get(url, params=params, timeout=self._timeout)
        response.raise_for_status()
        
        return self._parse_job_response(response.json())
    
    def get_job_status(self, job_id: str) -> ProcessingJob:
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
    
    def _await_job_completion(
        self,
        job_id: str,
        poll_interval: float = 5.0,
        max_wait: float = 3600.0,
        on_job_update: Optional[Callable[[ProcessingJob], None]] = None,
    ) -> ProcessingJob:
        """
        Wait for a Harmony job to complete.
        
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
        last_state: Optional[Tuple[str, int, str]] = None
        
        while True:
            job = self.get_job_status(job_id)
            
            if on_job_update:
                state = (job.status, job.progress, job.updated_at)
                if state != last_state:
                    on_job_update(job)
                    last_state = state
            
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

    def cancel_job(self, job: ProcessingJob | str) -> ProcessingJob:
        """Cancel a Harmony job using the job's cancel link."""
        return self._follow_job_link(job, rel="canceler", action="cancel")

    def pause_job(self, job: ProcessingJob | str) -> ProcessingJob:
        """Pause a Harmony job using the job's pause link."""
        return self._follow_job_link(job, rel="pauser", action="pause")
    
    def download_results(
        self,
        job: ProcessingJob,
        destination: str,
        skip_existing: bool = True,
        on_download_progress: Optional[Callable[[DownloadProgress], None]] = None,
    ) -> List[Path]:
        """Download output files from a completed Harmony job.
        
        Args:
            job: Completed HarmonyJob.
            destination: Local directory to save files.
            skip_existing: Skip files that already exist locally.
            on_download_progress: Optional callback for download progress updates.
            
        Returns:
            List of downloaded file paths.
        """
        from pathlib import Path
        
        dest_path = Path(destination)
        dest_path.mkdir(parents=True, exist_ok=True)
        
        downloaded: List[Path] = []
        
        for url in job.output_urls:
            filename = url.split("/")[-1].split("?")[0]
            local_path = dest_path / filename
            
            if skip_existing and local_path.exists():
                downloaded.append(local_path)
                if on_download_progress:
                    size = local_path.stat().st_size
                    on_download_progress(
                        DownloadProgress(
                            url=url,
                            path=str(local_path),
                            bytes_downloaded=size,
                            total_bytes=size,
                            done=True,
                            skipped=True,
                        )
                    )
                continue
            
            response = self._session.get(url, stream=True, timeout=self._timeout)
            response.raise_for_status()
            
            total_bytes: Optional[int] = None
            if response.headers.get("Content-Length"):
                try:
                    total_bytes = int(response.headers["Content-Length"])
                except ValueError:
                    total_bytes = None
            
            downloaded_bytes = 0
            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_bytes += len(chunk)
                        if on_download_progress:
                            on_download_progress(
                                DownloadProgress(
                                    url=url,
                                    path=str(local_path),
                                    bytes_downloaded=downloaded_bytes,
                                    total_bytes=total_bytes,
                                )
                            )
            
            if on_download_progress:
                on_download_progress(
                    DownloadProgress(
                        url=url,
                        path=str(local_path),
                        bytes_downloaded=downloaded_bytes,
                        total_bytes=total_bytes,
                        done=True,
                    )
                )
            
            downloaded.append(local_path)
        
        return downloaded

    def _follow_job_link(self, job: ProcessingJob | str, rel: str, action: str) -> ProcessingJob:
        job_info = job if isinstance(job, ProcessingJob) else self.get_job_status(job)
        link = job_info.get_link(rel)
        if not link or not link.get("href"):
            raise ValueError(
                f"Harmony job {job_info.job_id} does not expose a {action} link."
            )
        
        response = self._session.post(link["href"], timeout=self._timeout)
        response.raise_for_status()
        
        if response.content:
            return self._parse_job_response(response.json())
        
        return self.get_job_status(job_info.job_id)
    
    def _parse_job_response(self, data: Dict[str, Any]) -> ProcessingJob:
        """Parse Harmony API response into HarmonyJob."""
        return ProcessingJob(
            job_id=data.get("jobID", ""),
            status=data.get("status", "unknown"),
            message=data.get("message", ""),
            progress=data.get("progress", 0),
            links=data.get("links", []),
            created_at=data.get("createdAt", ""),
            updated_at=data.get("updatedAt", ""),
            username=data.get("username", ""),
            request_url=data.get("request", ""),
            data_expiration=data.get("dataExpiration", ""),
            num_input_granules=data.get("numInputGranules"),
            labels=data.get("labels") or [],
        )
