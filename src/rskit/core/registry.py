"""Plugin registry for managing data source plugins."""

from __future__ import annotations

import difflib
from importlib import import_module
from typing import Dict, List, Optional, Tuple, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from ..contracts.plugin import DataSourcePlugin

PluginSpec = Tuple[str, str]


class PluginRegistry:
    """
    Manages data source plugins and supported source discovery.
    """

    def __init__(self) -> None:
        # Map plugin source name to import path and class name
        self._plugin_specs: Dict[str, PluginSpec] = {
            "nasa_earthdata": ("rskit.plugins.nasa_earthdata.base", "NasaEarthdata"),
            "aviso_altimetry": ("rskit.plugins.aviso_altimetry.base", "AvisoAltimetry"),
        }
        # Map plugin source name to class
        self._plugins: Dict[str, Type["DataSourcePlugin"]] = {}

    # Public API methods
    def get_supported_sources(self) -> List[str]:
        """
        Returns a list of all supported data source identifiers.

        Returns:
            List[str]: A copy of the list of supported sources.
        """
        return list(self._plugin_specs.keys())
    
    def get_plugin(self, source: str) -> Optional[DataSourcePlugin]:
        """
        Get a plugin instance for the specified source.
        
        Args:
            source (str): Data source identifier. Use `get_supported_sources()` to see supported data sources.
            
        Returns:
            Optional[DataSourcePlugin]: Plugin instance, or None if source not found.
        """
        try:
            plugin_class = self._get_plugin_class(source)
            return plugin_class()
        except ValueError:
            return None

    def get_credential_schema(self, source: str) -> Dict[str, object]:
        """
        Return the credential schema for a given data source, which dictates the credential fields required to authenticate against a data source.

        Args:
            source (str): Data source identifier.

        Returns:
            Dict[str, object]: Plugin-defined credential schema.

        Raises:
            ValueError: If the source is unknown or the plugin does not define a credential schema.
        """
        # Resolve and warn if fuzzy-matched
        matched_source = self._match_source_name(source)
        if matched_source != source:
            print(
                f"Warning: '{source}' is not supported. Getting credential schema for '{matched_source}'."
            )

        plugin_class = self._get_plugin_class(matched_source)

        if not hasattr(plugin_class, "get_credential_schema"):
            raise ValueError(
                f"Plugin for source '{source}' does not define a credential schema."
            )

        schema = plugin_class.get_credential_schema()
        if not isinstance(schema, dict):
            raise ValueError(
                f"Credential schema for source '{source}' must be a dict, got {type(schema).__name__}."
            )
        return schema

    def get_params_schema(self, source: str) -> Dict[str, object]:
        """
        Return the query parameter schema for a given data source, describing plugin-specific
        parameters required by the source.

        Args:
            source (str): Data source identifier.

        Returns:
            Dict[str, object]: Plugin-defined params schema.

        Raises:
            ValueError: If the source is unknown or the plugin does not define a params schema.
        """
        matched_source = self._match_source_name(source)
        if matched_source != source:
            print(
                f"Warning: '{source}' is not supported. Getting params schema for '{matched_source}'."
            )

        plugin_class = self._get_plugin_class(matched_source)
        if not hasattr(plugin_class, "get_params_schema"):
            raise ValueError(
                f"Plugin for source '{source}' does not define a params schema."
            )

        schema = plugin_class.get_params_schema()
        if not isinstance(schema, dict):
            raise ValueError(
                f"Params schema for source '{source}' must be a dict, got {type(schema).__name__}."
            )
        return schema

    # Private helper methods
    def _match_source_name(self, source: str) -> str:
        """
        Finds the closest matching supported data source.

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

    def _get_plugin_class(self, source: str) -> Type["DataSourcePlugin"]:
        """
        Return the plugin class for a source, resolving matches and caching if needed.
        """
        matched_source = self._match_source_name(source)

        if matched_source not in self._plugins:
            module_path, class_name = self._plugin_specs[matched_source]
            module = import_module(module_path)
            plugin_class = getattr(module, class_name)
            self._plugins[matched_source] = plugin_class

        return self._plugins[matched_source]


# Create a singleton instance (assigned/instantiated upon import)
registry = PluginRegistry()

__all__ = ['registry']
