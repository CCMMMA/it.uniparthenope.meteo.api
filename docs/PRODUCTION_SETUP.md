# Production Setup Guide

Related documents:

- Operational guide: [OPERATIONS_AND_USAGE.md](OPERATIONS_AND_USAGE.md)
- Cache guide: [CACHE.md](CACHE.md)
- Endpoint reference: [API_ENDPOINTS.md](API_ENDPOINTS.md)
- Python tutorial: [PYTHON_API_TUTORIAL.md](PYTHON_API_TUTORIAL.md)
- Android tutorial: [ANDROID_KOTLIN_API_TUTORIAL.md](ANDROID_KOTLIN_API_TUTORIAL.md)
- iOS tutorial: [IOS_SWIFT_API_TUTORIAL.md](IOS_SWIFT_API_TUTORIAL.md)

## Goal

This document describes a practical production setup for `it.uniparthenope.meteo.api`, including infrastructure dependencies, filesystem layout, configuration, container runtime expectations, validation, and rollout guidance.

## Application bootstrap

`app.create_app()` is the application factory and composition root. It creates the Flask application, loads `APP_SETTINGS`, initializes extensions, and constructs the reusable meteorological, GRIB, tile, cache, and popularity-tracking services.

The WSGI contract remains backward compatible: `wsgi.py` exports the fully initialized `application` object, and existing uWSGI configuration does not need to change. Tests and future deployment tools may use `create_app()` when they require an independently constructed application.

## Required Services

Prepare the following before starting the API:

- reverse proxy or ingress with TLS termination
- the API container itself
- memcached
- MongoDB
- PostgreSQL
- mounted forecast archive/history storage
- mounted generated image and cache storage

Optional but commonly needed:

- Slurm access for `v2/slurm/*`
- Signal K endpoint for `/instruments`
- centralized logging
- monitoring and alerting

## Recommended Topology

Typical production traffic flow:

1. Client sends HTTPS request to the reverse proxy.
2. Reverse proxy forwards traffic to the uWSGI-backed Flask container.
3. The API checks memcached and disk cache first.
4. On a cache miss, the API reads local filesystems and backing data sources.
5. The API returns JSON, PNG, or CSV depending on the endpoint.

## Production Filesystem Layout

The committed configuration expects paths such as:

- `/project/etc`
- `/project/images`
- `/project/diskcache`
- `/storage/ccmmma/prometeo/data/opendap`
- `/data1/ccmmma/prometeo/data/opendap`

In production, confirm that:

- archive and history data are mounted and readable
- generated image directories are writable
- disk cache directories are writable
- static fallback assets such as `noimage.png` exist at the configured location

## Configuration Checklist

Validate these keys before rollout:

- `APP_SETTINGS`
- `BASE_PATH`
- `BASE_STORAGE_PATH`
- `BASE_PRODUCTS`
- `BASE_DISKCACHE`
- `MAPS`
- `LEGAL`
- `PAGES`
- `NOIMAGE_PATH`
- `NOIMAGE_URL`
- `TTL_MEMCACHED`
- `TTL_DISKCACHE`
- `ENV`

Also verify hostnames and credentials for:

- PostgreSQL
- MongoDB
- memcached

### API-key database schema

Before enabling API-key management in an environment, back up PostgreSQL and
apply the checked-in schema migration exactly once:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f migrations/001_api_keys.sql
```

The migration creates request, key, and lifecycle-audit tables. Application
startup deliberately does not call `db.create_all()` in production: schema
changes remain an explicit, reviewable deployment operation. Deploy the domain
code before any future authentication middleware, verify the tables and indexes,
and keep existing endpoint enforcement disabled during this checkpoint.

## Container Build

The repository ships a [Dockerfile](../Dockerfile) that:

- starts from Python 3.8
- installs OS-level numeric/scientific dependencies
- installs Python dependencies from `requirements.txt`
- copies the project into `/project`
- launches `uWSGI`

Example:

```bash
docker build -t it-uniparthenope-meteo-api:prod .
```

## Container Runtime

Production runtime expectations:

- `APP_SETTINGS` points to the active config file
- all configured directories are mounted correctly
- the container can reach memcached, MongoDB, PostgreSQL, and any optional upstream endpoints
- the reverse proxy forwards the intended base URL and headers

Example environment:

```bash
APP_SETTINGS=/project/etc/ccmmmaapi.conf
```

## Reverse Proxy

Recommended reverse-proxy responsibilities:

- TLS termination
- request size and timeout controls
- access logging
- gzip or brotli where appropriate
- forwarding to the uWSGI service port

Expose the Swagger UI at the API root path `/`.

## Health and Smoke Tests

After deployment, validate at least:

- `GET /`
- `GET /version`
- `GET /legal/disclaimer`
- `GET /products`
- one cache-backed `places` endpoint
- one cache-backed `products` endpoint

If the environment supports them, also validate:

- `GET /instruments`
- `GET /v2/slurm/info`

## Caching Guidance

The API uses two caching layers:

- memcached for quick response reuse across requests
- disk cache for larger or more persistent local reuse

Production recommendations:

- keep memcached reachable with low latency
- place disk cache on fast local or attached storage
- clear caches during major response-shape or serialization changes
- monitor cache volume growth over time

For a detailed cache architecture, tuning, and cleanup strategy, see [CACHE.md](CACHE.md).

## Deployment Procedure

1. Build the image.
2. Deploy to staging with production-like mounted storage.
3. Run smoke tests.
4. Verify Swagger at `/`.
5. Verify forecast, place, and legal endpoints.
6. Promote to production.
7. Watch logs and error rates after rollout.

## Rollback Procedure

If a rollout fails:

1. revert traffic to the previous image
2. keep configuration consistent with the restored image
3. clear caches if incompatible response payloads were introduced
4. re-run smoke tests on the rolled-back version

## Operational Best Practices

- do not expose backend services directly to the public internet
- treat filesystem mounts as part of the deployment contract
- keep cache directories out of the immutable image layer
- ship logs to external storage or observability tooling
- use staging before production for dependency or serialization changes
