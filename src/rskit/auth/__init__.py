"""
Authentication and authorization modules for RS-Kit.

This module provides a unified interface for managing credentials
across multiple data sources.
"""

from .credential_manager import CredentialManager
from ..core.registry import registry

from typing import Dict, Any

# Public API
def add_credential(source: str, **credentials):
    """Add credentials for a data source.
    
    Args:
        source (str): Data source identifier (e.g., "nasa_earthdata", "aviso_altimetry").
            Use list_supported_sources() to see all available sources.
        **credentials: Credential key-value pairs required by the data source.
            Use get_credential_schema(source) to see the required fields and their format.
    
    Examples:
        >>> # First, discover available sources and their credential requirements
        >>> rs.auth.list_supported_sources()
        ['nasa_earthdata', 'aviso_altimetry']
        >>> rs.auth.get_credential_schema("nasa_earthdata")
        {'required_fields': ['username', 'password', 'token']}
        
        >>> # Then add credentials with the correct fields
        >>> rs.auth.add_credential("nasa_earthdata", 
        ...                        username="your_username",
        ...                        password="your_password", 
        ...                        token="your_token")
    
    Note:
        The source name supports fuzzy matching (e.g., "nasaearthdata" matches "nasa_earthdata").
        A warning will be displayed if fuzzy matching is used.
    """
    return CredentialManager.add_credential(source, **credentials)

def get_credentials(source: str):
    return CredentialManager.get_credential(source)

def remove_credential(source: str):
    return CredentialManager.remove_credential(source)

def list_added_credentials():
    return CredentialManager.list_added_credentials()

def list_supported_sources():
    return registry.get_supported_sources()

def get_credential_schema(source: str):
    return registry.get_credential_schema(source)

__all__ = [
    "add_credential",
    "get_credentials",
    "remove_credential",
    "list_added_credentials",
    "list_supported_sources",
    "get_credential_schema"
]
