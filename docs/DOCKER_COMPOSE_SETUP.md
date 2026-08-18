# Docker Compose setup

This guide runs the meteorological API behind nginx with MongoDB, PostgreSQL,
and memcached on one private Docker Compose network. It is suitable for local
integration and as a starting point for a single-host deployment. Production
secrets, TLS, backups, monitoring, and externally managed data volumes still
need to be supplied by the operator.

## 1. Install the prerequisites

Install Docker Engine with the Compose plugin, then verify both commands:

```bash
docker --version
docker compose version
```

Clone the repository, check out `main`, and run the remaining commands from the
repository root.

The Dockerfile uses the legacy Python 3.8 image and pinned scientific packages.
On an ARM workstation, the native build may fail where those dependencies have
no compatible wheel; in that case build and run the stack with
`DOCKER_DEFAULT_PLATFORM=linux/amd64` so Docker uses emulation.

## 2. Prepare host directories and datasets

The image runs as UID and GID `60005`. Create its writable bind mounts before
starting Compose:

```bash
mkdir -p runtime/images runtime/skewt runtime/json runtime/diskcache runtime/prods
sudo chown -R 60005:60005 runtime
```

Two external dataset trees are also required for forecast, plot, time-series,
and GRIB endpoints:

- the forecast/archive tree mounted at `/data1/ccmmma/prometeo/data/opendap`
- the history/storage tree mounted at `/storage/ccmmma/prometeo/data/opendap`

They can be omitted only for a metadata-only development instance. If they are
mounted, keep them read-only. The directory hierarchy must match the paths
expected by `core/MakeArchivePaths.py`; Compose does not download meteorological
datasets.

Provide the fallback image expected by the committed configuration:

```bash
cp /absolute/path/to/a/fallback.png runtime/images/noimage.png
```

The repository does not include this deployment asset; use a valid PNG for
`runtime/images/noimage.png`.

## 3. Create an environment file

Create an untracked `.env` file beside `compose.yaml`:

```dotenv
POSTGRES_DB=cnmost
POSTGRES_USER=meteo
POSTGRES_PASSWORD=replace-with-a-long-random-password
FORECAST_ARCHIVE=/absolute/host/path/to/forecast/opendap
HISTORY_ARCHIVE=/absolute/host/path/to/history/opendap
PUBLIC_PORT=8080
```

Do not commit this file. `FORECAST_ARCHIVE` and `HISTORY_ARCHIVE` must be
absolute host paths shared with Docker Desktop where applicable.

The example application configuration already uses the Compose DNS names
`memcached` and `postgres`. MongoDB access is currently hard-coded to
`mongodb://db:27017/`, so the MongoDB service must retain the name `db` unless
the application code is changed.

## 4. Create `compose.yaml`

Add this file at the repository root:

```yaml
name: meteo-api

services:
  nginx:
    image: nginx:1.27-alpine
    ports:
      - "${PUBLIC_PORT:-8080}:80"
    volumes:
      - ./deploy/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./runtime/images:/srv/images:ro
    depends_on:
      api:
        condition: service_healthy
    restart: unless-stopped

  api:
    build:
      context: .
    image: it-uniparthenope-meteo-api:local
    command:
      - uwsgi
      - --module
      - wsgi
      - --http
      - :5000
      - --master
      - --processes
      - "4"
      - --enable-threads
      - --die-on-term
      - --single-interpreter
      - --socket-timeout
      - "300"
      - --http-timeout
      - "300"
      - --harakiri
      - "300"
    environment:
      APP_SETTINGS: /project/etc/ccmmmaapi.conf
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
    volumes:
      - ./etc:/project/etc:ro
      - ./vars-control-file:/project/vars-control-file:ro
      - ./runtime/images:/project/images
      - ./runtime/skewt:/project/skewt
      - ./runtime/json:/project/json
      - ./runtime/diskcache:/project/diskcache
      - ./runtime/prods:/project/var/prods
      - ${FORECAST_ARCHIVE}:/data1/ccmmma/prometeo/data/opendap:ro
      - ${HISTORY_ARCHIVE}:/storage/ccmmma/prometeo/data/opendap:ro
    depends_on:
      postgres:
        condition: service_healthy
      db:
        condition: service_started
      memcached:
        condition: service_started
    healthcheck:
      test:
        - CMD
        - python
        - -c
        - "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/version/', timeout=5)"
      interval: 15s
      timeout: 8s
      retries: 10
      start_period: 60s
    restart: unless-stopped

  db:
    image: mongo:7
    volumes:
      - mongodb_data:/data/db
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 5s
      timeout: 5s
      retries: 12
    restart: unless-stopped

  memcached:
    image: memcached:1.6-alpine
    command: ["memcached", "-m", "256", "-I", "8m"]
    restart: unless-stopped

volumes:
  mongodb_data:
  postgres_data:
```

The API command deliberately logs to container stdout/stderr instead of using
the file-log paths in `ccmmmaapi.ini`. Start with four uWSGI workers and tune
only after measuring RAM consumption with representative NetCDF requests.

For a metadata-only instance, remove the two archive volume entries and set the
corresponding paths in a copied configuration file to existing empty read-only
directories. Data-dependent endpoints will still fail or return no product.

## 5. Configure nginx

Create `deploy/nginx.conf`:

```nginx
upstream meteo_api {
    server api:5000;
    keepalive 16;
}

server {
    listen 80;
    server_name _;

    client_max_body_size 32m;

    location /images/ {
        alias /srv/images/;
        try_files $uri =404;
        expires 10m;
    }

    location / {
        proxy_pass http://meteo_api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 10s;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

This configuration speaks HTTP to uWSGI because `ccmmmaapi.ini` and the Compose
override expose an HTTP listener on port 5000; do not use `uwsgi_pass` with it.
Only nginx publishes a host port. MongoDB, PostgreSQL, memcached, and the API
remain reachable only on the private Compose network.

For public production traffic, terminate TLS at nginx or at an ingress/load
balancer in front of it and replace the public URL values in an
environment-specific copy of `etc/ccmmmaapi.conf`.

## 6. Validate and start the stack

Render the fully substituted Compose model before building. This catches unset
paths and YAML errors without starting containers:

```bash
docker compose config
docker compose build api
docker compose up -d
docker compose ps
```

Follow startup logs if the API does not become healthy:

```bash
docker compose logs -f api nginx postgres db memcached
```

## 7. Apply the PostgreSQL schema

PostgreSQL stores API-key and usage data. Apply each checked-in migration once
after the database is healthy:

```bash
docker compose exec -T postgres psql \
  -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 \
  < migrations/001_api_keys.sql

docker compose exec -T postgres psql \
  -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 \
  < migrations/002_api_usage_events.sql
```

Variables from `.env` are used by Compose for interpolation but are not
automatically exported into the invoking shell. If the two shell variables are
empty, run `set -a; . ./.env; set +a` first, or replace them explicitly in the
commands.

## 8. Load MongoDB place data

An empty MongoDB is enough for the API process to start, but place searches need
the deployment's `places` collection. The repository does not ship the
production place dataset. Given a newline-delimited JSON export named
`places.json`, import it with:

```bash
docker compose cp places.json db:/tmp/places.json
docker compose exec db mongoimport \
  --db ccmmma-database --collection places \
  --file /tmp/places.json --drop
```

Omit `--drop` when existing records must be preserved. For a BSON backup use
`mongorestore` instead and select the `ccmmma-database` database. Back up the
named `mongodb_data` volume before replacing production data.

## 9. Smoke-test through nginx

Open Swagger at `http://localhost:8080/`, then test low-dependency routes:

```bash
curl --fail http://localhost:8080/version/
curl --fail http://localhost:8080/legal/disclaimer
curl --fail http://localhost:8080/products
```

Next test one place query after importing MongoDB data and one forecast or
time-series request after mounting the archives. Swagger and metadata can work
even when the external datasets are absent, so they are not sufficient proof of
a complete deployment.

Inspect container and resource state when a check fails:

```bash
docker compose ps
docker compose logs --tail=200 api nginx
docker compose exec api python -m compileall -q app.py wsgi.py apis core
```

## 10. Operate, upgrade, and stop

Rebuild and replace only the application after a code update:

```bash
docker compose build api
docker compose up -d --no-deps api
docker compose up -d nginx
```

Stop containers without deleting database volumes:

```bash
docker compose down
```

`docker compose down --volumes` deletes the Compose-managed MongoDB and
PostgreSQL data. Do not use it unless those databases have been backed up and
their removal is intentional. The `runtime/` bind mounts and external archive
trees are not removed by `docker compose down`.

In production, also configure database and volume backups, log collection,
health monitoring, certificate renewal, image pinning, and resource limits.
Review [PRODUCTION_SETUP.md](PRODUCTION_SETUP.md) and [CACHE.md](CACHE.md) before
rollout or cache maintenance.
