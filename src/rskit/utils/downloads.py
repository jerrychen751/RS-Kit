"""
Download utilities for RS-Kit.

This module provides utilities for managing file downloads to the user's Downloads directory
with appropriate naming conventions based on data source and timestamp.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional


def create_download_folder(
    data_source: str,
    timestamp: Optional[datetime] = None
) -> Path:
    """Create a download folder in the user's Downloads directory.
    
    Args:
        data_source: Name of the data source (e.g., "aviso_altimetry", "nasa_earthdata").
        timestamp: Optional timestamp for folder naming. If None, uses current time.
        
    Returns:
        Path: Path to the created download folder.
    """
    downloads_dir = Path.home() / "Downloads"
    
    # Create folder with rskit- prefix and data source + timestamp
    if timestamp:
        folder_name = f"rskit-{data_source}-{timestamp.strftime('%Y%m%d_%H%M%S')}"
    else:
        folder_name = f"rskit-{data_source}-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    download_folder = downloads_dir / folder_name
    download_folder.mkdir(parents=True, exist_ok=True)
    
    return download_folder


def get_download_path(
    data_source: str,
    filename: str,
    timestamp: Optional[datetime] = None
) -> Path:
    """Get the full download path for a file.
    
    Args:
        data_source: Name of the data source.
        filename: Name of the file to download.
        timestamp: Optional timestamp for folder naming. If None, uses current time.
        
    Returns:
        Path: Full path where the file should be downloaded.
    """
    download_folder = create_download_folder(data_source, timestamp)
    return download_folder / filename


def ensure_downloads_directory() -> Path:
    """Ensure the Downloads directory exists and is accessible.
    
    Returns:
        Path: Path to the Downloads directory.
        
    Raises:
        OSError: If the Downloads directory cannot be created or accessed.
    """
    downloads_dir = Path.home() / "Downloads"
    
    try:
        downloads_dir.mkdir(parents=True, exist_ok=True)
        return downloads_dir
    except OSError as e:
        raise OSError(f"Cannot access or create Downloads directory: {e}")


def format_data_source_name(source: str) -> str:
    """Format a data source name for use in folder names.
    
    Args:
        source: Raw data source name.
        
    Returns:
        str: Formatted data source name suitable for folder names.
    """
    # Replace underscores with spaces and title case
    formatted = source.replace("_", " ").title()
    return formatted
