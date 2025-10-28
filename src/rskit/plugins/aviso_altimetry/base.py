

from typing import Dict, Any, Optional

from ...contracts.plugin import DataSourcePlugin
from ...core.query_builder import Query

class AvisoAltimetry(DataSourcePlugin):
    
    AUTH_SCHEMA = {
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