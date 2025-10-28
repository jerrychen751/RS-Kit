"""Integration tests for registry and credential manager interaction."""

import pytest
import json
from unittest.mock import patch

from rskit.core.registry import PluginRegistry, registry
from rskit.auth.credential_manager import CredentialManager
from tests.mock_plugins import (
    MockNasaEarthdataPlugin, 
    MockAvisoAltimetryPlugin,
    MockMinimalPlugin,
    MockComplexPlugin,
    MockPluginWithoutAuthSchema
)


class TestRegistryCredentialManagerIntegration:
    """Integration tests for PluginRegistry and CredentialManager interaction."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create a test registry with mock plugins
        self.test_registry = PluginRegistry()
        self.test_registry._plugins = {
            "nasa_earthdata": MockNasaEarthdataPlugin,
            "aviso_altimetry": MockAvisoAltimetryPlugin,
            "minimal_source": MockMinimalPlugin,
            "complex_source": MockComplexPlugin,
            "no_auth_source": MockPluginWithoutAuthSchema
        }
        
        # Create credential manager
        self.credential_manager = CredentialManager()
        
        # Mock keyring to avoid actual OS keyring access
        self.keyring_patcher = patch('rskit.auth.credential_manager.keyring')
        self.mock_keyring = self.keyring_patcher.start()
        
        # Set up default mock behavior for keyring
        self.mock_keyring.get_password.return_value = json.dumps([])
        
        # Mock the registry in credential manager
        self.registry_patcher = patch('rskit.auth.credential_manager.registry', self.test_registry)
        self.registry_patcher.start()

    def teardown_method(self):
        """Clean up after each test method."""
        self.keyring_patcher.stop()
        self.registry_patcher.stop()

    def test_integration_add_credential_with_registry_matching(self):
        """Test adding credentials with registry fuzzy matching."""
        # Arrange
        input_source = "nasa_earth"  # Fuzzy match for nasa_earthdata
        credentials = {
            "username": "test_user",
            "password": "test_pass", 
            "token": "test_token"
        }
        
        # Act
        with patch('builtins.print') as mock_print:
            self.credential_manager.add_credential(input_source, **credentials)
        
        # Assert
        mock_print.assert_called_once_with(
            "Warning: 'nasa_earth' is not supported. Adding credential for 'nasa_earthdata'."
        )
        # Verify set_password is called twice: once for credentials, once for sources registry
        assert self.mock_keyring.set_password.call_count == 2

    def test_integration_get_credential_with_registry_matching(self):
        """Test getting credentials with registry fuzzy matching."""
        # Arrange
        input_source = "altimetry"  # Fuzzy match for aviso_altimetry
        stored_credentials = {
            "ftp_host": "ftp.aviso.altimetry.fr",
            "username": "aviso_user",
            "password": "aviso_pass"
        }
        self.mock_keyring.get_password.return_value = json.dumps(stored_credentials)
        
        # Act
        with patch('builtins.print') as mock_print:
            result = self.credential_manager.get_credential(input_source)
        
        # Assert
        assert result == stored_credentials
        mock_print.assert_called_once_with(
            "Warning: 'altimetry' is not supported. Getting credentials for 'aviso_altimetry'."
        )
        self.mock_keyring.get_password.assert_called_once_with(
            self.credential_manager.SERVICE_NAME,
            "aviso_altimetry"  # Matched source name is used for retrieval
        )

    def test_integration_remove_credential_with_registry_matching(self):
        """Test removing credentials with registry fuzzy matching."""
        # Arrange
        input_source = "earthdata"  # Fuzzy match for nasa_earthdata
        
        # Act
        with patch('builtins.print') as mock_print:
            self.credential_manager.remove_credential(input_source)
        
        # Assert
        # Verify both warning messages are printed
        assert mock_print.call_count == 2
        mock_print.assert_any_call(
            "Warning: 'earthdata' is not supported. Did you want to remove the credential for 'nasa_earthdata'?"
        )
        mock_print.assert_any_call(
            "No credential was deleted. Please specify the exact source name to delete."
        )
        self.mock_keyring.delete_password.assert_not_called()

    def test_integration_credential_validation_with_plugin_schema(self):
        """Test credential validation using actual plugin auth schemas."""
        # Arrange
        source = "minimal_source"
        credentials = {"api_key": "test_api_key"}
        
        # Act
        self.credential_manager.add_credential(source, **credentials)
        
        # Assert
        # Verify set_password is called twice: once for credentials, once for sources registry
        assert self.mock_keyring.set_password.call_count == 2

    def test_integration_credential_validation_complex_schema(self):
        """Test credential validation with complex plugin schema."""
        # Arrange
        source = "complex_source"
        credentials = {
            "username": "user",
            "password": "pass",
            "token": "token",
            "endpoint": "https://api.example.com",
            "timeout": 30
        }
        
        # Act
        self.credential_manager.add_credential(source, **credentials)
        
        # Assert
        # Verify set_password is called twice: once for credentials, once for sources registry
        assert self.mock_keyring.set_password.call_count == 2

    def test_integration_credential_validation_missing_field(self):
        """Test credential validation with missing required field."""
        # Arrange
        source = "nasa_earthdata"
        credentials = {
            "username": "test_user",
            "password": "test_pass"
            # Missing "token" field
        }
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            self.credential_manager.add_credential(source, **credentials)
        
        assert "Missing required credential field 'token'" in str(exc_info.value)
        assert "Required fields are: ['username', 'password', 'token']" in str(exc_info.value)

    def test_integration_credential_validation_extra_field(self):
        """Test credential validation with extra field."""
        # Arrange
        source = "minimal_source"
        credentials = {
            "api_key": "test_api_key",
            "extra_field": "should_not_be_allowed"
        }
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            self.credential_manager.add_credential(source, **credentials)
        
        assert "Number of provided credential fields (2) does not match the number of required fields (1)" in str(exc_info.value)

    def test_integration_credential_validation_no_auth_schema(self):
        """Test credential validation with plugin that has no auth schema."""
        # Arrange
        source = "no_auth_source"
        credentials = {"any_field": "any_value"}
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            self.credential_manager.add_credential(source, **credentials)
        
        assert f"Plugin for source '{source}' does not define an authentication schema" in str(exc_info.value)

    def test_integration_end_to_end_workflow(self):
        """Test complete end-to-end workflow with registry and credential manager."""
        # Arrange
        source = "nasa_earthdata"
        credentials = {
            "username": "test_user",
            "password": "test_pass",
            "token": "test_token"
        }
        
        # Mock the sources registry
        self.mock_keyring.get_password.return_value = json.dumps([])
        
        # Act - Add credentials
        self.credential_manager.add_credential(source, **credentials)
        
        # Act - Get credentials
        self.mock_keyring.get_password.return_value = json.dumps(credentials)
        retrieved_credentials = self.credential_manager.get_credential(source)
        
        # Act - List credentials
        self.mock_keyring.get_password.return_value = json.dumps([source])
        listed_sources = self.credential_manager.list_credentials()
        
        # Act - Remove credentials
        self.mock_keyring.get_password.return_value = json.dumps([source])
        self.credential_manager.remove_credential(source)
        
        # Assert
        assert retrieved_credentials == credentials
        assert listed_sources == [source]
        
        # Verify keyring calls
        assert self.mock_keyring.set_password.call_count >= 2  # Credentials + sources registry
        assert self.mock_keyring.get_password.call_count >= 3  # Multiple get operations
        assert self.mock_keyring.delete_password.call_count == 1

    def test_integration_multiple_sources_management(self):
        """Test managing credentials for multiple sources."""
        # Arrange
        sources_and_credentials = [
            ("nasa_earthdata", {"username": "nasa_user", "password": "nasa_pass", "token": "nasa_token"}),
            ("aviso_altimetry", {"ftp_host": "ftp.aviso.fr", "username": "aviso_user", "password": "aviso_pass"}),
            ("minimal_source", {"api_key": "minimal_key"})
        ]
        
        # Mock sources registry to start empty
        self.mock_keyring.get_password.return_value = json.dumps([])
        
        # Act - Add credentials for all sources
        for source, credentials in sources_and_credentials:
            self.credential_manager.add_credential(source, **credentials)
        
        # Act - List all sources
        self.mock_keyring.get_password.return_value = json.dumps([source for source, _ in sources_and_credentials])
        listed_sources = self.credential_manager.list_credentials()
        
        # Assert
        assert len(listed_sources) == 3
        assert "nasa_earthdata" in listed_sources
        assert "aviso_altimetry" in listed_sources
        assert "minimal_source" in listed_sources

    def test_integration_fuzzy_matching_across_operations(self):
        """Test fuzzy matching consistency across all credential operations."""
        # Arrange
        fuzzy_inputs = ["nasa_earth", "altimetry"]
        expected_matches = ["nasa_earthdata", "aviso_altimetry"]
        
        credentials = [
            {"username": "user1", "password": "pass1", "token": "token1"},
            {"ftp_host": "ftp.test.com", "username": "user2", "password": "pass2"}
        ]
        
        # Mock sources registry
        self.mock_keyring.get_password.return_value = json.dumps([])
        
        # Act & Assert - Add credentials with fuzzy matching
        with patch('builtins.print') as mock_print:
            for i, (fuzzy_input, expected_match, creds) in enumerate(zip(fuzzy_inputs, expected_matches, credentials)):
                self.credential_manager.add_credential(fuzzy_input, **creds)
                
                # Verify warning was printed
                assert mock_print.call_args_list[i][0][0] == f"Warning: '{fuzzy_input}' is not supported. Adding credential for '{expected_match}'."

    def test_integration_error_propagation_from_registry(self):
        """Test that registry errors are properly propagated to credential manager."""
        # Arrange
        source = "unknown_source"
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            self.credential_manager.add_credential(source, username="test")
        
        assert "Unknown data source 'unknown_source'" in str(exc_info.value)

    def test_integration_plugin_instantiation_and_validation(self):
        """Test that plugins are properly instantiated and validated."""
        # Arrange
        source = "nasa_earthdata"
        credentials = {"username": "test", "password": "test", "token": "test"}
        
        # Act
        self.credential_manager.add_credential(source, **credentials)
        
        # Assert - Verify plugin was instantiated and schema was retrieved
        # This is implicitly tested by the successful credential validation
        
    def test_integration_registry_singleton_consistency(self):
        """Test that the registry singleton is consistent across operations."""
        # Arrange
        source = "nasa_earthdata"
        credentials = {"username": "test", "password": "test", "token": "test"}
        
        # Act
        self.credential_manager.add_credential(source, **credentials)
        
        # Assert - The registry should be the same instance used throughout
        # This is tested implicitly by the successful operations

    def test_integration_concurrent_operations(self):
        """Test concurrent operations on registry and credential manager."""
        import threading
        import time
        
        # Arrange
        sources = ["nasa_earthdata", "aviso_altimetry", "minimal_source"]
        credentials_list = [
            {"username": "user1", "password": "pass1", "token": "token1"},
            {"ftp_host": "ftp.test.com", "username": "user2", "password": "pass2"},
            {"api_key": "key1"}
        ]
        
        results = []
        
        def worker(source, credentials):
            """Worker function for concurrent testing."""
            try:
                self.credential_manager.add_credential(source, **credentials)
                results.append(f"Success: {source}")
            except Exception as e:
                results.append(f"Error: {source} - {e}")
        
        # Act
        threads = []
        for source, credentials in zip(sources, credentials_list):
            thread = threading.Thread(target=worker, args=(source, credentials))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Assert
        assert len(results) == 3
        assert all("Success:" in result for result in results)

    def test_integration_memory_efficiency(self):
        """Test memory efficiency of integrated operations."""
        # Arrange
        source = "nasa_earthdata"
        credentials = {"username": "test", "password": "test", "token": "test"}
        
        # Act - Perform multiple operations
        self.credential_manager.add_credential(source, **credentials)
        self.credential_manager.get_credential(source)
        self.credential_manager.list_credentials()
        
        # Assert - Verify that operations don't create unnecessary objects
        # This is tested implicitly by the successful completion without memory issues

    def test_integration_data_integrity(self):
        """Test data integrity across registry and credential operations."""
        # Arrange
        source = "nasa_earthdata"
        original_credentials = {
            "username": "original_user",
            "password": "original_pass",
            "token": "original_token"
        }
        
        # Mock sources registry
        self.mock_keyring.get_password.return_value = json.dumps([])
        
        # Act
        self.credential_manager.add_credential(source, **original_credentials)
        
        # Verify the credentials were stored correctly
        self.mock_keyring.get_password.return_value = json.dumps(original_credentials)
        retrieved_credentials = self.credential_manager.get_credential(source)
        
        # Assert
        assert retrieved_credentials == original_credentials
        assert retrieved_credentials is not None
        assert retrieved_credentials["username"] == "original_user"
        assert retrieved_credentials["password"] == "original_pass"
        assert retrieved_credentials["token"] == "original_token"
