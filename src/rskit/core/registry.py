"""Plugin registry for managing data source plugins."""

import difflib
from typing import Dict, List, Optional, Type

from ..interfaces.plugin import DataSourcePlugin
from ..plugins.nasa_earthdata.base import NasaEarthdata
from ..plugins.aviso_altimetry.base import AvisoAltimetry


class PluginRegistry:
    """Manages data source plugins and supported source discovery."""

    def __init__(self):
        """Initializes the plugin registry with supported data source identifiers."""
        self._plugins: Dict[str, Type[DataSourcePlugin]] = {
            "nasa_earthdata": NasaEarthdata,
            "aviso_altimetry": AvisoAltimetry
        }

    def match_source_name(self, source: str) -> str:
        """Finds the closest matching supported data source.

        Args:
            source (str): Data source identifier to match.

        Returns:
            str: The best-matched supported source.

        Raises:
            ValueError: If no supported source closely matches the input source.
        """
        source = source.lower()
        match: List[str] = difflib.get_close_matches(
            word=source,
            possibilities=self.get_supported_sources(),
            n=1,
            cutoff=0.7
        )

        if not match:
            supported = self.get_supported_sources()
            raise ValueError(
                f"Unknown data source '{source}'. Supported sources are: {supported}"
            )

        matched_source: str = match[0]
        return matched_source

    def match_plugin_class(self, source: str) -> Type[DataSourcePlugin]:
        """Get the plugin class for a matched source.

        Args:
            source (str): Data source identifier to match.

        Returns:
            Type[DataSourcePlugin]: The plugin class for the matched source.

        Raises:
            ValueError: If no supported source closely matches the input source.
        """
        name = self.match_source_name(source)
        return self._plugins[name]

    def get_supported_sources(self) -> List[str]:
        """Returns a list of all supported data source identifiers.

        Returns:
            List[str]: A copy of the list of supported sources.
        """
        return list(self._plugins.keys())

# Create a singleton instance (assigned/instantiated upon import)
registry = PluginRegistry()

__all__ = ['registry']