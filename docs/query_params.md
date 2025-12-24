# Data Plugin Query Parameters

This page is generated from plugin `schema.json` definitions.
Run `python scripts/docs/generate_query_params_docs.py` to update.

## nasa_earthdata

Plugin class: `NasaEarthdata`

Required (one of):
- `collection_concept_id`, or `collection_doi`, or `collection_short_name`, `collection_version`

Optional fields:
- `cloud_cover`: Tuple of (min_percent, max_percent) for cloud cover filtering.
- `sort_key`: CMR sort key (e.g., '-start_date').
- `max_granules`: Maximum number of granules to return/download.
- `download_dir`: Override download destination directory.
- `drop_nan_lines`: Drop all-NaN lines during client-side subsetting.

Notes:
- Query.time(...) and Query.region(...) are required for NASA Earthdata downloads.

## aviso_altimetry

Plugin class: `AvisoAltimetry`

Required fields:
- `file_identifier`: AVISO product identifier (e.g., 'SWOT_L3_LR_SSH').
- `version`: Product version from the catalog (e.g., 'v1_0').
- `variant`: Product variant from the catalog (e.g., 'Expert').

Optional fields:
- `download_dir`: Override download destination directory.

Notes:
- Query.time(...) is required for AVISO downloads.
