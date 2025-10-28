"""
Data models for RS-Kit.

This module contains Pydantic models for query validation and data structures.
"""

from .extents import SpatialExtent, TemporalExtent

__all__ = [
    "SpatialExtent",
    "TemporalExtent",
]
