# Core Services Architecture

The `core` package contains application services and infrastructure shared by
the Flask API namespaces. Route handlers should translate HTTP inputs and
outputs; data access, archive resolution, transformations, and caching belong
in these services.

## Dependency Direction

The intended dependency direction is:

```text
API namespaces
    -> RuntimeServices
        -> domain services (MeteoServices, GribServices, Places, Tiles)
        -> infrastructure (disk cache, memcache, popularity tracking)
            -> small utilities (cache keys, logging, path construction)
```

Lower layers must not import Flask application globals. Required configuration
and collaborators are passed explicitly so services can be tested in isolation.

## Cache Infrastructure

`core/cache_keys.py` is the single source of truth for cache-key hashing. Both
`ManageDiskCache` and `MemcachedMethodHandlers` delegate to it, preserving the
existing MD5 key format and canonical-key overrides.

`ManageDiskCache` performs direct daily-path lookups, caches filesystem metadata
within each read operation, and publishes writes with an atomic rename. A
malformed, expired, or concurrently deleted entry is an ordinary cache miss.

## Archive Paths

`MakeArchivePaths` owns parsing of `YYYYMMDDZHHMM` timestamps and construction
of current or historical NetCDF paths. Domain resolution stays in `Places`.
Callers must pass configuration explicitly; the helper does not reach into the
Flask application context.

## Maintenance Rules

- Preserve API response shapes while refactoring service internals.
- Keep cache keys compatible across memory, disk, invalidation, and rebuild paths.
- Write large cache artifacts atomically and avoid duplicate in-memory buffers.
- Prefer dependency injection over process-global application state.
- Comment invariants and design tradeoffs, not self-explanatory statements.
- Add focused unit tests before moving behavior between service boundaries.
