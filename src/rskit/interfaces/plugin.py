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
from typing import List, Dict, Optional, Any

from ..models.query import Query
from ..models.data_product import DataProduct


class DataSourcePlugin(ABC):
    name: str

    @abstractmethod
    def get_auth_schema(self) -> Dict[str, Any]:
        """Return the credentials schema required for authentication.

        Returns:
            Dict[str, Any]: A dictionary describing the required authentication parameters
            (e.g., username, password, token) and their properties (such as type, optionality).
        """
        ...
    
    @abstractmethod
    def discover(
        self,
        instrument: Optional[str] = None,
        variable: Optional[str] = None,
    ) -> str:
        """Discovers available data products across all instruments matching the specified criteria.
        
        Args:
            instrument (Optional[str]): Instrument name to filter by (e.g., "SWOT", "PACE").
                If None, returns products from all instruments.
            variable (Optional[str]): Variable name to filter by (e.g., "sea_surface_temperature").
                If None, returns all available variables.
        
        Returns:
            str: String representation of available data products.
        """
        ...
    
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