"""Comprehensive tests for CredentialManager class."""

import pytest
import json
from unittest.mock import Mock, patch

from rskit.auth.credential_manager import CredentialManager
from rskit.core.registry import registry


class TestCredentialManager:
    """Test cases for CredentialManager class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.credential_manager = CredentialManager()
        # Mock keyring to avoid actual OS keyring access
        self.keyring_patcher = patch('rskit.auth.credential_manager.keyring')
        self.mock_keyring = self.keyring_patcher.start()
        
        # Set up default mock behavior for keyring
        self.mock_keyring.get_password.return_value = json.dumps([])
        
        # Mock registry to avoid dependency on actual plugins
        self.registry_patcher = patch('rskit.auth.credential_manager.registry')
        self.mock_registry = self.registry_patcher.start()

    def teardown_method(self):
        """Clean up after each test method."""
        self.keyring_patcher.stop()
        self.registry_patcher.stop()

    def test_credential_manager_initialization(self):
        """Test that CredentialManager initializes correctly."""
        # Act
        manager = CredentialManager()
        
        # Assert
        assert manager.SERVICE_NAME == "rskit"
        assert manager._SOURCES_REGISTRY_KEY == "__sources__"

    def test_add_credential_exact_match(self):
        """Test adding credentials with exact source match."""
        # Arrange
        source = "nasa_earthdata"
        credentials = {"username": "test_user", "password": "test_pass", "token": "test_token"}
        self.mock_registry.match_source_name.return_value = source
        
        # Mock plugin instance and auth schema
        mock_plugin_instance = Mock()
        mock_plugin_instance.get_auth_schema.return_value = {
            "required_fields": ["username", "password", "token"]
        }
        self.mock_registry.match_plugin_class.return_value.return_value = mock_plugin_instance
        
        # Act
        self.credential_manager.add_credential(source, **credentials)
        
        # Assert
        self.mock_registry.match_source_name.assert_called_once_with(source)
        # Verify set_password is called twice: once for credentials, once for sources registry
        assert self.mock_keyring.set_password.call_count == 2
        # Verify the first call is for credentials
        self.mock_keyring.set_password.assert_any_call(
            self.credential_manager.SERVICE_NAME, 
            source, 
            json.dumps(credentials)
        )

    def test_add_credential_fuzzy_match(self):
        """Test adding credentials with fuzzy source match."""
        # Arrange
        input_source = "nasa_earth"
        matched_source = "nasa_earthdata"
        credentials = {"username": "test_user", "password": "test_pass", "token": "test_token"}
        self.mock_registry.match_source_name.return_value = matched_source
        
        # Mock plugin instance and auth schema
        mock_plugin_instance = Mock()
        mock_plugin_instance.get_auth_schema.return_value = {
            "required_fields": ["username", "password", "token"]
        }
        self.mock_registry.match_plugin_class.return_value.return_value = mock_plugin_instance
        
        # Act
        with patch('builtins.print') as mock_print:
            self.credential_manager.add_credential(input_source, **credentials)
        
        # Assert
        self.mock_registry.match_source_name.assert_called_once_with(input_source)
        mock_print.assert_called_once_with(f"Warning: '{input_source}' is not supported. Adding credential for '{matched_source}'.")
        # Verify set_password is called twice: once for credentials, once for sources registry
        assert self.mock_keyring.set_password.call_count == 2
        # Verify the first call is for credentials
        self.mock_keyring.set_password.assert_any_call(
            self.credential_manager.SERVICE_NAME, 
            input_source,  # Note: original source is used for storage
            json.dumps(credentials)
        )

    def test_add_credential_missing_required_field(self):
        """Test adding credentials with missing required field raises ValueError."""
        # Arrange
        source = "nasa_earthdata"
        credentials = {"username": "test_user", "password": "test_pass"}  # Missing token
        self.mock_registry.match_source_name.return_value = source
        
        # Mock plugin instance with auth schema requiring token
        mock_plugin_instance = Mock()
        mock_plugin_instance.get_auth_schema.return_value = {
            "required_fields": ["username", "password", "token"]
        }
        self.mock_registry.match_plugin_class.return_value.return_value = mock_plugin_instance
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            self.credential_manager.add_credential(source, **credentials)
        
        assert "Missing required credential field 'token'" in str(exc_info.value)
        assert "Required fields are: ['username', 'password', 'token']" in str(exc_info.value)

    def test_add_credential_extra_fields(self):
        """Test adding credentials with extra fields raises ValueError."""
        # Arrange
        source = "nasa_earthdata"
        credentials = {"username": "test_user", "password": "test_pass", "token": "test_token", "extra": "field"}
        self.mock_registry.match_source_name.return_value = source
        
        # Mock plugin instance with auth schema
        mock_plugin_instance = Mock()
        mock_plugin_instance.get_auth_schema.return_value = {
            "required_fields": ["username", "password", "token"]
        }
        self.mock_registry.match_plugin_class.return_value.return_value = mock_plugin_instance
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            self.credential_manager.add_credential(source, **credentials)
        
        assert "Number of provided credential fields (4) does not match the number of required fields (3)" in str(exc_info.value)

    def test_add_credential_no_auth_schema(self):
        """Test adding credentials when plugin has no auth schema raises ValueError."""
        # Arrange
        source = "nasa_earthdata"
        credentials = {"username": "test_user", "password": "test_pass"}
        self.mock_registry.match_source_name.return_value = source
        
        # Mock plugin instance without auth schema
        mock_plugin_instance = Mock()
        mock_plugin_instance.get_auth_schema.side_effect = AttributeError("No auth schema")
        self.mock_registry.match_plugin_class.return_value.return_value = mock_plugin_instance
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            self.credential_manager.add_credential(source, **credentials)
        
        assert f"Plugin for source '{source}' does not define an authentication schema" in str(exc_info.value)

    def test_get_credential_exact_match(self):
        """Test getting credentials with exact source match."""
        # Arrange
        source = "nasa_earthdata"
        credentials = {"username": "test_user", "password": "test_pass", "token": "test_token"}
        self.mock_registry.match_source_name.return_value = source
        self.mock_keyring.get_password.return_value = json.dumps(credentials)
        
        # Act
        result = self.credential_manager.get_credential(source)
        
        # Assert
        assert result == credentials
        self.mock_registry.match_source_name.assert_called_once_with(source)
        self.mock_keyring.get_password.assert_called_once_with(
            self.credential_manager.SERVICE_NAME, 
            source
        )

    def test_get_credential_fuzzy_match(self):
        """Test getting credentials with fuzzy source match."""
        # Arrange
        input_source = "nasa_earth"
        matched_source = "nasa_earthdata"
        credentials = {"username": "test_user", "password": "test_pass", "token": "test_token"}
        self.mock_registry.match_source_name.return_value = matched_source
        self.mock_keyring.get_password.return_value = json.dumps(credentials)
        
        # Act
        with patch('builtins.print') as mock_print:
            result = self.credential_manager.get_credential(input_source)
        
        # Assert
        assert result == credentials
        self.mock_registry.match_source_name.assert_called_once_with(input_source)
        mock_print.assert_called_once_with(f"Warning: '{input_source}' is not supported. Getting credentials for '{matched_source}'.")
        self.mock_keyring.get_password.assert_called_once_with(
            self.credential_manager.SERVICE_NAME, 
            matched_source
        )

    def test_get_credential_not_found(self):
        """Test getting credentials when not found returns None."""
        # Arrange
        source = "nasa_earthdata"
        self.mock_registry.match_source_name.return_value = source
        self.mock_keyring.get_password.return_value = None
        
        # Act
        result = self.credential_manager.get_credential(source)
        
        # Assert
        assert result is None

    def test_get_credential_invalid_json(self):
        """Test getting credentials with invalid JSON raises JSONDecodeError."""
        # Arrange
        source = "nasa_earthdata"
        self.mock_registry.match_source_name.return_value = source
        self.mock_keyring.get_password.return_value = "invalid json"
        
        # Act & Assert
        with pytest.raises(json.JSONDecodeError):
            self.credential_manager.get_credential(source)

    def test_remove_credential_exact_match(self):
        """Test removing credentials with exact source match."""
        # Arrange
        source = "nasa_earthdata"
        self.mock_registry.match_source_name.return_value = source
        self.mock_keyring.get_password.return_value = json.dumps([source])
        
        # Act
        self.credential_manager.remove_credential(source)
        
        # Assert
        self.mock_registry.match_source_name.assert_called_once_with(source)
        self.mock_keyring.delete_password.assert_called_once_with(
            self.credential_manager.SERVICE_NAME, 
            source
        )

    def test_remove_credential_fuzzy_match_warning(self):
        """Test removing credentials with fuzzy match shows warning and doesn't delete."""
        # Arrange
        input_source = "nasa_earth"
        matched_source = "nasa_earthdata"
        self.mock_registry.match_source_name.return_value = matched_source
        
        # Act
        with patch('builtins.print') as mock_print:
            self.credential_manager.remove_credential(input_source)
        
        # Assert
        self.mock_registry.match_source_name.assert_called_once_with(input_source)
        # Verify both warning messages are printed
        assert mock_print.call_count == 2
        mock_print.assert_any_call(f"Warning: '{input_source}' is not supported. Did you want to remove the credential for '{matched_source}'?")
        mock_print.assert_any_call("No credential was deleted. Please specify the exact source name to delete.")
        self.mock_keyring.delete_password.assert_not_called()

    def test_remove_credential_exact_match_updates_registry(self):
        """Test removing credentials updates the sources registry."""
        # Arrange
        source = "nasa_earthdata"
        sources = ["nasa_earthdata", "aviso_altimetry"]
        self.mock_registry.match_source_name.return_value = source
        self.mock_keyring.get_password.return_value = json.dumps(sources)
        
        # Act
        self.credential_manager.remove_credential(source)
        
        # Assert
        expected_sources = ["aviso_altimetry"]
        self.mock_keyring.set_password.assert_called_once_with(
            self.credential_manager.SERVICE_NAME,
            self.credential_manager._SOURCES_REGISTRY_KEY,
            json.dumps(sorted(expected_sources))
        )

    def test_list_credentials_empty(self):
        """Test listing credentials when none exist returns empty list."""
        # Arrange
        self.mock_keyring.get_password.return_value = None
        
        # Act
        result = self.credential_manager.list_credentials()
        
        # Assert
        assert result == []

    def test_list_credentials_with_data(self):
        """Test listing credentials returns stored sources."""
        # Arrange
        sources = ["nasa_earthdata", "aviso_altimetry"]
        self.mock_keyring.get_password.return_value = json.dumps(sources)
        
        # Act
        result = self.credential_manager.list_credentials()
        
        # Assert
        assert result == sources

    def test_list_credentials_invalid_json(self):
        """Test listing credentials with invalid JSON returns empty list."""
        # Arrange
        self.mock_keyring.get_password.return_value = "invalid json"
        
        # Act
        result = self.credential_manager.list_credentials()
        
        # Assert
        assert result == []

    def test_add_credential_updates_sources_registry(self):
        """Test that adding credentials updates the sources registry."""
        # Arrange
        source = "nasa_earthdata"
        credentials = {"username": "test_user", "password": "test_pass", "token": "test_token"}
        existing_sources = ["aviso_altimetry"]
        
        self.mock_registry.match_source_name.return_value = source
        self.mock_keyring.get_password.return_value = json.dumps(existing_sources)
        
        # Mock plugin instance and auth schema
        mock_plugin_instance = Mock()
        mock_plugin_instance.get_auth_schema.return_value = {
            "required_fields": ["username", "password", "token"]
        }
        self.mock_registry.match_plugin_class.return_value.return_value = mock_plugin_instance
        
        # Act
        self.credential_manager.add_credential(source, **credentials)
        
        # Assert
        expected_sources = ["aviso_altimetry", "nasa_earthdata"]
        self.mock_keyring.set_password.assert_any_call(
            self.credential_manager.SERVICE_NAME,
            self.credential_manager._SOURCES_REGISTRY_KEY,
            json.dumps(sorted(expected_sources))
        )

    def test_credential_manager_service_name_constant(self):
        """Test that SERVICE_NAME constant is correct."""
        # Act & Assert
        assert CredentialManager.SERVICE_NAME == "rskit"

    def test_credential_manager_sources_registry_key_constant(self):
        """Test that _SOURCES_REGISTRY_KEY constant is correct."""
        # Act & Assert
        assert CredentialManager._SOURCES_REGISTRY_KEY == "__sources__"

    @pytest.mark.parametrize("source_name,expected_match", [
        ("nasa_earthdata", "nasa_earthdata"),
        ("NASA_EARTHDATA", "nasa_earthdata"),
        ("nasa_earth", "nasa_earthdata"),
        ("aviso_altimetry", "aviso_altimetry"),
        ("AVISO_ALTIMETRY", "aviso_altimetry"),
        ("aviso", "aviso_altimetry"),
    ])
    def test_add_credential_parametrized(self, source_name, expected_match):
        """Test add_credential with various source names."""
        # Arrange
        credentials = {"username": "test_user", "password": "test_pass", "token": "test_token"}
        self.mock_registry.match_source_name.return_value = expected_match
        
        # Mock plugin instance and auth schema
        mock_plugin_instance = Mock()
        mock_plugin_instance.get_auth_schema.return_value = {
            "required_fields": ["username", "password", "token"]
        }
        self.mock_registry.match_plugin_class.return_value.return_value = mock_plugin_instance
        
        # Act
        self.credential_manager.add_credential(source_name, **credentials)
        
        # Assert
        self.mock_registry.match_source_name.assert_called_once_with(source_name)

    def test_credential_manager_error_handling(self):
        """Test error handling in credential operations."""
        # Arrange
        source = "nasa_earthdata"
        self.mock_registry.match_source_name.side_effect = ValueError("Unknown source")
        
        # Act & Assert
        with pytest.raises(ValueError):
            self.credential_manager.add_credential(source, username="test")

    def test_credential_manager_json_serialization(self):
        """Test that credentials are properly JSON serialized."""
        # Arrange
        source = "nasa_earthdata"
        credentials = {
            "username": "test_user",
            "password": "test_pass",
            "token": "test_token"
        }
        self.mock_registry.match_source_name.return_value = source
        
        # Mock plugin instance and auth schema
        mock_plugin_instance = Mock()
        mock_plugin_instance.get_auth_schema.return_value = {
            "required_fields": ["username", "password", "token"]
        }
        self.mock_registry.match_plugin_class.return_value.return_value = mock_plugin_instance
        
        # Act
        self.credential_manager.add_credential(source, **credentials)
        
        # Assert
        # Verify set_password is called twice: once for credentials, once for sources registry
        assert self.mock_keyring.set_password.call_count == 2
        # Verify the first call is for credentials
        self.mock_keyring.set_password.assert_any_call(
            self.credential_manager.SERVICE_NAME,
            source,
            json.dumps(credentials)
        )

    def test_credential_manager_thread_safety(self):
        """Test basic thread safety of credential operations."""
        import threading
        import time
        
        # Arrange
        source = "nasa_earthdata"
        credentials = {"username": "test_user", "password": "test_pass", "token": "test_token"}
        self.mock_registry.match_source_name.return_value = source
        
        # Mock plugin instance and auth schema
        mock_plugin_instance = Mock()
        mock_plugin_instance.get_auth_schema.return_value = {
            "required_fields": ["username", "password", "token"]
        }
        self.mock_registry.match_plugin_class.return_value.return_value = mock_plugin_instance
        
        results = []
        
        def worker():
            """Worker function for thread testing."""
            try:
                self.credential_manager.add_credential(source, **credentials)
                results.append("success")
            except Exception as e:
                results.append(f"Error: {e}")
        
        # Act
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Assert
        assert len(results) == 5
        assert all(result == "success" for result in results)

    def test_credential_manager_memory_efficiency(self):
        """Test that credential manager doesn't create unnecessary objects."""
        # Arrange
        source = "nasa_earthdata"
        credentials = {"username": "test_user", "password": "test_pass", "token": "test_token"}
        self.mock_registry.match_source_name.return_value = source
        
        # Mock plugin instance and auth schema
        mock_plugin_instance = Mock()
        mock_plugin_instance.get_auth_schema.return_value = {
            "required_fields": ["username", "password", "token"]
        }
        self.mock_registry.match_plugin_class.return_value.return_value = mock_plugin_instance
        
        # Act
        self.credential_manager.add_credential(source, **credentials)
        
        # Assert - Verify that JSON serialization is called only once
        assert self.mock_keyring.set_password.call_count == 2  # Once for credentials, once for sources registry
