from __future__ import annotations

from pydantic import BaseModel, ValidationInfo, Field, field_validator, model_validator
from datetime import datetime
from typing import Optional, List, Dict, Any

class Query(BaseModel):
    """
    Unified query object that translates to source-specific API calls.

    Validation happens automatically on instantiation.
    """
    variable: str = Field(..., description="Variable to query (e.g., 'sea_surface_temperature')")
    spatial: SpatialExtent = Field(..., description="Spatial extent of the query")
    temporal: TemporalExtent = Field(..., description="Temporal extent of the query")
    sources: List[str] = Field(default_factory=list, description="Data sources to query")
    options: Dict[str, Any] = Field(default_factory=dict, description="Additional query options")
    
    @model_validator(mode='after')
    def validate_query(self):
        """Validate the complete query."""
        if not self.sources:
            raise ValueError("At least one data source must be specified")
        return self

class SpatialExtent(BaseModel):
    """Spatial bounding box for data queries."""
    lon_min: float = Field(..., ge=-180, le=180)
    lon_max: float = Field(..., ge=-180, le=180)
    lat_min: float = Field(..., ge=-90, le=90)
    lat_max: float = Field(..., ge=-90, le=90)
    crs: str = Field(default="EPSG:4326", description="Coordinate reference system")

    @field_validator('lon_max')
    @classmethod
    def validate_lon_range(cls, v: float, info: ValidationInfo):
        """Ensure lon_max >= lon_min."""
        if 'lon_min' in info.data and v < info.data['lon_min']:
            raise ValueError(f"lon_max ({v}) must be >= lon_min ({info.data['lon_min']})")
        return v

    @field_validator('lat_max')
    @classmethod
    def validate_lat_range(cls, v: float, info: ValidationInfo):
        """Ensure lat_max >= lat_min."""
        if 'lat_min' in info.data and v <= info.data['lat_min']:
            raise ValueError(f"lat_max ({v}) must be > lat_min ({info.data['lat_min']})")
        return v

class TemporalExtent(BaseModel):
    """Temporal bounding box for data queries."""
    start: datetime = Field(..., description="Start time of the temporal extent")
    end: datetime = Field(..., description="End time of the temporal extent")
    # TODO: potentially add frequency

    @model_validator(mode='after') # validate after Pydantic performs type coercion
    def validate_temporal_extent(self):
        """Ensure end time is after start time."""
        if self.start > self.end:
            raise ValueError(f"start ({self.start}) must be before end ({self.end})")
        return self