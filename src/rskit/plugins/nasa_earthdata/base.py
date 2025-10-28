from typing import Dict, Any, Optional

from ...interfaces.plugin import DataSourcePlugin
from ...models.query import Query

class NasaEarthdata(DataSourcePlugin):

    def get_auth_schema(self) -> Dict[str, Any]:
        return {
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