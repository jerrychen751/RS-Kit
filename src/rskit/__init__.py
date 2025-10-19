"""
RS-Kit: Remote Sensing Data Query and Processing Toolkit

A unified toolkit for querying and processing remote sensing data from multiple sources.
"""

__version__ = "0.1.0"
__author__ = "RS-Kit Team"
__email__ = "contact@rskit.dev"

# Import main classes for easy access
from .models.query import Query, SpatialExtent, TemporalExtent

__all__ = [
    "Query",
    "SpatialExtent", 
    "TemporalExtent",
]
