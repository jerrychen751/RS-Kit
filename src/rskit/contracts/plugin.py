"""
Base plugin interface for data sources.

Each plugin represents a data source (e.g., NASA Earthdata, AVISO)
rather than individual instruments (SWOT, PACE). Within each data source, 
there can be instrument-specific configurations.

Structure:
    plugins/my_source/
    ├── base.py          # Main plugin (inherits DataSourcePlugin)
    ├── schema.json      # Credential + parameter schema
    ├── config.py        # Source settings (URLs, rate limits)
    └── instruments/     # Optional: instrument metadata
        ├── swot.py      # Collections, variable mappings
        └── pace.py
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

from ..core.query import Query


class DataSourcePlugin(ABC):
    @classmethod
    def _schema_path(cls) -> Optional[Path]:
        module = sys.modules.get(cls.__module__)
        module_file = getattr(module, "__file__", None)
        if not module_file:
            return None
        return Path(module_file).with_name("schema.json")

    @classmethod
    @lru_cache(maxsize=None)
    def _schema(cls) -> Dict[str, Any]:
        schema_path = cls._schema_path()
        if not schema_path or not schema_path.exists():
            return {}
        try:
            data = json.loads(schema_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid schema JSON for {cls.__name__}: {schema_path}"
            ) from exc
        if not isinstance(data, dict):
            raise ValueError(
                f"Schema JSON must be an object for {cls.__name__}: {schema_path}"
            )
        return data

    @classmethod
    def _schema_section(cls, key: str) -> Dict[str, Any]:
        schema = cls._schema()
        if not schema:
            return {}
        section = schema.get(key, {})
        if section is None:
            return {}
        if not isinstance(section, dict):
            schema_path = cls._schema_path()
            path_label = schema_path if schema_path else "<unknown>"
            raise ValueError(
                f"Schema section '{key}' must be an object for {cls.__name__}: {path_label}"
            )
        return section

    @classmethod
    def get_credential_schema(cls) -> Dict[str, Any]:
        """Return the credential schema required for authentication.

        Returns:
            Dict[str, Any]: A dictionary describing the required credential parameters
            (e.g., username, password, token) and their properties (such as type, optionality).
        """
        return cls._schema_section("credential_schema")

    @classmethod
    def get_params_schema(cls) -> Dict[str, Any]:
        """Return the schema for plugin-specific query parameters.

        Returns:
            Dict[str, Any]: A dictionary describing required and optional query parameters
            specific to the plugin (e.g., collection identifiers, product codes).
            Common keys include required_fields, required_any_of, optional_fields,
            field_descriptions, and notes.
        """
        return cls._schema_section("params_schema")
    
    def estimate_size(self, query: Query) -> Optional[int]:
        """Estimate download size in bytes.
        
        Args:
            query (Query): Query to estimate.
            
        Returns:
            (int): Estimated size in bytes, or None if unknown.
        """
        ...
    
    @abstractmethod
    def download_data(
        self,
        query: Query,
        destination: Optional[Path] = None,
        *,
        limit: Optional[int] = None,
        skip_existing: bool = True,
    ) -> List[Path]:
        """Download data files for the query.
        
        Plugins must implement this to support file downloads. If a source does not
        provide raw downloads, it should raise NotImplementedError.
        """
        ...
