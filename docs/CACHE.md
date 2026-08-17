# Cache Guide

## Purpose

This document explains how caching works in `it.uniparthenope.meteo.api`, how the memcache and disk-cache layers interact, how to configure them for strong production performance, and how to clean them safely.

Related documents:

- Main project overview: [../README.md](../README.md)
- Operations guide: [OPERATIONS_AND_USAGE.md](OPERATIONS_AND_USAGE.md)
- Production setup guide: [PRODUCTION_SETUP.md](PRODUCTION_SETUP.md)
- Endpoint reference: [API_ENDPOINTS.md](API_ENDPOINTS.md)

## Popularity Tracking

The API now keeps a lightweight popularity log for forecast and time-series request signatures.

The tracker is designed for hot request paths:

- counts are updated in memory
- persistence is batched
- request signatures are normalized so JSON and CSV time-series requests share the same popularity identity

The primary use cases are:

- finding the hottest request signatures per product and place
- targeted cache rebuilds after data refreshes
- targeted invalidation and rewarming instead of full cache wipes

## Why The API Uses Two Cache Layers

The API exposes routes that may:

- query MongoDB or PostgreSQL
- read large NetCDF or GRIB-backed files
- generate plots and derived images
- transform structured data into JSON or CSV

Doing all of that work for every request would increase latency and I/O pressure. For this reason, the service uses two complementary cache layers:

1. memcache for very fast reuse of already computed responses across requests
2. disk cache for reuse of heavier artifacts and larger payloads on the local filesystem

The two layers are designed to reduce repeated work while still allowing the API to rebuild data when source files change or cached objects become stale.

## High-Level Request Flow

For many cache-aware endpoints, the flow is:

1. Build a cache key from the full request URL.
2. Check memcache first.
3. If memcache misses, check the disk cache.
4. If both miss, compute the response from the real data sources.
5. Store the fresh result in disk cache when appropriate.
6. Store the fresh result in memcache.
7. Return the response to the client.

In practice, this means:

- memcache is the fastest layer
- disk cache is the fallback layer for local reuse
- the original data source is only used on a full cache miss or when a cached object has expired

For a small set of expensive endpoints, the application now also supports canonical cache keys that are not tied to a single URL representation. This is important when two routes expose the same structured payload in different formats.

## Memcache Layer

### What It Stores

Memcache is used for fast reuse of recent API responses, especially:

- JSON payloads
- CSV-like structured payloads
- metadata results
- lightweight image response descriptors

The memcache key is usually derived from the request URL using an MD5 hash. This means query parameters are part of the cache identity, which is important because many routes depend on `date`, `place`, `prod`, `output`, or other request parameters.

For selected endpoints, the shared helpers also accept an explicit cache-key override. That allows multiple route shapes to reuse the same cached structured payload when they are semantically identical.

### Current Implementation

The shared memcache logic lives in:

- [core/MemcachedMethodHandlers.py](../core/MemcachedMethodHandlers.py)

Important properties of the current implementation:

- the key is stable for the same request URL
- dictionaries and lists are serialized as JSON before storage
- strings are stored as encoded UTF-8 bytes
- cached bytes are decoded back into Python strings when possible
- JSON payloads can be safely reconstructed through `load_cached_json(...)`

### Why Memcache Is Checked First

Memcache is faster than disk for small and medium payloads because:

- it avoids filesystem traversal
- it avoids opening and reading files
- it can return the payload directly from memory

This is especially useful for hot endpoints such as:

- places lookups
- metadata routes
- repeated forecast or time-series requests for the same parameters

## Disk Cache Layer

### What It Stores

Disk cache is used for local persistence of cacheable responses such as:

- JSON payloads
- CSV-oriented payloads
- generated plot images

The shared disk-cache logic lives in:

- [core/ManageDiskCache.py](../core/ManageDiskCache.py)

### Directory Structure

Disk-cache files are stored by day in a folder structure like:

```text
BASE_DISKCACHE/<year>/<month>/<day>/
```

Examples:

```text
/project/diskcache/2026/3/17/
/project/diskcache/2026/3/18/
```

Inside each daily directory, files are named with the MD5 hash of the request URL or explicit cache-key source plus an extension:

- `.json`
- `.csv`
- `.png`

This keeps the cache simple and avoids very long filenames.

### Current Read Behavior

When the disk cache is queried:

1. the request URL or canonical cache-key source is hashed
2. the helper checks the expected cache file paths directly
3. if a cache file exists, the helper validates:
   - whether the source archive file is newer
   - whether the cache file is older than the TTL
4. expired or invalid files are deleted immediately
5. valid files are loaded and returned

### Current Write Behavior

When storing to disk cache:

- JSON and CSV cache entries are written as JSON text
- plot cache entries are written as binary payloads
- the required daily directory is created automatically

This behavior is important because plot endpoints should not be written in text mode, while structured payloads should be written in a stable text representation.

## How The Two Layers Work Together

The two cache layers are not identical.

Memcache is best for:

- very fast reuse
- short-lived hot keys
- response sharing without filesystem access

Disk cache is best for:

- larger local artifacts
- reusing expensive generated results
- fallback reuse when memcache has been cleared or restarted

A good mental model is:

- memcache is the fast front layer
- disk cache is the heavier local persistence layer

## Multi-Step Endpoint Optimization

The most expensive public routes are usually the multi-time-step endpoints, especially:

- `GET /products/<prod>/timeseries/<place>`
- `GET /products/<prod>/timeseries/<place>/csv`

Those routes now use the cache system in two complementary ways.

### 1. Shared top-level cache for JSON and CSV time series

The JSON and CSV routes expose the same underlying time-series payload. They now use the same canonical cache key based on the request-driving parameters:

- product
- place
- date
- aggregation step
- number of hours
- option string

This means:

- a JSON request can warm the cache for the CSV route
- a CSV request can warm the cache for the JSON route
- the expensive `timeseries(...)` computation is only done once per canonical request

The CSV route now reuses the structured cached payload and only performs the lightweight CSV rendering step on top of it.

### 2. Per-time-step reuse inside `MeteoServices.timeseries(...)`

The `timeseries(...)` builder internally fans out across multiple forecast hours and calls `modelOutput(...)` for each one. That path now honors the existing `use_disk_cached` flag instead of forcing `modelOutput(...)` to bypass its on-disk JSON cache.

This reduces repeated work for hot time-series requests because:

- already-generated per-hour `modelOutput(...)` JSON files can be reused
- repeated NetCDF reads for the same hourly slices are avoided
- the thread pool focuses on cache hits instead of recomputation when the hourly slices are already present

In production, this is the main performance improvement for repeated requests against the same place and product over many forecast steps.

### 3. Multiprocessing for cache misses

After partitioning the hourly items into cache hits and cache misses, the service now uses a hybrid execution strategy:

- cached hourly slices are loaded in-process with threads
- uncached hourly slices can be computed with a process pool

This is useful because the expensive part of a cold request is the NetCDF-backed extraction work, not the cache lookup itself.

The relevant configuration keys are:

- `NUM_THREADS` for local cache-load concurrency and thread fallback
- `NUM_PROCESSES` for cold-slice multiprocessing fan-out
- `TIMESERIES_PARALLEL_MODE` to choose the execution mode

Recommended production setting:

- keep `TIMESERIES_PARALLEL_MODE="processes"` for multi-core hosts
- size `NUM_PROCESSES` conservatively to the number of physical or effective cores available to the API container
- avoid setting `NUM_PROCESSES` so high that multiple large requests oversubscribe CPU and disk bandwidth

## Important Configuration Keys

The most important cache-related settings are in `etc/ccmmmaapi.conf`:

- `BASE_DISKCACHE`
- `TTL_MEMCACHED`
- `TTL_DISKCACHE`
- `POPULAR_REQUESTS_LIMIT`
- `REQUEST_POPULARITY_FLUSH_EVERY`
- `REQUEST_POPULARITY_FLUSH_INTERVAL`
- `REQUEST_POPULARITY_PATH`

### `BASE_DISKCACHE`

This is the root directory for on-disk cached artifacts.

Production recommendation:

- place it on fast local SSD or low-latency attached storage
- do not store it inside a slow remote filesystem unless necessary
- ensure the API process can create directories and write files under it

### `TTL_MEMCACHED`

This controls how long objects should remain valid in memcache.

Production recommendation:

- use a shorter TTL than disk cache
- keep it tuned for hot traffic reuse rather than long-term persistence

A reasonable rule of thumb is:

- memcache for minutes to a few hours
- disk cache for longer reuse when source data does not change frequently

### `TTL_DISKCACHE`

This controls how long the disk-cache entries are considered valid.

Production recommendation:

- choose a value based on how often underlying source files change
- keep it long enough to absorb repeated expensive requests
- keep it short enough that stale local files do not accumulate excessively

## Production Performance Recommendations

## 1. Memcache Placement

For best performance:

- keep memcached on the same private network as the API container
- minimize network hops
- avoid internet-routable cache access
- keep memcached latency low and predictable

If memcache is too slow, the application can still work, but the cache layer stops being a performance win.

## 2. Memcache Timeouts

The application now uses short memcache client timeouts in [app.py](../app.py) so a slow cache server does not block request handling for too long.

Production recommendation:

- keep these timeouts conservative
- prefer a fast failure and fallback to disk cache or recomputation
- monitor memcache availability separately from API latency

## 3. Disk Cache Storage Choice

For best disk-cache performance:

- use local SSD whenever possible
- avoid high-latency network filesystems for the cache directory
- keep the cache on storage with good small-file performance
- ensure enough free inode capacity if the cache will hold many files

## 4. Separate Immutable Data From Cache Data

Do not mix:

- archive/history source data
- generated products
- disk-cache files

Keeping them separate makes:

- cache cleanup safer
- observability easier
- incident recovery less risky

## 5. Tune TTLs By Endpoint Behavior

Not all endpoints benefit equally from the same TTL.

For example:

- lightweight metadata endpoints can tolerate shorter TTLs because recomputation is cheap
- time-series endpoints benefit from longer disk-cache reuse because they aggregate many hourly reads
- plot and legend endpoints may need TTLs aligned with product regeneration frequency

When tuning the system, treat multi-step endpoints as the primary beneficiaries of the disk-cache layer.

## Targeted Invalidation And Rebuild

The products namespace now exposes two cache-maintenance endpoints:

- `GET /products/<prod>/invalidate/<place>/?date=YYYYMMDDZhhmm&hours=n`
- `GET /products/<prod>/rebuild/?date=YYYYMMDDZhhmm&hours=n`

The invalidate endpoint:

- removes the per-hour `modelOutput(...)` JSON cache files under `CACHE_JSON`
- removes matching top-level forecast and time-series cache entries from memcache and disk cache
- scopes the work to one product/place and one time window
- resolves the meteo service, both cache layers, and the persisted popularity
  tracker from the active Flask application's runtime-service container

The rebuild endpoint:

- looks up the most popular forecast and time-series signatures for the selected product
- rebuilds them for the requested start date and hour window
- uses the popularity tracker so operators can warm the caches that matter most first
- writes through the configured disk and memory layers using the same canonical
  keys as the public forecast and time-series handlers; disabled cache layers
  remain disabled during operational warming

Examples:

- metadata endpoints can usually tolerate longer TTLs
- endpoints tied to changing archive files may need shorter TTLs
- image-generation endpoints often benefit from disk cache more than tiny metadata routes

If you observe cache churn or stale results, do not only increase TTLs. First verify:

- source data update frequency
- request diversity
- cache hit rate
- file invalidation behavior

## 6. Warm Important Hot Keys After Deployment

For high-traffic production systems, a useful strategy is to warm a small set of common endpoints after rollout, for example:

- `/version`
- one common place lookup
- one common forecast route
- one common time-series route

This reduces cold-start latency immediately after deployment or restart.

## Best Cache-Clean Strategies

There is no single universal cleaning strategy. The best approach depends on what changed.

## Strategy 1. TTL-Driven Normal Operation

Use this as the default strategy.

Behavior:

- let memcache evict naturally by TTL
- let disk cache expire entries naturally by TTL
- let the API delete outdated disk-cache files when they are accessed

Use this when:

- no response shape changed
- no serialization format changed
- source data is updating normally

Pros:

- minimal operational work
- low risk
- good steady-state performance

Cons:

- old files may remain on disk until accessed or cleaned externally

## Strategy 2. Rolling Memcache Flush Only

Use this when:

- a deployment changed response content but not disk-cache file format
- you want hot keys to be recomputed quickly
- disk cache is still considered structurally valid

Behavior:

- clear or restart memcache
- keep disk cache
- allow the API to repopulate memcache from disk cache or fresh computation

Pros:

- fast and simple
- low impact

Cons:

- if disk cache is also stale, stale data may still be reused

## Strategy 3. Selective Disk-Cache Cleanup

Use this when:

- only a subset of routes changed behavior
- only one product family changed
- only one day of cached files is problematic

Behavior:

- remove only the relevant daily disk-cache directories or known cache files
- keep memcache and unrelated disk cache intact

Pros:

- minimizes cold-cache impact
- preserves good hot data

Cons:

- requires operational precision

## Strategy 4. Full Cache Invalidation

Use this when:

- response serialization changed
- cache key semantics changed
- binary/text cache behavior changed
- a major release invalidated prior cached content

Behavior:

- flush memcache
- remove disk-cache directories
- redeploy and warm the most important endpoints

Pros:

- clean reset
- avoids subtle stale-format bugs

Cons:

- largest temporary performance hit
- highest recomputation cost immediately after rollout

## Recommended Production Cleaning Policy

For most production systems, a balanced policy is:

1. rely on TTL for day-to-day operation
2. use selective cleanup for localized issues
3. flush memcache on deployments that change response content significantly
4. use full cache invalidation only for structural cache changes

## Disk Cache Cleanup Best Practices

### Clean By Age

The safest routine cleanup is age-based deletion.

Examples:

- remove daily directories older than a retention period
- keep the last few days if the API commonly serves recent data

This is usually better than deleting random individual files because the cache is already organized by day.

### Clean By Deployment Window

If a release changes cache serialization or cacheable response structure:

- schedule a cache cleanup during deployment
- warm a small set of hot endpoints immediately after

This prevents users from paying the full cold-start cost on the first real traffic burst.

### Clean By Disk Pressure

If the cache volume grows too much:

- delete the oldest daily directories first
- preserve the most recent days
- avoid deleting source archive data by mistake

### Never Mix Cleanup Targets

Do not confuse:

- `BASE_DISKCACHE`
- source data directories
- generated product directories

A cleanup script should target only the disk-cache root unless you are intentionally removing another kind of generated artifact.

## Memcache Cleanup Best Practices

Memcache is ephemeral by design. The most common strategies are:

- let TTL expire keys naturally
- restart memcache during deployment when needed
- flush the memcache instance only when a deployment invalidates cached response content

Best practice:

- do not flush memcache on every deployment by default
- flush it when you know cache reuse would be incorrect
- prefer targeted operational reasoning over habitual full resets

## Suggested Production Monitoring

Monitor at least:

- API latency by endpoint family
- memcache reachability and error rate
- disk usage of `BASE_DISKCACHE`
- cache growth over time
- frequency of cold-start recomputation for expensive endpoints

Warning signs:

- memcache timeouts becoming frequent
- disk-cache directories growing without retention cleanup
- repeated stale-data reports after deployments
- image-generation endpoints becoming slow after cache misses

## Practical Setup Checklist

Before production rollout, confirm:

- memcached is reachable from the API container
- `BASE_DISKCACHE` exists and is writable
- `TTL_MEMCACHED` and `TTL_DISKCACHE` are explicitly reviewed
- disk cache is on fast storage
- a retention cleanup strategy exists
- cache invalidation steps are part of the deployment checklist

## Practical Example Policy

An example policy for a production installation could be:

- keep memcache TTL short enough for fast reuse of hot requests
- keep disk cache TTL longer than memcache TTL
- run a daily cleanup job that removes old disk-cache day directories
- flush memcache only on deployments with response-shape changes
- fully clear both layers only on structural cache changes

## Final Recommendation

If you want the best production performance, optimize in this order:

1. make sure the source data and generated assets are on fast storage
2. keep memcached low-latency and close to the API
3. use disk cache on local SSD
4. tune TTLs using real traffic patterns
5. clean caches deliberately, not aggressively

The goal is not to maximize cache size. The goal is to maximize useful cache hits while keeping stale or incompatible cache content under control.
