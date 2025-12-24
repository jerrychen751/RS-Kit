# AVISO Altimetry Plugin (Source Name: aviso_altimetry)

This plugin provides discovery, download, and fetch helpers for AVISO SWOT altimetry data.

Required query params (via `Query.with_params(...)`):
- `file_identifier`, `version`, `variant`.

Other required query settings:
- `Query.time(...)`.

Optional params:
- `download_dir`.

Programmatic schema lookup:

```python
import rskit as rs

schema = rs.plugins.get_params_schema("aviso_altimetry")
```

Convenience import:

```python
from rskit.plugins import AvisoAltimetry
```
