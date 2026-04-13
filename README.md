# it.uniparthenope.meteo.api

`it.uniparthenope.meteo.api` is the Flask-based service layer that powers the meteorological products and application integrations exposed by the University of Naples Parthenope weather platform.

The project aggregates forecast products, place metadata, legal and CMS content, generated plots, GRIB/NetCDF-derived resources, webcam assets, weather reports, and application-specific datasets behind a single HTTP API. The codebase is designed to run in a containerized environment and relies on a combination of local storage, generated assets, MongoDB, PostgreSQL, memcached, and upstream meteorological archives.

The repository includes both operational documentation for deployers and pedagogical tutorials for students and mobile or web developers who want to consume the API from real applications.

## Main Capabilities

- Publish forecast, time-series, plot, legend, and GRIB-oriented endpoints for supported products.
- Serve place search and lookup APIs backed by the configured metadata store.
- Expose version, legal, login, instruments, webcam, and application-support endpoints.
- Provide `v2` CMS and weather-report APIs for frontend applications.
- Cache expensive responses through memcached and on-disk cache layers.
- Reuse cached hourly slices and shared JSON/CSV payloads for multi-step endpoints such as `timeseries`.
- Parallelize cold multi-time-step extraction with multiprocessing while keeping cache-hit reuse lightweight.
- Track the most popular forecast and time-series request signatures to drive targeted cache rebuilds.
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
2. Review the production rollout guide in [docs/PRODUCTION_SETUP.md](docs/PRODUCTION_SETUP.md).
3. Read the endpoint reference in [docs/API_ENDPOINTS.md](docs/API_ENDPOINTS.md) before integrating a client.
4. Read the testing guide in [docs/TESTING.md](docs/TESTING.md) before validating changes.
5. Verify the runtime paths and environment keys in [etc/ccmmmaapi.conf](etc/ccmmmaapi.conf).
6. Install the Python dependencies from [requirements.txt](requirements.txt).
7. Start the service through `uWSGI` or the project container.
8. Open the Swagger UI exposed by Flask-RESTX at `/` to inspect and test the API surface.

## Learning Paths

- If you want to call the API from scripts, start with [docs/PYTHON_API_TUTORIAL.md](docs/PYTHON_API_TUTORIAL.md).
- If you want to build an Android client, start with [docs/ANDROID_KOTLIN_API_TUTORIAL.md](docs/ANDROID_KOTLIN_API_TUTORIAL.md).
- If you want to build an iPhone app, start with [docs/IOS_SWIFT_API_TUTORIAL.md](docs/IOS_SWIFT_API_TUTORIAL.md).
- If you need a route-by-route reference, use [docs/API_ENDPOINTS.md](docs/API_ENDPOINTS.md).
- If you need to validate endpoint behavior locally, use [docs/TESTING.md](docs/TESTING.md).

## Documentation

- Operational and development guide: [docs/OPERATIONS_AND_USAGE.md](docs/OPERATIONS_AND_USAGE.md)
- Production setup guide: [docs/PRODUCTION_SETUP.md](docs/PRODUCTION_SETUP.md)
- Cache architecture and tuning guide: [docs/CACHE.md](docs/CACHE.md)
- Testing and evaluation guide: [docs/TESTING.md](docs/TESTING.md)
- Live API comparison and timing workflow: [docs/TESTING.md](docs/TESTING.md)
- Endpoint catalog: [docs/API_ENDPOINTS.md](docs/API_ENDPOINTS.md)
- Step-by-step Python tutorial: [docs/PYTHON_API_TUTORIAL.md](docs/PYTHON_API_TUTORIAL.md)
- Step-by-step Android/Kotlin tutorial: [docs/ANDROID_KOTLIN_API_TUTORIAL.md](docs/ANDROID_KOTLIN_API_TUTORIAL.md)
- Step-by-step iOS/Swift tutorial: [docs/IOS_SWIFT_API_TUTORIAL.md](docs/IOS_SWIFT_API_TUTORIAL.md)
- Agent contribution notes: [AGENTS.md](AGENTS.md)
