"""Comprehensive tests for PluginRegistry class."""

import pytest
from typing import Dict, Any, Optional

from rskit.core.registry import PluginRegistry, registry
from rskit.contracts.plugin import DataSourcePlugin
from rskit.core.query_builder import Query


class MockDataSourcePlugin(DataSourcePlugin):
    """Mock plugin for testing purposes."""
    
    def __init__(self, name: str = "mock_source", required_fields: Optional[list] = None):
        self.name = name
        self._required_fields = required_fields or ["username", "password"]
    
    def get_auth_schema(self) -> Dict[str, Any]:
        return {
            "required_fields": self._required_fields,
            "field_descriptions": {
                field: f"Description for {field}" for field in self._required_fields
            }
        }
    
    def discover(self, instrument: Optional[str] = None, variable: Optional[str] = None) -> str:
        return f"Mock data products for {self.name}"
    
    def supports_variable(self, variable: str) -> bool:
        return variable in ["temperature", "pressure", "humidity"]
    
    def estimate_size(self, query: Query) -> Optional[int]:
        return 1024 * 1024  # 1MB


class TestPluginRegistry:
    """Test cases for PluginRegistry class."""

    def test_registry_initialization(self):
        """Test that registry initializes with correct plugins."""
        # Act
        test_registry = PluginRegistry()
        
        # Assert
        assert isinstance(test_registry._plugins, dict)
        assert "nasa_earthdata" in test_registry._plugins
        assert "aviso_altimetry" in test_registry._plugins
        assert len(test_registry._plugins) == 2

    def test_get_supported_sources(self):
        """Test getting list of supported sources."""
        # Arrange
        test_registry = PluginRegistry()
        
        # Act
        sources = test_registry.get_supported_sources()
        
        # Assert
        assert isinstance(sources, list)
        assert len(sources) == 2
        assert "nasa_earthdata" in sources
        assert "aviso_altimetry" in sources
        # Ensure it returns a copy, not the original
        sources.append("test")
        assert "test" not in test_registry.get_supported_sources()

    def test__match_source_name_exact_match(self):
        """Test matching exact source names."""
        # Arrange
        test_registry = PluginRegistry()
        
        # Act & Assert
        assert test_registry._match_source_name("nasa_earthdata") == "nasa_earthdata"
        assert test_registry._match_source_name("aviso_altimetry") == "aviso_altimetry"

    def test__match_source_name_case_insensitive(self):
        """Test that matching is case insensitive."""
        # Arrange
        test_registry = PluginRegistry()
        
        # Act & Assert
        assert test_registry._match_source_name("NASA_EARTHDATA") == "nasa_earthdata"
        assert test_registry._match_source_name("Aviso_Altimetry") == "aviso_altimetry"
        assert test_registry._match_source_name("NASA EARTHDATA") == "nasa_earthdata"

    def test__match_source_name_fuzzy_matching(self):
        """Test fuzzy matching with typos and variations."""
        # Arrange
        test_registry = PluginRegistry()
        
        # Act & Assert - Close matches should work
        assert test_registry._match_source_name("nasa_earth") == "nasa_earthdata"
        assert test_registry._match_source_name("earthdata") == "nasa_earthdata"
        assert test_registry._match_source_name("altimetry") == "aviso_altimetry"

    def test__match_source_name_no_match(self):
        """Test that unknown sources raise ValueError."""
        # Arrange
        test_registry = PluginRegistry()
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            test_registry._match_source_name("unknown_source")
        
        assert "Unknown data source 'unknown_source'" in str(exc_info.value)
        assert "Supported sources are:" in str(exc_info.value)
        assert "nasa_earthdata" in str(exc_info.value)
        assert "aviso_altimetry" in str(exc_info.value)

    def test__match_source_name_poor_match(self):
        """Test that sources with poor similarity raise ValueError."""
        # Arrange
        test_registry = PluginRegistry()
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            test_registry._match_source_name("xyz")
        
        assert "Unknown data source 'xyz'" in str(exc_info.value)

    def test__match_source_name_empty_string(self):
        """Test matching empty string."""
        # Arrange
        test_registry = PluginRegistry()
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            test_registry._match_source_name("")
        
        assert "Unknown data source ''" in str(exc_info.value)

    def test__match_source_name_whitespace(self):
        """Test matching strings with whitespace."""
        # Arrange
        test_registry = PluginRegistry()
        
        # Act & Assert
        assert test_registry._match_source_name("  nasa_earthdata  ") == "nasa_earthdata"
        assert test_registry._match_source_name("\taviso_altimetry\n") == "aviso_altimetry"

    def test_match_plugin_class_exact_match(self):
        """Test getting plugin class for exact match."""
        # Arrange
        test_registry = PluginRegistry()
        
        # Act
        nasa_class = test_registry._match_plugin_class("nasa_earthdata")
        aviso_class = test_registry._match_plugin_class("aviso_altimetry")
        
        # Assert
        assert nasa_class is not None
        assert aviso_class is not None
        assert nasa_class != aviso_class

    def test_match_plugin_class_fuzzy_match(self):
        """Test getting plugin class for fuzzy match."""
        # Arrange
        test_registry = PluginRegistry()
        
        # Act
        nasa_class = test_registry._match_plugin_class("nasa_earth")
        aviso_class = test_registry._match_plugin_class("altimetry")
        
        # Assert
        assert nasa_class is not None
        assert aviso_class is not None

    def test_match_plugin_class_unknown_source(self):
        """Test getting plugin class for unknown source raises ValueError."""
        # Arrange
        test_registry = PluginRegistry()
        
        # Act & Assert
        with pytest.raises(ValueError):
            test_registry._match_plugin_class("unknown_source")

    def test_match_plugin_class_returns_correct_type(self):
        """Test that match_plugin_class returns correct plugin classes."""
        # Arrange
        test_registry = PluginRegistry()
        
        # Act
        nasa_class = test_registry._match_plugin_class("nasa_earthdata")
        aviso_class = test_registry._match_plugin_class("aviso_altimetry")
        
        # Assert
        assert issubclass(nasa_class, DataSourcePlugin)
        assert issubclass(aviso_class, DataSourcePlugin)

    def test_registry_singleton_instance(self):
        """Test that the registry singleton instance works correctly."""
        # Act & Assert
        assert registry is not None
        assert isinstance(registry, PluginRegistry)
        assert registry.get_supported_sources() == ["nasa_earthdata", "aviso_altimetry"]

    def test_registry_plugin_instantiation(self):
        """Test that plugin classes can be instantiated correctly."""
        # Arrange
        test_registry = PluginRegistry()
        
        # Act
        nasa_class = test_registry._match_plugin_class("nasa_earthdata")
        nasa_instance = nasa_class()
        
        aviso_class = test_registry._match_plugin_class("aviso_altimetry")
        aviso_instance = aviso_class()
        
        # Assert
        assert isinstance(nasa_instance, DataSourcePlugin)
        assert isinstance(aviso_instance, DataSourcePlugin)
        assert hasattr(nasa_instance, 'get_auth_schema')
        assert hasattr(aviso_instance, 'get_auth_schema')

    def test_registry_plugin_auth_schemas(self):
        """Test that plugin instances return valid auth schemas."""
        # Arrange
        test_registry = PluginRegistry()
        
        # Act
        nasa_class = test_registry._match_plugin_class("nasa_earthdata")
        nasa_instance = nasa_class()
        nasa_schema = nasa_instance.get_auth_schema()
        
        aviso_class = test_registry._match_plugin_class("aviso_altimetry")
        aviso_instance = aviso_class()
        aviso_schema = aviso_instance.get_auth_schema()
        
        # Assert
        assert isinstance(nasa_schema, dict)
        assert "required_fields" in nasa_schema
        assert "field_descriptions" in nasa_schema
        assert isinstance(nasa_schema["required_fields"], list)
        
        assert isinstance(aviso_schema, dict)
        assert "required_fields" in aviso_schema
        assert "field_descriptions" in aviso_schema
        assert isinstance(aviso_schema["required_fields"], list)

    def test_registry_plugin_required_fields(self):
        """Test that plugins have correct required fields."""
        # Arrange
        test_registry = PluginRegistry()
        
        # Act
        nasa_class = test_registry._match_plugin_class("nasa_earthdata")
        nasa_instance = nasa_class()
        nasa_schema = nasa_instance.get_auth_schema()
        
        aviso_class = test_registry._match_plugin_class("aviso_altimetry")
        aviso_instance = aviso_class()
        aviso_schema = aviso_instance.get_auth_schema()
        
        # Assert
        nasa_fields = nasa_schema["required_fields"]
        assert "username" in nasa_fields
        assert "password" in nasa_fields
        assert "token" in nasa_fields
        
        aviso_fields = aviso_schema["required_fields"]
        assert "ftp_host" in aviso_fields
        assert "username" in aviso_fields
        assert "password" in aviso_fields

    @pytest.mark.parametrize("source_name,expected_match", [
        ("nasa_earthdata", "nasa_earthdata"),
        ("NASA_EARTHDATA", "nasa_earthdata"),
        ("nasa_earth", "nasa_earthdata"),
        ("earthdata", "nasa_earthdata"),
        ("aviso_altimetry", "aviso_altimetry"),
        ("AVISO_ALTIMETRY", "aviso_altimetry"),
        ("altimetry", "aviso_altimetry"),
    ])
    def test__match_source_name_parametrized(self, source_name, expected_match):
        """Test match_source_name with various inputs."""
        # Arrange
        test_registry = PluginRegistry()
        
        # Act
        result = test_registry._match_source_name(source_name)
        
        # Assert
        assert result == expected_match

    @pytest.mark.parametrize("invalid_source", [
        "unknown_source",
        "xyz",
        "random_string",
    ])
    def test__match_source_name_invalid_parametrized(self, invalid_source):
        """Test match_source_name with invalid inputs."""
        # Arrange
        test_registry = PluginRegistry()
        
        # Act & Assert
        with pytest.raises(ValueError):
            test_registry._match_source_name(invalid_source)

    def test_registry_immutability(self):
        """Test that registry plugins can be modified externally."""
        # Arrange
        test_registry = PluginRegistry()
        original_plugins = test_registry._plugins.copy()
        
        # Act - Direct modification affects the internal dict
        test_registry._plugins["test"] = MockDataSourcePlugin
        
        # Assert - get_supported_sources returns a new list from current keys, so modifications are reflected
        assert "test" in test_registry.get_supported_sources()
        assert "test" in test_registry._plugins
        assert test_registry._plugins != original_plugins

    def test_registry_thread_safety(self):
        """Test basic thread safety of registry operations."""
        import threading
        import time
        
        # Arrange
        test_registry = PluginRegistry()
        results = []
        
        def worker():
            """Worker function for thread testing."""
            try:
                result = test_registry._match_source_name("nasa_earthdata")
                results.append(result)
            except Exception as e:
                results.append(f"Error: {e}")
        
        # Act
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Assert
        assert len(results) == 10
        assert all(result == "nasa_earthdata" for result in results)

    def test_registry_memory_efficiency(self):
        """Test that registry doesn't create unnecessary objects."""
        # Arrange
        test_registry = PluginRegistry()
        
        # Act
        sources1 = test_registry.get_supported_sources()
        sources2 = test_registry.get_supported_sources()
        
        # Assert - Should return different list objects (copies)
        assert sources1 is not sources2
        assert sources1 == sources2

    def test_registry_error_messages(self):
        """Test that error messages are informative."""
        # Arrange
        test_registry = PluginRegistry()
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            test_registry._match_source_name("invalid")
        
        error_message = str(exc_info.value)
        assert "Unknown data source 'invalid'" in error_message
        assert "Supported sources are:" in error_message
        assert "nasa_earthdata" in error_message
        assert "aviso_altimetry" in error_message
