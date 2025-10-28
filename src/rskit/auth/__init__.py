"""
Authentication and authorization modules for RS-Kit.

This module provides a unified interface for managing credentials
across multiple data sources.
"""

from .credential_manager import CredentialManager

# Public API
def add_credential(source: str, **credentials):
    return CredentialManager.add_credential(source, **credentials)

def get_credentials(source: str):
    return CredentialManager.get_credential(source)

def remove_credential(source: str):
    return CredentialManager.remove_credential(source)

def list_credentials():
    return CredentialManager.list_credentials()