# NASA Earthdata Plugin (Source Name: nasa_earthdata)

This plugin provides discovery, download, and fetch helpers for NASA Earthdata collections.

Required query params (via `Query.with_params(...)`):
- `collection_concept_id` (resolve it first with `NasaEarthdata.resolve_collection_concept_id`).

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
- `variables`.

Harmony subsetting is used automatically when the collection supports it, with
fallback to client-side processing if Harmony fails.
