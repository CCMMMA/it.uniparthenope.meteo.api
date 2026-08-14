# AGENTS.md

## Project Overview

This repository hosts a Flask-based meteorological API.

Primary entrypoints and code areas:

- `app.py`: Flask application setup, cache clients, service wiring.
- `wsgi.py`: WSGI entrypoint.
- `apis/`: Flask-RESTX namespaces and route handlers.
- `core/`: business logic for products, places, plotting, GRIB/NetCDF access, cache helpers, and external services.
- `etc/`: JSON and config files used at runtime.
- `data/` and `static/`: bundled assets and reference data.

The active application branch is `main`. The `master` branch is retained for
historical comparison and must not be treated as the default implementation.

## Working Agreement

When editing this project:

1. Preserve API response formats unless the task explicitly allows breaking changes.
2. Prefer optimizations that reduce I/O, repeated parsing, or unnecessary allocations in request paths.
3. Keep filesystem paths and cache behavior consistent with the deployment configuration.
4. Be careful with large NetCDF/GRIB datasets: avoid loading or duplicating more data than needed.
5. Run at least a syntax-level verification on touched Python files before finishing.
6. Run the API endpoint unit-test suite with `pytest` whenever you change API handlers, request/response behavior, authentication flow, or shared service wiring.
7. If you touch popularity tracking, invalidation, or rebuild behavior, update the related cache and operations documentation together with the code.
8. When adding or retiring routes, update `docs/API_ENDPOINTS.md`, the client tutorials, the compatibility matrix, and both local and live endpoint tests in the same change.
9. Do not restore retired compatibility routes without an explicit requirement and coverage for their authentication, response, and operational dependencies.

## Optimization Priorities

The most likely performance-sensitive areas are:

1. `core/GribServices.py` for NetCDF reads, interpolation, and export generation.
2. `core/MeteoServices.py` for request-time data transformation and remote fetch orchestration.
3. `core/ManageDiskCache.py` for disk cache lookups and cache-file churn.
4. MongoDB-backed place lookups in `core/Places.py`.

Focus on measurable wins such as:

1. Reusing parsed timestamps and derived filesystem paths.
2. Avoiding full in-memory buffering when streaming large export files.
3. Replacing repeated filesystem scans with direct lookups where possible.
4. Reducing duplicate object creation inside hot request handlers.
5. Preserving the low-overhead request-popularity tracker on forecast and time-series hot paths.
6. Promoting on-disk OWM tile hits into memcached to avoid repeated disk reads and JSON decoding.
7. Reusing bounded worker pools for tile generation instead of creating an executor for every cache miss.

## API Surface Notes

The supported route catalog is maintained in `docs/API_ENDPOINTS.md`. The
following legacy families are intentionally not registered on `main`:

- `POST /users/login`
- `GET /apps/sais/index`
- `/v2/auth/login`
- `/v2/navbar`
- `/v2/pages` and `/v2/page/detail`
- `/v2/weatherreports/*`

Their former helpers may also have been removed. Treat a `404` for these paths
as the expected behavior, and keep regression tests that assert they remain
unregistered unless the API contract is deliberately changed.

## Notes For Future Agents

- Check which branch is active before assessing repository contents. `main` and `master` differ substantially.
- Treat `main` as the current application branch. Use `master` only when a task explicitly targets or compares the historical branch.
- If you change cache semantics or path construction, verify the related config keys in `etc/ccmmmaapi.conf`.
- OWM tile requests use memcached as the first-level cache and disk cache as the second level. Preserve promotion of disk hits back into memcached and honor `use_disk_cached` when writing.
- `core/Tiles.py` owns a long-lived, bounded `ThreadPoolExecutor`; do not recreate it inside request handlers or per-tile cache misses.
- If you change forecast or time-series cache keys, update the invalidate/rebuild endpoints and the popularity-tracker normalization logic together.
- The cache-maintenance endpoints depend on persisted popularity counters under `REQUEST_POPULARITY_PATH`; keep the tracker writable in tests and deployments.
- The standard API test approach in this repository is `pytest` with Flask's test client and mocked service dependencies; keep endpoint coverage up to date when new routes are added.
