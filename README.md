# it.uniparthenope.meteo.api

`it.uniparthenope.meteo.api` is the Flask-based service layer that powers the meteorological products and application integrations exposed by the University of Naples Parthenope weather platform.

The project aggregates forecast products, place metadata, legal and CMS content, generated plots, GRIB/NetCDF-derived resources, webcam assets, weather reports, and application-specific datasets behind a single HTTP API. The codebase is designed to run in a containerized environment and relies on a combination of local storage, generated assets, MongoDB, PostgreSQL, memcached, and upstream meteorological archives.

## Main Capabilities

- Publish forecast, time-series, plot, legend, and GRIB-oriented endpoints for supported products.
- Serve place search and lookup APIs backed by the configured metadata store.
- Expose version, legal, login, instruments, webcam, and application-support endpoints.
- Provide `v2` CMS and weather-report APIs for frontend applications.
- Cache expensive responses through memcached and on-disk cache layers.
- Generate or proxy image products, including legends, plots, and Skew-T diagrams.

## Architecture Overview

- [app.py](app.py): Flask application factory-style bootstrap, cache clients, and service singletons.
- [apis/](apis): Flask-RESTX namespaces used to expose Swagger/OpenAPI documentation and HTTP routes.
- [core/](core): domain logic for products, places, plotting, GRIB/NetCDF processing, CMS, login, Slurm integration, and helpers.
- [etc/](etc): runtime configuration and JSON metadata.
- [data/](data) and [static/](static): bundled assets and reference files.

## Runtime Characteristics

- Python 3.8 application served with `uWSGI`.
- Flask-RESTX provides the HTTP routing and Swagger UI.
- Disk cache and memcached are both used to reduce repeated computation and I/O.
- Product endpoints expect archive/history datasets and generated assets to exist at configured filesystem paths.
- Some services depend on external systems such as MongoDB, PostgreSQL, Signal K, Slurm, and static storage volumes.

## Quick Start

1. Review the deployment and development guidance in [docs/OPERATIONS_AND_USAGE.md](docs/OPERATIONS_AND_USAGE.md).
2. Verify the runtime paths and environment keys in [etc/ccmmmaapi.conf](etc/ccmmmaapi.conf).
3. Install the Python dependencies from [requirements.txt](requirements.txt).
4. Start the service through `uWSGI` or the project container.
5. Open the Swagger UI exposed by Flask-RESTX to inspect and test the API surface.

## Documentation

- Operational and development guide: [docs/OPERATIONS_AND_USAGE.md](docs/OPERATIONS_AND_USAGE.md)
- Endpoint catalog: [docs/API_ENDPOINTS.md](docs/API_ENDPOINTS.md)
- Agent contribution notes: [AGENTS.md](AGENTS.md)
