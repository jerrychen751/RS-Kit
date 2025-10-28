"""
RS-Kit: Remote Sensing Data Query and Processing Toolkit

A unified toolkit for querying and processing remote sensing data from multiple sources.
"""

__version__ = "1.0.0"

# Import main classes for easy access
from .models.query import Query, SpatialExtent, TemporalExtent
from .api import query

__all__ = [
    "Query",
    "SpatialExtent", 
    "TemporalExtent",
    "query",
]