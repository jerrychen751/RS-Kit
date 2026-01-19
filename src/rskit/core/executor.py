"""Query executor for orchestrating data downloads."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

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
        limit: Optional[int] = None,
        skip_existing: bool = True,
    ) -> List[Path]:
        plugin = self._get_plugin(query)

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
