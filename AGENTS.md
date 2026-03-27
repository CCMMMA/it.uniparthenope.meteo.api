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

## Working Agreement

When editing this project:

1. Preserve API response formats unless the task explicitly allows breaking changes.
2. Prefer optimizations that reduce I/O, repeated parsing, or unnecessary allocations in request paths.
3. Keep filesystem paths and cache behavior consistent with the deployment configuration.
4. Be careful with large NetCDF/GRIB datasets: avoid loading or duplicating more data than needed.
5. Run at least a syntax-level verification on touched Python files before finishing.
6. Run the API endpoint unit-test suite with `pytest` whenever you change API handlers, request/response behavior, authentication flow, or shared service wiring.

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

## Notes For Future Agents

- Check which branch is active before assessing repository contents. `main` and `master` differ substantially.
- Treat `master` as the branch containing the current application code unless the user asks otherwise.
- If you change cache semantics or path construction, verify the related config keys in `etc/ccmmmaapi.conf`.
- The standard API test approach in this repository is `pytest` with Flask's test client and mocked service dependencies; keep endpoint coverage up to date when new routes are added.
