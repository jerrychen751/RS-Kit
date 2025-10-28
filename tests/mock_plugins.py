"""Mock plugins for testing purposes."""

from typing import Dict, Any, Optional
from rskit.contracts.plugin import DataSourcePlugin
from rskit.core.query import Query


class MockNasaEarthdataPlugin(DataSourcePlugin):
    """Mock NASA Earthdata plugin for testing."""
    
    def get_auth_schema(self) -> Dict[str, Any]:
        return {
            "required_fields": ["username", "password", "token"],
            "field_descriptions": {
                "username": "NASA Earthdata username",
                "password": "NASA Earthdata password", 
                "token": "Bearer token for Earthdata Login system",
            }
        }
    
    def discover(self, instrument: Optional[str] = None, variable: Optional[str] = None) -> str:
        products = []
        if instrument is None or instrument == "SWOT":
            products.append("SWOT Sea Surface Height")
        if instrument is None or instrument == "PACE":
            products.append("PACE Ocean Color")
        if variable:
            products = [p for p in products if variable.lower() in p.lower()]
        return f"Available products: {', '.join(products)}"
    
    def supports_variable(self, variable: str) -> bool:
        supported_vars = ["sea_surface_height", "ocean_color", "chlorophyll", "sst"]
        return variable.lower() in supported_vars
    
    def estimate_size(self, query: Query) -> Optional[int]:
        # Mock size estimation based on spatial extent
        spatial = query.spatial
        area = (spatial.lon_max - spatial.lon_min) * (spatial.lat_max - spatial.lat_min)
        return int(area * 1000)  # 1000 bytes per degree squared


class MockAvisoAltimetryPlugin(DataSourcePlugin):
    """Mock AVISO Altimetry plugin for testing."""
    
    def get_auth_schema(self) -> Dict[str, Any]:
        return {
            "required_fields": ["ftp_host", "username", "password"],
            "field_descriptions": {
                "ftp_host": "AVISO FTP server hostname",
                "username": "AVISO FTP username",
                "password": "AVISO FTP password"
            }
        }
    
    def discover(self, instrument: Optional[str] = None, variable: Optional[str] = None) -> str:
        products = []
        if instrument is None or instrument == "Jason":
            products.append("Jason-3 Sea Level Anomaly")
        if instrument is None or instrument == "Sentinel":
            products.append("Sentinel-3 Altimetry")
        if variable:
            products = [p for p in products if variable.lower() in p.lower()]
        return f"Available products: {', '.join(products)}"
    
    def supports_variable(self, variable: str) -> bool:
        supported_vars = ["sea_level_anomaly", "altimetry", "ssh", "sla"]
        return variable.lower() in supported_vars
    
    def estimate_size(self, query: Query) -> Optional[int]:
        # Mock size estimation based on temporal extent
        temporal = query.temporal
        days = (temporal.end - temporal.start).days
        return days * 500  # 500 bytes per day


class MockMinimalPlugin(DataSourcePlugin):
    """Mock plugin with minimal required fields for testing."""
    
    def get_auth_schema(self) -> Dict[str, Any]:
        return {
            "required_fields": ["api_key"],
            "field_descriptions": {
                "api_key": "API key for data access"
            }
        }
    
    def discover(self, instrument: Optional[str] = None, variable: Optional[str] = None) -> str:
        return "Mock minimal data products"
    
    def supports_variable(self, variable: str) -> bool:
        return variable.lower() in ["temperature", "pressure"]
    
    def estimate_size(self, query: Query) -> Optional[int]:
        return 1024  # 1KB


class MockComplexPlugin(DataSourcePlugin):
    """Mock plugin with complex authentication schema for testing."""
    
    def get_auth_schema(self) -> Dict[str, Any]:
        return {
            "required_fields": ["username", "password", "token", "endpoint", "timeout"],
            "field_descriptions": {
                "username": "Service username",
                "password": "Service password",
                "token": "Authentication token",
                "endpoint": "API endpoint URL",
                "timeout": "Request timeout in seconds"
            }
        }
    
    def discover(self, instrument: Optional[str] = None, variable: Optional[str] = None) -> str:
        return f"Complex mock products for {instrument or 'all instruments'}"
    
    def supports_variable(self, variable: str) -> bool:
        return variable.lower() in ["complex_var1", "complex_var2", "complex_var3"]
    
    def estimate_size(self, query: Query) -> Optional[int]:
        return 2048  # 2KB


class MockPluginWithoutAuthSchema(DataSourcePlugin):
    """Mock plugin without auth schema for testing error cases."""
    
    def get_auth_schema(self) -> Dict[str, Any]:
        raise AttributeError("No auth schema")
    
    def discover(self, instrument: Optional[str] = None, variable: Optional[str] = None) -> str:
        return "Mock products without auth schema"
    
    def supports_variable(self, variable: str) -> bool:
        return True
    
    def estimate_size(self, query: Query) -> Optional[int]:
        return None
