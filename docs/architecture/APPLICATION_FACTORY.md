# Application Factory and Dependency Composition

## Status

Accepted as the incremental bootstrap architecture for the versioned API migration.

## Context

Historically, importing `app.py` constructed the Flask application and every shared service as unrelated module globals. Route modules then imported `app` to reach configuration, caches, meteorological services, GRIB services, tile generation, and popularity tracking. This arrangement works for a single process-level application, but it obscures dependency ownership and creates circular imports between transport and application layers.

The refactoring must preserve the established WSGI symbol and all endpoint behavior. A simultaneous rewrite of every handler would create an unnecessarily large compatibility risk, particularly for cached forecast and time-series routes.

## Decision

`create_app()` is the composition root. In a fixed order it:

1. creates the Flask object;
2. loads deployment configuration;
3. initializes database, CORS, RESTX, and version-response behavior;
4. constructs long-lived runtime services;
5. stores one typed `RuntimeServices` container in `application.extensions["meteo_api"]`; and
6. publishes compatibility globals for handlers that have not yet migrated.

The module still evaluates `application = create_app()` so `from app import application` and `wsgi:application` remain valid.

## Dependency rule

New transport code accesses shared services through Flask's application context:

```python
services = current_app.extensions["meteo_api"]
```

It must not introduce new imports of the top-level `app` module. Existing imports are migrated in bounded resource-family changes with their local and live contract tests.

## Migration record

| Resource family | Dependency access | Compatibility status |
| --- | --- | --- |
| `/version` | `current_app.config` plus shared version metadata | Migrated; response contract preserved |
| `/legal/*` | `current_app.extensions["meteo_api"].meteo` | Migrated; response contract preserved |
| `/instruments/*` | `current_app.extensions["meteo_api"].meteo` | Migrated; list, detail, and legacy 404 preserved |
| `/webcam/*` | `current_app.config` | Migrated; JPEG fallback behavior preserved |
| `/box/*` | No application dependency | Reviewed; already decoupled |
| `/v2/slurm/*` | `current_app.config` | Migrated; response contracts preserved |
| `/v2/carousel`, `/v2/cards` | Removed with their CMS/authentication helpers | Retired by explicit decision; 404 enforced |
| `/v2/basemaps`, `/v2/layers`, `/v2/maps` | Static module data | Reviewed; no application dependency |
| `/places/*` | Runtime memory/disk caches plus `current_app.config` | Migrated; cache order and response contracts preserved |
| `/apps/owm/*` | Runtime caches and injected long-lived tile service | Migrated; disk-hit promotion and worker reuse preserved |
| `/products` metadata and availability routes | `current_app.extensions["meteo_api"].meteo` | Migrated; payload contracts preserved |
| `/products/{prod}/forecast/{place}` JSON | Runtime service, caches, and popularity tracker | Migrated; canonical key and cache order preserved |
| `/products/{prod}/timeseries/{place}` JSON and CSV | Runtime service, caches, archive config, and popularity tracker | Migrated together; shared structured cache preserved |
| `/products/{prod}/forecast/{domain}/grib/{text,json}` | Runtime GRIB service, memory cache, and application config | Migrated together; representation and cache contracts preserved |
| `/products/{prod}/forecast/{place}/plot/image` and `/products/wrf5/forecast/plot/SkewT/image` | Runtime meteo service and caches | Migrated together; PNG and cache-order contracts preserved |
| `/products/{prod}/forecast/legend/{position}/{output}` standard and ncWMS variants | Runtime meteo service, memory cache, and application config | Migrated together; binary representation and URL-keyed cache separation preserved |
| `/products/{prod}/plot/{output}/metacharts` | Runtime meteo service plus memory and disk caches | Migrated; memory-first order preserved and disk-hit promotion added |
| `/products/{prod}/forecast/{place}/plot/alt` | Runtime meteo service plus request-scoped place lookup using `current_app.config` | Migrated; localized place-name and response contracts preserved |
| `/products/{prod}/forecast/{place}/map/image` | Runtime meteo service and memory cache | Migrated; legacy PNG compatibility contract preserved without per-request service construction |
| `/products/{prod}/forecast/{place}/plot` | Runtime meteo service plus memory and disk caches | Migrated; JSON/inline response behavior and fallback URL preserved, with disk-hit promotion added |
| `/products/{prod}/invalidate/{place}/` and `/products/{prod}/rebuild/` | Runtime meteo service, caches, popularity tracker, and application config | Migrated together; canonical-key invalidation and popularity-driven warming preserved |
| Other legacy namespaces | Transitional module globals | Pending bounded migration |

Archive-path construction is also dependency-explicit. `MakeArchivePaths.makePath`
requires the owning service or request handler to supply its configuration; it
never imports the composition root as a fallback. This prevents core-to-web
dependency inversion and ensures application-factory instances cannot silently
read paths from a different process-global application.

The legal migration also removes construction of a new `MeteoServices` object for every request. Legal content now uses the process-level service created by the composition root, avoiding repeated parsing of maps and legal configuration files.

The instrument migration similarly reuses the composed meteorological service while retaining an upstream lookup for each request. Caching or changing that lookup frequency would alter freshness semantics and therefore requires a separate measured change. Webcam fallback resolution now uses the active Flask configuration without changing its established filesystem path or `image/jpg` media type.

Place handlers retain their established lookup sequence: memcached, disk cache, and finally the MongoDB-backed `Places` service. Cold source results are written to disk and then memcached. Disk hits are not newly promoted in this migration because that would change established cache behavior; such promotion should be evaluated separately with latency and staleness measurements.

OWM tile handlers retain their distinct promotion policy: a disk hit is written back to memcached because tile payloads are comparatively large and repeatedly decoding them from disk is avoidable work. `Tiles` now receives the composed meteorological service explicitly and retains one bounded executor for its full lifetime; neither a handler nor an individual cache miss constructs a worker pool.

## Consequences

Positive consequences include explicit service ownership, a stable seam for dependency substitution, and a gradual route away from circular imports. The factory also makes configuration ordering visible: database configuration is loaded before `db.init_app()`.

During the transition, the extension container and legacy globals reference the same objects. This duplication is intentional and is verified by a bootstrap contract test. The factory currently creates heavyweight services eagerly because changing their lifetime could alter cache, worker-pool, and request behavior. Lazy construction may be considered only after measurement and dedicated lifecycle tests.

## Validation

Each bootstrap change requires Python syntax validation and the complete endpoint unit suite because shared service wiring affects every namespace. Production deployment continues to load `wsgi:application` until a separately tested deployment migration is approved.
