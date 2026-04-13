# Operations, Development, Deployment, and Usage Guide

## Purpose

This document describes how to deploy, develop, update, operate, and use `it.uniparthenope.meteo.api` in a production-oriented environment.

The application is a Flask-RESTX API that exposes meteorological products and supporting content. It is not a standalone demo application: several endpoints assume the presence of mounted meteorological archives, generated image directories, configuration files, cache services, and backing databases.

Related documents:

- Endpoint reference: [API_ENDPOINTS.md](API_ENDPOINTS.md)
- Production setup checklist: [PRODUCTION_SETUP.md](PRODUCTION_SETUP.md)
- Cache guide: [CACHE.md](CACHE.md)
- Testing guide: [TESTING.md](TESTING.md)
- Python usage tutorial: [PYTHON_API_TUTORIAL.md](PYTHON_API_TUTORIAL.md)
- Android usage tutorial: [ANDROID_KOTLIN_API_TUTORIAL.md](ANDROID_KOTLIN_API_TUTORIAL.md)
- iOS usage tutorial: [IOS_SWIFT_API_TUTORIAL.md](IOS_SWIFT_API_TUTORIAL.md)

## Technology Stack

- Python 3.8
- Flask
- Flask-RESTX
- uWSGI
- NumPy, SciPy, netCDF4, wrf-python, matplotlib, MetPy
- pymongo and Flask-SQLAlchemy
- pymemcache
- Docker for containerized deployment

## Repository Layout

- `app.py`: application bootstrap and shared service initialization.
- `wsgi.py`: WSGI entrypoint used by uWSGI.
- `apis/`: HTTP namespaces and Swagger-visible endpoints.
- `core/`: meteorological business logic and service integrations.
- `etc/`: configuration and static JSON metadata.
- `static/`: static images served by some endpoints.
- `data/`: shapefiles and static data assets.
- `vars-control-file/`: variable-control metadata used by product workflows.
- `diskcache-cleaner` and `link-storage.sh`: operational helper scripts.

## Runtime Dependencies

The service may require some or all of the following, depending on which endpoints are used:

- memcached for hot response caching
- MongoDB for places and related metadata
- PostgreSQL for SQLAlchemy-backed models
- shared filesystem mounts for archives, history, generated products, and disk cache
- Signal K endpoint for instruments data
- Slurm access for queue and storage endpoints
- CMS JSON configuration files

## Configuration

The application expects `APP_SETTINGS` to point to a Python-readable configuration file, typically `etc/ccmmmaapi.conf`.

Important configuration keys include:

- `BASE_PATH`: archive root for forecast NetCDF products
- `BASE_STORAGE_PATH`: history storage root
- `BASE_PRODUCTS`: generated product output directory
- `BASE_DISKCACHE`: on-disk cache root
- `TTL_MEMCACHED`: memcached time-to-live in seconds
- `TTL_DISKCACHE`: disk cache time-to-live in seconds
- `NUM_THREADS`: thread fan-out for local parallel work
- `NUM_PROCESSES`: process fan-out for cold multi-time-step computations
- `TIMESERIES_PARALLEL_MODE`: execution mode for multi-time-step endpoints
- `POPULAR_REQUESTS_LIMIT`: number of hottest forecast and time-series signatures to consider during rebuild
- `REQUEST_POPULARITY_PATH`: persisted popularity-counter file
- `REQUEST_POPULARITY_FLUSH_EVERY`, `REQUEST_POPULARITY_FLUSH_INTERVAL`: batching controls for tracker persistence
- `MAPS`, `LEGAL`, `PAGES`: JSON metadata files
- `NOIMAGE_PATH`, `NOIMAGE_URL`: fallback image resources
- `ENV`: deployment environment label

Before deployment, validate that every configured absolute path exists inside the container or is mounted from the host.

## Local Development

### 1. Create an isolated environment

Example flow:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

### 2. Provide configuration

Set:

```bash
export APP_SETTINGS=/absolute/path/to/etc/ccmmmaapi.conf
```

For local development, prepare a configuration file with accessible development paths rather than the production filesystem locations used in the committed example.

### 3. Start the application

For lightweight development:

```bash
flask --app app:application run --host 0.0.0.0 --port 5000
```

For a stack closer to production:

```bash
uwsgi --ini ccmmmaapi.ini
```

### 4. Validate the application

Recommended checks:

- open the Swagger UI and verify namespace registration
- call `/version`
- call a simple metadata endpoint such as `/legal/disclaimer`
- call one cache-backed endpoint and inspect memcached/disk cache behavior
- run the endpoint unit-test suite described in [TESTING.md](TESTING.md)
- compile touched modules with `python3 -m py_compile`

## Container Deployment

The repository already includes a [Dockerfile](../Dockerfile).

Deployment behavior:

- installs Python dependencies from `requirements.txt`
- copies the project into `/project`
- sets `APP_SETTINGS=/project/etc/ccmmmaapi.conf`
- starts `uWSGI` with `ccmmmaapi.ini`

### Recommended deployment steps

1. Build the image.
2. Mount production data volumes for archives, generated images, cache, and configuration if needed.
3. Inject environment-specific configuration.
4. Ensure the memcached, MongoDB, and PostgreSQL endpoints are reachable from the container.
5. Run readiness checks on lightweight endpoints before routing external traffic.

### Example build command

```bash
docker build -t it-uniparthenope-meteo-api .
```

### Example runtime considerations

- mount archive/history directories read-only where appropriate
- mount generated output and disk cache directories read-write
- expose the uWSGI-serving port through a reverse proxy
- configure logging aggregation outside the container

## Update Procedure

Use a repeatable update workflow:

1. Pull the desired branch and inspect the diff.
2. Review configuration changes, especially filesystem and cache settings.
3. Rebuild the container image if dependencies or code changed.
4. Run syntax checks and smoke tests.
5. Run the endpoint unit-test suite documented in [TESTING.md](TESTING.md).
6. Deploy to staging first when practical.
7. Warm or clear caches if response-shape changes could invalidate cached content. Use [CACHE.md](CACHE.md) to choose between TTL-only cleanup, selective invalidation, and full cache reset.
8. Promote to production only after validating product, place, and `v2` endpoints.

## Best Practices

### Development

- Prefer logging over `print`.
- Keep API response shapes stable unless a versioned change is intentional.
- Avoid speculative optimization; focus on I/O, dataset loading, and repeated parsing.
- Be careful with `eval`-style cache reads and legacy patterns when refactoring.
- Add or improve Swagger descriptions whenever a route changes.

### Performance

- Reuse derived paths and parsed timestamps in request handlers.
- Avoid buffering large generated files fully in memory unless necessary.
- Let memcached and disk cache absorb repeated reads for expensive endpoints.
- Be cautious with large NetCDF datasets and interpolation-heavy paths.
- Treat multi-time-step endpoints such as `timeseries` as priority cache consumers because they fan out across many hourly reads.
- Prefer cache sharing between alternate representations of the same payload, such as JSON and CSV time-series exports.
- Use multiprocessing for cold multi-time-step slices and keep cache-hit loading local so CPU time is spent only where it buys latency reduction.
- Use targeted invalidation and rebuilds for product/place windows before reaching for a full cache purge.

### Reliability

- Fail with explicit error JSON where possible.
- Keep fallback assets such as `NOIMAGE_PATH` available.
- Treat external services such as Signal K, Slurm, and MongoDB as partial-failure domains.
- Use conservative timeouts and retries around remote requests.

### Security

- Do not commit production credentials.
- Validate tokens and auth-protected `v2` behavior through the existing decorators.
- Review the login and token-handling endpoints before exposing the API publicly.
- Put the service behind a reverse proxy with TLS termination and request limits.

## Usage Guidance

### Swagger / OpenAPI

Flask-RESTX exposes a Swagger interface for interactive endpoint discovery and testing at the application root path `/`. This should be the primary manual exploration entrypoint for developers and integrators.

Use Swagger to:

- inspect namespace groupings
- review path and query parameters
- test authenticated and non-authenticated endpoints
- verify the expected content type for JSON, CSV, and PNG responses

### Core endpoint families

- `version`: service version and environment
- `legal`: disclaimer and privacy resources
- `places`: geospatial and identifier-based place discovery
- `products`: forecasts, plots, GRIB data, legends, time series, and related assets
- `apps`: application-facing integration endpoints
- `v2`: weather reports, CMS/navigation, map metadata, Slurm endpoints, and auth-related flows
- `webcam`: latest webcam frame retrieval
- `instruments`: instruments inventory and lookup

## Troubleshooting

### The service starts but product endpoints fail

Likely causes:

- missing NetCDF archive/history files
- invalid `BASE_PATH` or `BASE_STORAGE_PATH`
- generated output directories not writable

### Cache-backed endpoints behave inconsistently

Check:

- memcached reachability
- `BASE_DISKCACHE` write permissions
- TTL values in configuration
- stale on-disk objects created by older response shapes

For multi-time-step endpoints specifically, also check:

- whether the per-hour JSON cache under `CACHE_JSON` is writable
- whether JSON and CSV variants are warming the same canonical time-series cache entries
- whether the archive file mtime is invalidating the expected disk-cache entries
- whether `REQUEST_POPULARITY_PATH` is writable so rebuilds can see the latest hot signatures

### Rebuild and invalidation operations

Useful maintenance commands:

- invalidate one product/place window:

```text
GET /products/<prod>/invalidate/<place>/?date=YYYYMMDDZhhmm&hours=n
```

- rebuild the hottest caches for one product:

```text
GET /products/<prod>/rebuild/?date=YYYYMMDDZhhmm&hours=n
```

Recommended sequence after a targeted data refresh:

1. call the invalidate endpoint for the affected product/place window
2. call the rebuild endpoint for the product
3. compare live timings against production or pre-production using the pytest live suite

### Swagger loads but endpoints error

Check:

- whether the namespace dependencies are reachable
- whether required files in `etc/` exist
- whether auth-protected `v2` endpoints are being called without headers

### Image endpoints return fallbacks or missing content

Check:

- generated product directories
- `NOIMAGE_PATH`
- plotting dependencies and font/static asset availability

## Documentation Maintenance

When the code changes:

1. Update `README.md` if architecture or usage changed.
2. Update this file when deployment or operational behavior changed.
3. Update `docs/PRODUCTION_SETUP.md` when production setup assumptions change.

## Comparing Two Working APIs

The repository test suite can compare two deployed APIs in terms of both behavior and wallclock timing.

Typical use case:

- primary URL: production
- comparison URL: pre-production or staging

Command:

```bash
python3 -m pytest -q \
  --live-base-url https://api.meteo.uniparthenope.it \
  --compare-base-url https://preprod.example.test
```

What this gives you:

- contract-style comparison for the covered endpoint catalog
- visibility into status-code mismatches
- visibility into payload mismatches
- per-invocation wallclock timings for both environments

How to use the results:

1. resolve behavior mismatches first
2. compare the slowest endpoints in the timing summary
3. focus on cache-heavy routes such as `timeseries`, plots, and GRIB-derived endpoints when latency changes

This is especially useful before promoting a release from pre-production to production.
4. Update `docs/CACHE.md` when cache architecture, TTL strategy, invalidation behavior, or cleanup guidance changes.
5. Update `docs/TESTING.md` when the test workflow, dependencies, or evaluation criteria change.
6. Update `docs/API_ENDPOINTS.md` if routes or semantics changed.
7. Update `docs/PYTHON_API_TUTORIAL.md` when beginner-facing examples or recommended usage patterns change.
7. Update the Android and iOS tutorial documents when mobile integration guidance changes.
8. Improve the corresponding Flask-RESTX Swagger docstrings or decorators.
