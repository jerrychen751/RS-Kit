"""
Central credential management system. Stateless utility class interacting with informations tored in OS keyring.
"""

import json
import keyring
from typing import Dict, Optional, Any, List

from ..core.registry import registry

class CredentialManager:
    """Manages credentials across all data sources."""
    
    SERVICE_NAME: str = "rskit"
    _SOURCES_REGISTRY_KEY: str = "__sources__" # keyring storing names of sources with credentials stored

    # Public API methods
    @staticmethod
    def add_credential(source: str, **credentials) -> None:
        """
        Add credentials for a data source.
        
        Args:
            source (str): Data source identifier.
            **credentials: Credential key-value pairs.
        """
        # Validate the data source and credentials against registered data plugins
        matched_source = registry._match_source_name(source)
        if matched_source != source:
            print(f"Warning: '{source}' is not supported. Adding credential for '{matched_source}'.")
        
        CredentialManager._validate_credentials(matched_source, credentials)

        # Store and update registry
        keyring.set_password(
            CredentialManager.SERVICE_NAME,
            matched_source,
            json.dumps(credentials),
        )

        sources = CredentialManager.list_added_credentials()
        if matched_source not in sources:
            sources.append(matched_source)
            CredentialManager._update_stored_sources(sorted(sources))
    
    @staticmethod
    def get_credential(source: str) -> Optional[Dict[str, Any]]:
        """
        Get credentials for a data source.
        
        Args:
            source (str): Data source identifier.
            
        Returns:
            Optional[Dict[str, Any]]: Credentials dict or None if not found.
        """
        matched_source = registry._match_source_name(source)
        if matched_source != source:
            print(f"Warning: '{source}' is not supported. Getting credentials for '{matched_source}'.")
        
        stored = keyring.get_password(CredentialManager.SERVICE_NAME, matched_source)
        return json.loads(stored) if stored else None
    
    @staticmethod
    def remove_credential(source: str) -> None:
        """
        Remove credentials for a data source.
        
        Args:
            source (str): Data source identifier.
        """
        matched_source = registry._match_source_name(source)
        if matched_source != source:
            print(f"Warning: '{source}' is not supported. Did you want to remove the credential for '{matched_source}'?")
            print("No credential was deleted. Please specify the exact source name to delete.")
        else:
            keyring.delete_password(CredentialManager.SERVICE_NAME, source)
            sources = CredentialManager.list_added_credentials()
            sources.remove(source)
            CredentialManager._update_stored_sources(sorted(sources))

    @staticmethod
    def list_added_credentials() -> List[str]:
        """
        List all stored data source identifiers.
        
        Returns:
            List[str]: List of data source identifiers.
        """
        sources_json = keyring.get_password(CredentialManager.SERVICE_NAME, CredentialManager._SOURCES_REGISTRY_KEY)
        if sources_json:
            try:
                return json.loads(sources_json) # list converted to a set
            except json.JSONDecodeError:
                return []
        return []
    
    # Private helper methods
    @staticmethod
    def _validate_credentials(source: str, credentials: Dict[str, Any]) -> None:
        """
        Validate provided credentials against the plugin's required credential schema.

        Args:
            source (str): Data source identifier (must match a registered data plugin).
            credentials (Dict[str, Any]): Credential key-value pairs to validate.

        Raises:
            ValueError: If required credential fields are missing, the number of provided fields does not match the required fields, or the plugin does not define a credential schema.
        """
        plugin_class = registry._get_plugin_class(source)
        plugin_instance = plugin_class()

        if hasattr(plugin_instance, 'get_credential_schema'):
            try:
                schema = plugin_instance.get_credential_schema()
                required_fields: List[str] = schema['required_fields']

                for field in required_fields:
                    if field not in credentials:
                        raise ValueError(
                            f"Missing required credential field '{field}' for source '{source}'.\n"
                            f"Required fields are: {required_fields}."
                        )

                if len(credentials) != len(required_fields):
                    raise ValueError(
                        f"Number of provided credential fields ({len(credentials)}) does not match the number of required fields "
                        f"({len(required_fields)}) for source '{source}'.\n"
                        f"Required fields: {required_fields}.\n"
                        f"Provided fields: {list(credentials.keys())}."
                    )
            except AttributeError:
                raise ValueError(
                    f"Plugin for source '{source}' does not define a credential schema."
                )
        else:
            raise ValueError(
                f"Plugin for source '{source}' does not define a credential schema."
            )

    @staticmethod
    def _update_stored_sources(sources: List[str]) -> None:
        """
        Update the set of stored data source identifiers in the OS keyring.
        
        Args:
            sources (Set[str]): Set of data source identifiers to store.
        """
        keyring.set_password(CredentialManager.SERVICE_NAME, CredentialManager._SOURCES_REGISTRY_KEY, json.dumps(list(sources)))
    
