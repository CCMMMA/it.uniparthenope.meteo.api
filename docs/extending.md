# Extending the API

## Choose the extension point

- Add HTTP routes to an existing module in `apis/` when they belong to that namespace.
- Add a namespace in `apis/` for a distinct public resource family, then register it in `apis/__init__.py`.
- Put meteorological computation, archive access, caching, plotting, or external orchestration in `core/`; keep route handlers focused on validation and HTTP responses.
- Extend `etc/maps.json`, the variable-control files, or other metadata when behavior is data-driven rather than endpoint-specific.

Preserve existing response envelopes, status codes, media types, and cache keys unless a versioned breaking change is explicitly intended.

## Application and service access

`app.create_app()` is the composition root: it loads deployment configuration, initializes Flask extensions, creates reusable runtime services, and publishes them under `current_app.extensions["meteo_api"]`.

New handlers should obtain shared dependencies from that extension instead of importing the `app` module. For example:

```python
from flask import current_app

services = current_app.extensions["meteo_api"]
forecast = services.meteo.modelOutput(params)
```

The module-level names such as `app.meteo_services` and `app.diskcache` remain temporarily available for legacy handlers. They form a compatibility bridge, not the preferred extension point. Migrate them resource-by-resource so each change can retain explicit endpoint contract tests.

## Adding an endpoint

1. Locate the closest namespace and copy its Flask-RESTX resource conventions.
2. Define path/query parameters and Swagger documentation.
3. Validate and normalize inputs at the boundary.
4. Delegate work to a shared service rather than constructing expensive helpers per request.
5. Return explicit JSON errors and suitable HTTP status codes; do not leak stack traces or filesystem paths.
6. Add Flask test-client coverage in `tests/test_api_endpoints.py` and reusable cases in `tests/api_cases.py` where appropriate.
7. Update [API_ENDPOINTS.md](API_ENDPOINTS.md) and client tutorials if the new route is user-facing.

If authentication, shared service wiring, or request/response behavior changes, run the complete endpoint unit suite.

## Adding a product or model variable

Inspect how `MeteoServices`, `GribServices`, `Plotter`, `Places`, and the relevant variable-control file derive domains, archive paths, timestamps, and output metadata. Confirm:

- the NetCDF variable name, dimensions, units, fill values, and coordinate order
- the model/domain archive naming convention
- interpolation behavior at domain edges and missing cells
- JSON, CSV, plot, legend, and time-series representations
- fallback behavior when a forecast cycle or image is absent

Open datasets for the shortest possible scope. Slice only required variables and time steps, avoid copying full arrays, and close dataset handles deterministically.

## Cache-safe changes

Forecast and time-series handlers use memcached, disk cache, shared hourly slices, and persisted popularity signatures. When changing a key or normalized parameter:

1. update writers and readers together
2. update invalidate and rebuild endpoints
3. update `RequestPopularityTracker` normalization
4. test JSON/CSV variants that share canonical entries
5. document migration or expiry behavior in [CACHE.md](CACHE.md) and [OPERATIONS_AND_USAGE.md](OPERATIONS_AND_USAGE.md)

Prefer direct cache-file lookup over directory scans. Use atomic persistence for shared metadata and avoid loading large export files into memory when a streaming response is possible.

## Adding an external service

Keep hostnames, credentials, timeouts, and feature flags in deployment configuration. Create one reusable client/service during application startup when it is safe to share. Bound network calls with timeouts, translate upstream failures into stable API errors, and make optional integrations degrade independently.

Mock the service boundary in unit tests. Do not require live credentials or network access in the default `pytest` run.

## Testing and verification

At minimum for touched Python files:

```bash
python -m py_compile path/to/changed.py
```

For handlers, authentication, response behavior, or service wiring:

```bash
pytest -q
```

Add focused tests for valid requests, missing/invalid parameters, missing upstream data, cache hits and misses, and stable response shape. Use optional live tests only against an explicitly selected environment; POST calls remain opt-in. See [TESTING.md](TESTING.md).

## Review checklist

- response compatibility is preserved or deliberately versioned
- no credentials or deployment-only absolute paths were added
- large files and arrays are not unnecessarily buffered or duplicated
- files, datasets, connections, and process/thread pools are cleaned up
- cache invalidation and operations docs match cache behavior
- Swagger and endpoint docs match the implementation
- syntax checks and relevant tests pass
