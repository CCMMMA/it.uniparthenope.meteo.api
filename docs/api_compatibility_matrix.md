# API Compatibility Matrix

This matrix tracks the highest-priority interoperability gaps between this codebase
and the production API at `https://api.meteo.uniparthenope.it`.

It is intentionally small and focused on the endpoints called out in
`codex_meteo_api_interchangeability_plan.md`. Expand it as more production
snapshots are captured.

| Endpoint | Method | Production reference | Expected status | Expected content type | Local implementation | Parity status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/api/v1` | `GET` | new governed contract | `200` | `application/json` | `apis/namespace_api_v1.py` | additive | Discovery endpoint; it does not change or replace a legacy response. |
| `/instruments/<identification>` | `GET` | production live response | `200` for existing ids, `404` with JSON string for missing ids | `application/json` | `apis/namespace_instruments.py` | in-progress | Missing-id response now uses JSON quoting like production. |
| `/v2/basemaps/<name>` | `GET` | production swagger | `200` or `404` | `application/json` | `apis/namespace_v2.py` | in-progress | Missing basemap now returns a structured `404` instead of raising `KeyError`. |
| `/v2/basemap/detail?name=<name>` | `GET` | legacy compatibility route | `200` or `404` | `application/json` | `apis/namespace_v2.py` | added compatibility alias | Preserved as an alias for older clients. |
| `/products/wrf5/forecast/d02/grib/text` | `GET` | comparison suite | `200` | `text/plain` | `apis/namespace_products.py` + `core/GribServices.py` | pending deeper validation | Needs live body comparison once the new stack is wired to production data sources. |
| `/products/wrf5/timeseries/com63049/csv` | `GET` | comparison suite | `200` | `text/csv` | `apis/namespace_products.py` + `core/MeteoServices.py` | pending deeper validation | Requires byte-for-byte CSV parity against a captured production fixture. |

## Verified production observations

The following live responses were manually sampled on 2026-04-18:

- `GET /instruments/station-01` returned the JSON string
  `"Identification not found!"`.

## Next compatibility targets

- Capture production fixtures for the failing `places`, `products`, and CSV routes.
- Add regression tests that compare the local serializers against those fixtures.
- Validate image endpoints with stable binary snapshots once the rendering
  environment matches production fonts and plotting dependencies.
