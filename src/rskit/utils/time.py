"""Time-related utility functions."""

import re
from datetime import datetime
from typing import Sequence
import numpy as np
import pandas as pd
import xarray as xr


def parse_doi(doi_link: str) -> str:
    """Parse the full DOI link to get the DOI. If already just a DOI, return the DOI.
    
    Args:
        doi_link (str): Full DOI link or just DOI string.
        
    Returns:
        str: The DOI string.
    """
    if "doi.org" in doi_link:
        return doi_link.split("doi.org/")[1]
    else:
        return doi_link


def parse_time(local_filepath: str) -> tuple[datetime, datetime]:
    """Return start and end times of data collection for a file given the local path.
    
    Args:
        local_filepath (str): Path to the local data file.
        
    Returns:
        tuple[datetime, datetime]: Start and end times.
        
    Raises:
        ValueError: If start and end time metadata could not be found.
    """
    ds = xr.open_dataset(local_filepath)
    start_time = ds.attrs.get('time_coverage_start')
    end_time = ds.attrs.get('time_coverage_end')

    if start_time and end_time:
        return datetime.fromisoformat(start_time), datetime.fromisoformat(end_time)
    else:
        raise ValueError(f"The start and end time metadata could not be found within the dataset attributes of {local_filepath}.")


def parse_start_time(download_url: str) -> datetime:
    """Return start time of data granule given download url.
    
    Args:
        download_url (str): Download URL containing timestamp in filename.
        
    Returns:
        datetime: Start time parsed from filename.
        
    Raises:
        ValueError: If no valid datetime pattern found or parsing fails.
    """
    filename = download_url.rsplit("/", 1)[-1]
    pattern = r"\d{8}T\d{6}"

    match = re.search(pattern, filename)
    if match:
        time_str = match.group(0)
        try:
            return datetime.strptime(time_str, "%Y%m%dT%H%M%S")
        except ValueError as e:
            raise ValueError(f"Failed to parse datetime from '{time_str}' in filename '{filename}': {e}")
    else:
        raise ValueError(f"No valid datetime pattern found in filename '{filename}'.")


def get_mid_time(local_filepath: str) -> datetime:
    """Return the middle time between start and end times.
    
    Args:
        local_filepath (str): Path to the local data file.
        
    Returns:
        datetime: Middle time between start and end.
    """
    start_time, end_time = parse_time(local_filepath)
    return start_time + (end_time - start_time) / 2


def calculate_timestep(times: np.ndarray) -> np.floating:
    """Calculates the average timestep between consecutive time measurements.

    Args:
        times (np.ndarray): An array of datetime-like objects.

    Returns:
        np.floating: The average timestep in seconds.
    """
    time_dt = pd.to_datetime(times)
    time_diffs = np.diff(time_dt)
    time_diffs_seconds = np.array([td / np.timedelta64(1, 's') for td in time_diffs])
    return np.mean(time_diffs_seconds)


def parse_time_range(time_range: tuple[str, str]) -> tuple[datetime, datetime]:
    """Parse time range strings into datetime objects.
    
    Args:
        time_range (tuple[str, str]): Tuple of start and end date strings in 'YYYY-MM-DD' format.
        
    Returns:
        tuple[datetime, datetime]: Start and end datetime objects.
        
    Raises:
        ValueError: If time range format is invalid.
    """
    try:
        time_start = datetime.strptime(time_range[0], "%Y-%m-%d")
        time_end = datetime.strptime(time_range[1] + " 23:59:59", "%Y-%m-%d %H:%M:%S")
        return time_start, time_end
    except ValueError as e:
        raise ValueError(f"Invalid time range format. Use 'YYYY-MM-DD': {e}")


def get_time_range(file_paths: list[str]) -> tuple[datetime, datetime]:
    """Extracts the time range from a list of SWOT data file paths.

    Args:
        file_paths (list[str]): A list of file paths.

    Returns:
        tuple[datetime, datetime]: The start and end times.
        
    Raises:
        ValueError: If no valid time information found in file names.
    """
    import os
    
    file_names = [os.path.basename(f) for f in file_paths]
    regex_pattern = r"(\d{8}T\d{6})"
    
    all_times = [
        datetime.strptime(t, "%Y%m%dT%H%M%S")
        for filename in file_names
        for t in re.findall(regex_pattern, filename)
    ]

    if not all_times:
        raise ValueError("No valid time information found in file names.")
        
    return min(all_times), max(all_times)
