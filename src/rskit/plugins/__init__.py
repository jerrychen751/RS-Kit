"""
Plugin system for RS-Kit.

This module contains plugins for different data sources and processing backends.
"""

from ..core.registry import registry
from .nasa_earthdata.base import NasaEarthdata
from .aviso_altimetry.base import AvisoAltimetry


def list_supported_plugins():
    """Return the list of supported plugin identifiers."""
    return registry.get_supported_plugins()


def get_params_schema(source: str):
    """Return the params schema for a data source plugin."""
    return registry.get_params_schema(source)

__all__ = [
    "NasaEarthdata",
    "AvisoAltimetry",
    "list_supported_plugins",
    "get_params_schema",
]
