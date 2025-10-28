from typing import Dict, Any, Optional

from ...contracts.plugin import DataSourcePlugin
from ...core.query_builder import Query

class NasaEarthdata(DataSourcePlugin):
    
    AUTH_SCHEMA = {
        "required_fields": ["username", "password", "token"],
        "field_descriptions": {
            "username": "NASA Earthdata username",
            "password": "NASA Earthdata password", 
            "token": "Bearer token to access application services integrated with the Earthdata Login system",
        }
    }

    def discover(
        self,
        instrument: Optional[str] = None,
        variable: Optional[str] = None
    ) -> str:
        pass

    def supports_variable(self, variable: str) -> bool:
        pass

    def estimate_size(self, query: Query) -> Optional[int]:
        pass