# RS-Kit Data Source Plugins

Each plugin represents a **data portal/service** (e.g., NASA Earthdata, AVISO Altimetry).

## Structure

```
plugins/
├── nasa_earthdata/
│   ├── base.py             # Plugin entrypoint (registered in core/registry.py)
│   ├── cmr.py              # CMR API client
│   ├── harmony.py          # Optional server-side subsetting
│   └── subset.py           # Client-side subsetting helpers
└── aviso_altimetry/
    ├── base.py             # Plugin entrypoint
    └── data/               # Shipped catalogs (JSON) + shapefiles
```

**Components**:

- `base.py`: Authentication + query execution (`download()` / `fetch()`) and any source-specific helpers.
- `data/`: Non-Python assets shipped with the package (see `pyproject.toml` package-data).

## Credentials

Credential requirements are documented centrally in [docs/credentials.md](../../../docs/credentials.md) and generated from each plugin's `schema.json`.
