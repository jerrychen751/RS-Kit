"""
RS-Kit: Remote Sensing Data Query and Processing Toolkit

A unified toolkit for querying and processing remote sensing data from multiple sources.
"""

__version__ = "1.0.0"

# Import main classes for easy access
from . import auth
from .core.registry import registry
from .api import query

__all__ = [
    "query",
    "auth",
]