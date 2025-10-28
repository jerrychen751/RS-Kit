

from typing import Dict, Any, Optional

from ...interfaces.plugin import DataSourcePlugin
from ...models.query import Query

class AvisoAltimetry(DataSourcePlugin):

    def get_auth_schema(self) -> Dict[str, Any]:
        return {
            "required_fields": ["ftp_host", "username", "password"],
            "field_descriptions": {
                "ftp_host": "AVISO FTP server hostname",
                "username": "AVISO FTP username",
                "password": "AVISO FTP password"
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