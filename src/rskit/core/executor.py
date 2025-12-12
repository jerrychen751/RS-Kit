"""Query executor for orchestrating data downloads."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING, Any
import inspect

import xarray as xr

from .registry import registry

if TYPE_CHECKING:
    from ..contracts.plugin import DataSourcePlugin
    from .query import Query


class QueryExecutor:
    """Executes queries by coordinating with plugins."""

    def __init__(self) -> None:
        self._registry = registry

    # Public API methods
    def download(
        self,
        query: Query,
        destination: Optional[Path] = None,
        *,
        limit: Optional[int] = None,
        skip_existing: bool = True,
    ) -> List[Path]:
        plugin = self._get_plugin(query)
        self._validate_variable_support(plugin, query)

        try:
            return plugin.download(
                query,
                destination=destination,
                limit=limit,
                skip_existing=skip_existing,
            )
        except NotImplementedError as exc:
            raise NotImplementedError(
                f"Plugin '{query.source}' does not support download operations."
            ) from exc

    def fetch(
        self,
        query: Query,
        destination: Optional[Path] = None,
        *,
        limit: Optional[int] = None,
        skip_existing: bool = True,
        **plugin_kwargs: Any,
    ) -> xr.Dataset:
        plugin = self._get_plugin(query)
        self._validate_variable_support(plugin, query)

        try:
            return plugin.fetch(
                query,
                destination=destination,
                limit=limit,
                skip_existing=skip_existing,
                **plugin_kwargs,
            )
        except TypeError as exc:
            # Improve UX when a plugin doesn't accept a provided keyword.
            msg = str(exc)
            if "unexpected keyword argument" in msg and plugin_kwargs:
                try:
                    sig = inspect.signature(plugin.fetch)
                    supported = [
                        name
                        for name, param in sig.parameters.items()
                        if param.kind
                        in (
                            inspect.Parameter.POSITIONAL_OR_KEYWORD,
                            inspect.Parameter.KEYWORD_ONLY,
                        )
                        and name not in {"self", "query", "destination", "limit", "skip_existing"}
                    ]
                except Exception:
                    supported = []

                supported_hint = (
                    f" Supported plugin fetch options: {sorted(supported)}." if supported else ""
                )
                raise TypeError(
                    f"Plugin '{query.source}' does not support one or more provided fetch options: "
                    f"{sorted(plugin_kwargs.keys())}." + supported_hint
                ) from exc
            raise

    def execute(self, query: Query) -> xr.Dataset:
        warnings.warn(
            "QueryExecutor.execute() is deprecated. Use QueryExecutor.fetch() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.fetch(query)

    def estimate_size(self, query: Query) -> Optional[int]:
        plugin = self._registry.get_plugin(query.source) if query.source else None
        if plugin and hasattr(plugin, "estimate_size"):
            return plugin.estimate_size(query)
        return None

    # Private helper methods
    def _get_plugin(self, query: Query) -> DataSourcePlugin:
        if not query.source:
            raise ValueError("Data source must be specified.")

        plugin = self._registry.get_plugin(query.source)
        if not plugin:
            raise ValueError(f"No plugin found for source '{query.source}'.")

        return plugin

    @staticmethod
    def _validate_variable_support(plugin: DataSourcePlugin, query: Query) -> None:
        if query.variable_name and hasattr(plugin, "supports_variable"):
            if not plugin.supports_variable(query.variable_name):
                raise ValueError(
                    f"Variable '{query.variable_name}' not supported by source '{query.source}'."
                )
