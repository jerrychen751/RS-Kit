# NASA Earthdata Plugin (Source Name: nasa_earthdata)

This plugin provides discovery and download helpers for NASA Earthdata collections.

Required query params (via `Query.with_params(...)`):
- `collection_concept_id` (resolve it first with `NasaEarthdata.resolve_collection_concept_id`).

Other required query settings:
- `Query.time(...)` and `Query.region(...)`.

Optional params:
- `cloud_cover`, `sort_key`, `max_granules`, `variables` (client-side only), `drop_nan_lines`.

Programmatic schema lookup:

```python
import rskit as rs

schema = rs.plugins.get_params_schema("nasa_earthdata")
```

Convenience import:

```python
from rskit.plugins import NasaEarthdata
```

Harmony subsetting is used automatically when the collection supports it (spatial/temporal only),
with fallback to client-side processing if Harmony fails.
