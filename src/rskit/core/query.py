"""Query builder for fluent API."""

from __future__ import annotations

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import xarray as xr
from dateutil.parser import parse as parse_date

from ..models.extents import SpatialExtent, TemporalExtent
from .registry import PluginRegistry


class Query:
    """Fluent interface for building queries."""
    
    def __init__(self, registry: Optional[PluginRegistry] = None):
        """Initialize query builder.
        
        Args:
            registry (Optional[PluginRegistry]): Plugin registry instance.
        """
        self._variable: Optional[str] = None
        self._region: Optional[SpatialExtent] = None
        self._temporal: Optional[TemporalExtent] = None
        self._sources: List[str] = []
        self._options: Dict[str, Any] = {}
        self._registry = registry or PluginRegistry()
    
    def variable(self, name: str) -> Query:
        """Set the variable to query.
        
        Args:
            name (str): Dataset-specific variable name.
            
        Returns:
            (Query): Query instance for method chaining.
        """
        self._variable = name
        return self
    
    def region(
        self,
        lon: Optional[tuple] = None,
        lat: Optional[tuple] = None,
        bbox: Optional[tuple] = None,
        **kwargs
    ) -> Query:
        """Set spatial region.
        
        Args:
            lon (Optional[tuple]): (lon_min, lon_max) tuple.
            lat (Optional[tuple]): (lat_min, lat_max) tuple.
            bbox (Optional[tuple]): (lon_min, lat_min, lon_max, lat_max) tuple.
            **kwargs: Additional arguments for SpatialExtent.
            
        Returns:
            (Query): Query instance for method chaining.
            
        Raises:
            ValueError: If neither bbox nor both lon and lat are specified.
        """
        if bbox:
            # bbox format: (lon_min, lat_min, lon_max, lat_max)
            self._region = SpatialExtent(
                lon_min=bbox[0],
                lat_min=bbox[1], 
                lon_max=bbox[2],
                lat_max=bbox[3],
                **kwargs
            )
        elif lon and lat:
            self._region = SpatialExtent(
                lon_min=lon[0],
                lon_max=lon[1],
                lat_min=lat[0],
                lat_max=lat[1],
                **kwargs
            )
        else:
            raise ValueError("Must specify either bbox or both lon and lat")
        
        return self
    
    def time(
        self,
        start: Union[str, datetime],
        end: Union[str, datetime],
        **kwargs
    ) -> Query:
        """Set temporal range.
        
        Args:
            start (Union[str, datetime]): Start time (flexible string format or datetime).
            end (Union[str, datetime]): End time (flexible string format or datetime).
            **kwargs: Additional arguments for TemporalExtent.
            
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
            
        self._temporal = TemporalExtent(start=start, end=end, **kwargs)
        return self
    
    def from_source(self, source: str) -> Query:
        """Query from a single source.
        
        Args:
            source (str): Data source name (e.g., 'noaa_oisst', 'cmems').
            
        Returns:
            (Query): Query instance for method chaining.
        """
        self._sources = [source]
        return self
    
    def from_sources(self, sources: List[str]) -> Query:
        """Query from multiple sources.
        
        Args:
            sources (List[str]): List of data source names.
            
        Returns:
            (Query): Query instance for method chaining.
        """
        self._sources = sources
        return self
    
    def with_options(self, **options) -> Query:
        """Add additional query options.
        
        Args:
            **options: Additional options to pass to the query.
            
        Returns:
            (Query): Query instance for method chaining.
        """
        self._options.update(options)
        return self
    
    # Properties for easy access by plugins
    @property
    def variable_name(self) -> Optional[str]:
        """Get the variable name."""
        return self._variable
    
    @property
    def spatial(self) -> Optional[SpatialExtent]:
        """Get the spatial extent."""
        return self._region
    
    @property
    def temporal(self) -> Optional[TemporalExtent]:
        """Get the temporal extent."""
        return self._temporal
    
    @property
    def sources(self) -> List[str]:
        """Get the data sources."""
        return self._sources
    
    @property
    def options(self) -> Dict[str, Any]:
        """Get the query options."""
        return self._options
    
    def execute(self) -> xr.Dataset:
        """Execute the query.
        
        Returns:
            (xr.Dataset): xarray.Dataset with the requested data.
            
        Raises:
            ValueError: If required fields are missing.
        """
        # Validate required fields
        if not self._variable:
            raise ValueError("Variable must be specified")
        if not self._region:
            raise ValueError("Spatial region must be specified")
        if not self._temporal:
            raise ValueError("Temporal range must be specified")
        if not self._sources:
            raise ValueError("At least one data source must be specified")
        
        # Execute query using the executor
        from .executor import QueryExecutor
        executor = QueryExecutor(self._registry)
        return executor.execute(self)
    
    def estimate_size(self) -> Optional[int]:
        """Estimate query cost before execution.
        
        Returns:
            (Optional[int]): Estimated size in bytes, or None if unknown.
        """
        from .executor import QueryExecutor
        executor = QueryExecutor(self._registry)
        return executor.estimate_size(self)