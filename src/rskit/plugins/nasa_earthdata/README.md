# NASA Earthdata Plugin (Source Name: nasa_earthdata)

This plugin provides discovery, download, and fetch helpers for NASA Earthdata collections.

Required query params (via `Query.with_params(...)`):
- Provide one of: `collection_concept_id`, `collection_doi`, or both `collection_short_name` and `collection_version`.

Other required query settings:
- `Query.time(...)` and `Query.region(...)`.

Optional params:
- `cloud_cover`, `sort_key`, `max_granules`, `download_dir`, `drop_nan_lines`.

Programmatic schema lookup:

```python
import rskit as rs

schema = rs.plugins.get_params_schema("nasa_earthdata")
```

Convenience import:

```python
from rskit.plugins import NasaEarthdata
```

Fetch-specific kwargs (passed directly to `Query.fetch(...)`):
- `use_harmony`, `variables`.
