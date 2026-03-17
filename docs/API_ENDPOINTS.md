# API Endpoint Catalog

## Overview

The API is organized into the following namespaces:

- `users`
- `apps`
- `box`
- `legal`
- `places`
- `products`
- `v2`
- `version`
- `webcam`
- `instruments`

## Endpoint Groups

### users

- `POST /users/login`: authenticate a user through the legacy login flow.

### apps

- `GET /apps/owm/<prod>/<placeprefix>/<z>/<x>/<y>.geojson`: application-oriented OWM-like weather tile payload.
- `GET /apps/sais/index`: SAIS application index payload.

### box

- `GET /box/today/<place>`: retrieve box/today content for a place code.

### legal

- `GET /legal/disclaimer`: legal disclaimer content.
- `GET /legal/privacy`: privacy content.

### places

- `GET /places`: retrieve the full place collection.
- `GET /places/search/byname/<name>`: search places by name.
- `GET /places/search/byname/autocomplete`: autocomplete lookup by the `term` query parameter.
- `GET /places/<identifier>`: resolve a place by identifier.
- `GET /places/search/bycoords/<latitude>/<longitude>`: locate nearby places.
- `GET /places/search/byboundingbox/<minLatitude>/<minLongitude>/<maxLatitude>/<maxLongitude>`: list places inside a bounding box.

### products

- `GET /products`: list products.
- `GET /products/<prod>`: retrieve product metadata.
- `GET /products/<prod>/outputs`: list outputs for a product.
- `GET /products/<prod>/fields`: list fields for a product.
- `GET /products/maps`: retrieve maps metadata.
- `GET /products/<prod>/maps/themes`: retrieve themes for a product.
- `GET /products/<prod>/<place>/avail`: get availability summary.
- `GET /products/<prod>/<place>/avail/calendar`: get availability calendar.
- `GET /products/<prod>/forecast/<place>`: structured forecast output.
- `GET /products/<prod>/forecast/<place>/plot/image`: rendered forecast image.
- `GET /products/wrf5/forecast/plot/SkewT/image`: Skew-T image.
- `GET /products/<prod>/forecast/<place>/plot/alt`: alternative/alt-text payload for plots.
- `GET /products/<prod>/forecast/<domain>/grib/text`: text export for GRIB-oriented data.
- `GET /products/<prod>/forecast/<domain>/grib/json`: JSON export for GRIB-oriented data.
- `GET /products/<prod>/forecast/<place>/plot`: plot link or image payload.
- `GET /products/<prod>/forecast/legend/<position>/<output>`: legend image.
- `GET /products/<prod>/forecast/legend/<position>/<output>/ncwms`: legend image from ncWMS-oriented path.
- `GET /products/<prod>/plot/<output>/metacharts`: plotting metadata.
- `GET /products/<prod>/timeseries/<place>`: timeseries JSON.
- `GET /products/<prod>/timeseries/<place>/csv`: timeseries CSV.
- `GET /products/<prod>/forecast/<place>/map/image`: legacy map image endpoint.
- `GET /products/resource/forecast/<icon>`: static icon asset.

### v2

- `GET /v2/weatherreports/latest/json`
- `GET /v2/weatherreports/latest/<field>/json`
- `GET /v2/weatherreports/json`
- `GET /v2/slurm/storage`
- `GET /v2/slurm/info`
- `GET /v2/slurm/queue`
- `GET /v2/carousel`
- `GET /v2/cards`
- `GET /v2/basemaps`
- `GET /v2/basemaps/<name>`
- `GET /v2/layers`
- `GET /v2/layers/<name>`
- `GET /v2/maps`
- `GET /v2/maps/<name>`
- `GET /v2/navbar`
- `GET /v2/pages`
- `GET /v2/pages/<page>`
- `POST /v2/pages/<page>`
- `GET /v2/auth/login`

### version

- `GET /version`

### webcam

- `GET /webcam/<place>/<location>/<cam>`

### instruments

- `GET /instruments`
- `GET /instruments/<identification>`

## Notes

- Query parameters are handled dynamically by the route implementations, especially in `products`, `places`, and `v2`.
- Some endpoints return JSON, while others return PNG or CSV content.
- A number of routes depend on external data availability and may return fallback or error payloads if storage is unavailable.
- The Swagger UI should be treated as the primary interactive contract for parameters and examples after the code-level documentation updates.
