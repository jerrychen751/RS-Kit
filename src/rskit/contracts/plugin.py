"""
Base plugin interface for data sources.

Each plugin represents a data source (e.g., NASA Earthdata, AVISO)
rather than individual instruments (SWOT, PACE). Within each data source, 
there can be instrument-specific configurations.

Structure:
    plugins/my_source/
    ├── base.py          # Main plugin (inherits DataSourcePlugin)
    ├── config.py        # Source settings (URLs, rate limits)
    └── instruments/     # Optional: instrument metadata
        ├── swot.py      # Collections, variable mappings
        └── pace.py
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any
import xarray as xr

from ..core.query import Query


class DataSourcePlugin(ABC):
    CREDENTIAL_SCHEMA: Dict[str, Any] = {}
    PARAMS_SCHEMA: Dict[str, Any] = {}

    @classmethod
    def get_credential_schema(cls) -> Dict[str, Any]:
        """Return the credential schema required for authentication.

        Returns:
            Dict[str, Any]: A dictionary describing the required credential parameters
            (e.g., username, password, token) and their properties (such as type, optionality).
        """
        return cls.CREDENTIAL_SCHEMA

    @classmethod
    def get_params_schema(cls) -> Dict[str, Any]:
        """Return the schema for plugin-specific query parameters.

        Returns:
            Dict[str, Any]: A dictionary describing required and optional query parameters
            specific to the plugin (e.g., collection identifiers, product codes).
            Common keys include required_fields, required_any_of, optional_fields,
            field_descriptions, and notes.
        """
        return cls.PARAMS_SCHEMA
    
    @abstractmethod
    def supports_variable(self, variable: str) -> bool:
        """Check if this source supports a given variable.
        
        Args:
            variable (str): Dataset-specific variable name (e.g., 'sst', 'thetao').
            
        Returns:
            (bool): True if the variable is supported.
        """
        ...
    
    def estimate_size(self, query: Query) -> Optional[int]:
        """Estimate download size in bytes.
        
        Args:
            query (Query): Query to estimate.
            
        Returns:
            (int): Estimated size in bytes, or None if unknown.
        """
        ...
    
    @abstractmethod
    def download(
        self,
        query: Query,
        destination: Optional[Path] = None,
        *,
        limit: Optional[int] = None,
        skip_existing: bool = True,
    ) -> List[Path]:
        """Download data files for the query.
        
        Plugins must implement this to support file downloads. If a source does not
        provide raw downloads, it should raise NotImplementedError.
        """
        ...

    @abstractmethod
    def fetch(
        self,
        query: Query,
        destination: Optional[Path] = None,
        *,
        limit: Optional[int] = None,
        skip_existing: bool = True,
        **kwargs: Any,
    ) -> xr.Dataset:
        """Fetch data for the given query, downloading if necessary.
        """
        ...
