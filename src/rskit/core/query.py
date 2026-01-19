"""Query builder for fluent API."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, Any, Union, List
from datetime import datetime
from dateutil.parser import parse as parse_date

from .executor import QueryExecutor
from .registry import registry
from ..models.extents import SpatialExtent, TemporalExtent


class Query:
    """Fluent interface for building queries."""
    
    def __init__(self):
        """Initialize query builder."""
        self._registry = registry

        # Applies to most or all data sources
        self._source: Optional[str] = None
        self._spatial_extent: Optional[SpatialExtent] = None
        self._temporal_extent: Optional[TemporalExtent] = None
        self._params: Dict[str, Any] = {}

        # FTP servers
        self._data_path: Optional[str] = None
    
    # Public API methods
    def path(self, data_path: str) -> Query:
        self._data_path = data_path
        return self
    
    def region(
        self,
        lon: Optional[tuple] = None,
        lat: Optional[tuple] = None,
        bbox: Optional[tuple] = None
    ) -> Query:
        """Set spatial region. You can specify either both lon and lat or bbox.
        
        Args:
            lon (Optional[tuple]): (lon_min, lon_max) tuple.
            lat (Optional[tuple]): (lat_min, lat_max) tuple.
            bbox (Optional[tuple]): (lon_min, lat_min, lon_max, lat_max) tuple.
            
        Returns:
            (Query): Query instance for method chaining.
            
        Raises:
            ValueError: If neither bbox nor both lon and lat are specified.
        """
        if lon and lat:
            self._spatial_extent = SpatialExtent(
                lon_min=lon[0],
                lon_max=lon[1],
                lat_min=lat[0],
                lat_max=lat[1]
            )
        elif bbox:
            # bbox format: (lon_min, lat_min, lon_max, lat_max)
            self._spatial_extent = SpatialExtent(
                lon_min=bbox[0],
                lat_min=bbox[1], 
                lon_max=bbox[2],
                lat_max=bbox[3]
            )
        else:
            raise ValueError("Must specify either bbox or both lon and lat")
        
        return self
    
    def time(
        self,
        start: Union[str, datetime],
        end: Union[str, datetime]
    ) -> Query:
        """Set temporal range.
        
        Args:
            start (Union[str, datetime]): Start time. Recommended format: "YYYY-MM-DD" 
                (e.g., "2023-01-15"). For more precision, use "YYYY-MM-DD HH:MM:SS" 
                (e.g., "2023-01-15 14:30:00") or datetime object.
            end (Union[str, datetime]): End time. Recommended format: "YYYY-MM-DD" 
                (e.g., "2023-12-31"). For more precision, use "YYYY-MM-DD HH:MM:SS" 
                (e.g., "2023-12-31 23:59:59") or datetime object.
            
        Returns:
            (Query): Query instance for method chaining.
            
        Raises:
            ValueError: If date string cannot be parsed.
        """
        # Convert strings to datetime using flexible parsing
        if isinstance(start, str):
            try:
                start = parse_date(start)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Could not parse start time '{start}': {e}")
                
        if isinstance(end, str):
            try:
                end = parse_date(end)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Could not parse end time '{end}': {e}")
            
        self._temporal_extent = TemporalExtent(start=start, end=end)
        return self
    
    def with_params(self, **params) -> Query:
        """
        Add plugin-specific query parameters, some of which may be required by the active data source.

        Use rs.plugins.get_params_schema(data_source_str) to obtain a list of required and optional query params.
        
        Args:
            **params: Plugin-specific parameters.
            
        Returns:
            (Query): Query instance for method chaining.
        """
        self._params.update(params)
        return self


    # Calls methods from executor.py, which delegates to specific plugin-specific implementations
    def download(
        self,
        destination: Optional[Path] = None,
        *,
        limit: Optional[int] = None,
        skip_existing: bool = True,
    ) -> List[Path]:
        """Download data for the query via the registered plugin."""
        executor = QueryExecutor()
        return executor.download(
            self,
            destination=destination,
            limit=limit,
            skip_existing=skip_existing,
        )

    def require_extents(self) -> tuple[SpatialExtent, TemporalExtent]:
        """
        Ensures that both TemporalExtent and SpatialExtent objects have been associated with the query.
        """
        if self._spatial_extent is None:
            raise ValueError("Use .region() and pass in lon/lat ranges or a bbox tuple to attach a SpatialExtent object to the query first.")
        if self._temporal_extent is None:
            raise ValueError("Use .time() to pass in start and end times to attach a TemporalExtent object to the query first.")
        
        return self._spatial_extent, self._temporal_extent

    def estimate_size(self) -> Optional[int]:
        """Estimate query cost before execution.
        
        Returns:
            (Optional[int]): Estimated size in bytes, or None if unknown.
        """
        # TODO: Implement size estimation
        return None
    
    # Properties (read-only)
    @property
    def source(self) -> Optional[str]:
        return self._source
    
    @property
    def data_path(self) -> Optional[str]:
        return self._data_path
    
    @property
    def spatial_extent(self) -> Optional[SpatialExtent]:
        return self._spatial_extent
    
    @property
    def temporal_extent(self) -> Optional[TemporalExtent]:
        return self._temporal_extent
    
    @property
    def params(self) -> Dict[str, Any]:
        return self._params

    
    # Private methods
    def _from_source(self, source: str) -> Query:
        """
        Query from a single source.
        
        Args:
            source (str): Data source name (e.g., 'nasa_earthdata', 'aviso_altimetry').
            
        Returns:
            (Query): Query instance for method chaining.
        """
        self._source = source
        return self
