# Installation

## Supported installation models

The checked-in image uses Python 3.8 and uWSGI. A virtual environment is convenient for development; Docker is the closest match to deployment. Scientific packages have native dependencies, so installation on a newer Python version may require different package versions or compilation fixes.

## Local development environment

Install a compiler toolchain plus NetCDF/HDF5, GEOS/PROJ, BLAS/LAPACK, PostgreSQL, and Python development headers using the package manager for your operating system. Then install into an isolated environment:

```bash
python3.8 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

If `wrf-python`, `netCDF4`, `basemap`, `psycopg2`, or `uwsgi` fails to build, inspect the first compiler error and install the missing native development package. Avoid resolving build errors by removing a runtime dependency: imports occur while the application namespaces and shared services are initialized.

## Backing services

The full endpoint surface expects:

- memcached at `MEMCACHED_SERVER` for hot response caching
- MongoDB reachable by the current MongoDB handlers for place metadata
- PostgreSQL at `SQLALCHEMY_DATABASE_URI` or `DATABASE_URL`
- mounted NetCDF archive/history trees
- writable product, JSON, Skew-T, and disk-cache directories

Only start the services required for the endpoints you are developing. Unit tests mock service boundaries and do not require production datasets.

## Docker image

Build from the repository root:

```bash
docker build -t it-uniparthenope-meteo-api .
```

The image sets `APP_SETTINGS=/project/etc/ccmmmaapi.conf`, copies the application to `/project`, changes to the unprivileged `ccmmma` user, and serves HTTP on port 5000 through uWSGI.

A production run must mount the paths named in the settings file. Archive inputs should normally be read-only; cache and generated-output paths must be writable by UID/GID `60005`. Supply secrets through deployment configuration rather than committing them.

## Production server

For a local production-like launch:

```bash
export APP_SETTINGS=/absolute/path/to/settings.py
uwsgi --ini ccmmmaapi.ini
```

The uWSGI configuration starts multiple worker processes. Size worker and request-timeout values against available RAM and the largest NetCDF request; every process can hold its own scientific-library and dataset memory. Put uWSGI behind a TLS-terminating reverse proxy and configure request/body limits there.

## Upgrade procedure

1. Review `requirements.txt`, settings, schema, and mount changes.
2. Build a new environment or image rather than modifying a running one.
3. Run `python -m compileall -q app.py wsgi.py apis core tests` and `pytest -q`.
4. Validate representative metadata, forecast, time-series, image, and operational routes in staging.
5. Decide whether changed response or cache semantics require targeted invalidation and rebuild; follow [CACHE.md](CACHE.md).
6. Roll out with enough overlap to preserve availability, then watch error rate, latency, worker memory, cache writes, and upstream failures.

## Uninstallation and cleanup

A virtual-environment installation is removed by deleting only its dedicated `.venv` directory. Container removal does not remove mounted archives or caches. Treat persistent cache and generated-product volumes as operational data and confirm their exact mount targets before deleting them.
