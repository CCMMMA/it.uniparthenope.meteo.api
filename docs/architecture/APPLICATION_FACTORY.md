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

## Consequences

Positive consequences include explicit service ownership, a stable seam for dependency substitution, and a gradual route away from circular imports. The factory also makes configuration ordering visible: database configuration is loaded before `db.init_app()`.

During the transition, the extension container and legacy globals reference the same objects. This duplication is intentional and is verified by a bootstrap contract test. The factory currently creates heavyweight services eagerly because changing their lifetime could alter cache, worker-pool, and request behavior. Lazy construction may be considered only after measurement and dedicated lifecycle tests.

## Validation

Each bootstrap change requires Python syntax validation and the complete endpoint unit suite because shared service wiring affects every namespace. Production deployment continues to load `wsgi:application` until a separately tested deployment migration is approved.
