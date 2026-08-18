# Configuration

## Loading settings

`app.py` requires `APP_SETTINGS` to name an absolute Python configuration file. Settings are loaded before Flask extensions and shared services initialize. `DATABASE_URL` is accepted as a database-URI fallback; an explicit `SQLALCHEMY_DATABASE_URI` in the settings file takes precedence.

```bash
export APP_SETTINGS=/absolute/path/to/settings.py
```

The committed `etc/ccmmmaapi.conf` is a deployment example, not a portable development configuration. It contains no production secrets and assumes `/project` and `/storage` mounts.

## URL and presentation settings

| Key | Purpose |
| --- | --- |
| `HOME_URL`, `BASE_URL` | Public site/API bases used in generated links and remote calls. |
| `DODS_URL`, `WMS_URL` | OPeNDAP and ncWMS URL templates. Preserve the `%s` placeholders in `DODS_URL`. |
| `PUB_URL` | Public base for generated images. |
| `CHART_PAGE`, `TABLE_PAGE`, `FORECAST_PAGE` | Frontend route fragments returned to clients. |
| `NOIMAGE_URL` | Public fallback-image URL. |
| `LANG`, `ENV` | Default language and environment label exposed by `/version`. |

## Filesystem settings

| Key | Access | Purpose |
| --- | --- | --- |
| `BASE_PATH` | read | Forecast/archive model root. |
| `BASE_PATH_HISTORY`, `BASE_STORAGE_PATH` | read | Historical dataset roots used by legacy and current paths. |
| `PRODS_PATH`, `VARS_CONTROL_PATH` | read | Product and variable-control metadata. |
| `BASE_PRODUCTS` | read/write | Generated plots, legends, and product images. |
| `BASE_SKEWT` | read/write | Generated Skew-T images. |
| `CACHE_JSON` | read/write | Shared JSON/CSV and hourly-slice cache. |
| `BASE_DISKCACHE` | read/write | HTTP/resource disk cache. |
| `REQUEST_POPULARITY_PATH` | read/write | Persisted hot-request counters; normally inside `BASE_DISKCACHE`. |
| `NOIMAGE_PATH` | read | Local fallback image. |
| `LEGAL`, `MAPS`, `PAGES` | read | JSON metadata files. |

Use absolute paths. Create writable directories before startup, keep path ownership aligned with the service user, and preserve the archive layout expected by `core/MakeArchivePaths.py` and the meteorological services. Do not point two environments at the same writable cache unless their data, URLs, and cache semantics are identical.

Archive-path construction receives the active application configuration
explicitly from `MeteoServices` or the request handler. There is no fallback to
a module-global Flask application; tests and auxiliary callers must therefore
pass `config=` when invoking `MakeArchivePaths.makePath` directly.

## Cache and concurrency settings

| Key | Meaning |
| --- | --- |
| `MEMCACHED_SERVER` | pymemcache endpoint, for example `memcached:11211`. |
| `TTL_MEMCACHED` | Hot-cache lifetime in seconds. |
| `TTL_DISKCACHE` | Disk-cache lifetime in seconds. |
| `CACHE_TIMEOUT` | Legacy plot/GRIB cache lifetime; normally set to `TTL_DISKCACHE`. |
| `NUM_THREADS` | Maximum local thread fan-out. |
| `NUM_PROCESSES` | Maximum process fan-out for cold time-series slices. |
| `TIMESERIES_PARALLEL_MODE` | Multi-slice execution mode; the current production example uses `processes`. |
| `POPULAR_REQUESTS_LIMIT` | Maximum hot request signatures selected for rebuild. |
| `REQUEST_POPULARITY_FLUSH_EVERY` | Event count that triggers popularity persistence. |
| `REQUEST_POPULARITY_FLUSH_INTERVAL` | Maximum persistence interval in seconds. |

Increasing workers can multiply memory and storage pressure. Benchmark with realistic NetCDF files and concurrent requests. Read [CACHE.md](CACHE.md) before changing TTL, cache-key, popularity, invalidation, or rebuild behavior.

## Database and external services

Set `SQLALCHEMY_DATABASE_URI` in the settings file or provide `DATABASE_URL`. Never commit real credentials. `DATABASE` names the MongoDB database used by place handlers. Other external integrations are configured in their service/metadata files; verify Signal K and Slurm connectivity only when those routes are enabled.

## Minimal local settings pattern

Start by copying the example and changing every filesystem path. A local override should include:

```python
BASE_DISKCACHE = "/absolute/writable/path/diskcache"
CACHE_JSON = "/absolute/writable/path/json"
BASE_PRODUCTS = "/absolute/writable/path/images"
BASE_SKEWT = "/absolute/writable/path/skewt"
LEGAL = "/absolute/repository/path/etc/legal.json"
MAPS = "/absolute/repository/path/etc/maps.json"
PAGES = "/absolute/repository/path/etc/pages.json"
VARS_CONTROL_PATH = "/absolute/repository/path/vars-control-file"
MEMCACHED_SERVER = "127.0.0.1:11211"
SQLALCHEMY_DATABASE_URI = "postgresql://user:password@127.0.0.1/database"
```

Retain the remaining URL, archive, TTL, and model settings from the example, adjusted for the local environment.

## Preflight checklist

- `APP_SETTINGS` resolves to a readable file.
- all metadata files parse as JSON
- archive and history roots are readable
- cache/output roots exist and are writable
- fallback image exists
- database hosts and memcached resolve from the runtime network
- public URLs match the reverse-proxy hostname
- secrets are injected outside version control
