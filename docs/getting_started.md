# Getting started

This guide gets a developer from a fresh checkout to a locally testable instance of the meteorological API. The service can start without production forecast archives, but data-dependent endpoints need the files and backing services described below.

## Prerequisites

- Python 3.8 (the version used by the container) and a C/Fortran build toolchain
- native libraries required by netCDF4, wrf-python, Basemap, SciPy, and PostgreSQL
- optional local or containerized memcached, MongoDB, and PostgreSQL services
- access to forecast/history NetCDF archives for product endpoints

For a complete dependency setup, see [installation.md](installation.md). Configuration keys and path requirements are documented in [configuration.md](configuration.md).

## Repository map

- `app.py` creates the Flask application and shared services.
- `wsgi.py` exports `application` for uWSGI.
- `apis/` contains Flask-RESTX namespaces and HTTP handlers.
- `core/` contains product, place, cache, plotting, and external-service logic.
- `etc/` contains the example Python configuration and JSON metadata.
- `vars-control-file/` describes variables exposed by each model.
- `tests/` contains isolated endpoint tests and optional live-contract tests.

## First local run

Create and activate an environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Copy `etc/ccmmmaapi.conf` to an untracked local file. Replace `/project` and `/storage` paths with absolute, writable local paths. At minimum, create the directories configured by `BASE_DISKCACHE`, `CACHE_JSON`, `BASE_PRODUCTS`, and `BASE_SKEWT`, and make `LEGAL`, `MAPS`, `PAGES`, and `VARS_CONTROL_PATH` point to repository resources.

```bash
export APP_SETTINGS=/absolute/path/to/local_settings.py
flask --app app:application run --host 127.0.0.1 --port 5000
```

Open `http://127.0.0.1:5000/` for Swagger UI. A low-dependency smoke check is:

```bash
curl http://127.0.0.1:5000/version/
```

Route details are catalogued in [API_ENDPOINTS.md](API_ENDPOINTS.md).

## Validate the checkout

Run syntax and isolated endpoint checks from the repository root:

```bash
python -m compileall -q app.py wsgi.py apis core tests
pytest -q
```

The regular suite supplies temporary writable paths and mocks expensive services. Live API tests only run when explicitly given `--live-base-url`; see [TESTING.md](TESTING.md).

## Expected partial failures

Swagger and metadata routes can work while product routes fail. For product, plot, time-series, or GRIB routes, verify that the configured archive contains the expected model/domain/date hierarchy. Place routes require MongoDB data; model-backed routes require PostgreSQL; instruments and Slurm routes require their corresponding upstream services.

Memcached is an optimization, not the source of truth. If it is unavailable, requests should fall back to computation and disk cache, but latency will increase.

## Next steps

- Use [installation.md](installation.md) for native packages, Docker, and production serving.
- Use [configuration.md](configuration.md) to build an environment-specific settings file.
- Use [extending.md](extending.md) before adding an endpoint, product, cache key, or service.
- Use [CACHE.md](CACHE.md) for invalidation and popularity-driven rebuild behavior.
