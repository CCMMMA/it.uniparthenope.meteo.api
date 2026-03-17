# API Endpoint Manual

## How To Read This Document

This document describes the active HTTP endpoints exposed by `it.uniparthenope.meteo.api`.

For each endpoint you will find:

- what the endpoint is for
- the HTTP method and path
- the most important parameters
- the typical response format
- one or more easy-to-use examples

Swagger UI is exposed at the API root path `/`, but this file is intended to be the deeper written reference.

Related documents:

- Operational guide: [OPERATIONS_AND_USAGE.md](OPERATIONS_AND_USAGE.md)
- Production setup guide: [PRODUCTION_SETUP.md](PRODUCTION_SETUP.md)
- Python tutorial: [PYTHON_API_TUTORIAL.md](PYTHON_API_TUTORIAL.md)
- Android tutorial: [ANDROID_KOTLIN_API_TUTORIAL.md](ANDROID_KOTLIN_API_TUTORIAL.md)
- iOS tutorial: [IOS_SWIFT_API_TUTORIAL.md](IOS_SWIFT_API_TUTORIAL.md)

## Common Notes

- Base URL examples are written as relative paths such as `/products/...`.
- Many endpoints also accept query parameters parsed dynamically by the application.
- Some endpoints return JSON, while others return PNG images or CSV text.
- Several data-heavy endpoints depend on archive files, caches, and external services being available.

## 1. `version`

### `GET /version`

Purpose:

- Returns the deployed API version and environment name.

Typical response:

- JSON object with `version` and `environment`.

Example:

```http
GET /version
```

## 2. `legal`

### `GET /legal/disclaimer`

Purpose:

- Returns the legal disclaimer content shown by clients.

Typical response:

- JSON payload containing disclaimer text or structured legal content.

Example:

```http
GET /legal/disclaimer
```

### `GET /legal/privacy`

Purpose:

- Returns privacy information used by the platform.

Typical response:

- JSON payload containing privacy text or structured privacy content.

Example:

```http
GET /legal/privacy
```

## 3. `users`

### `POST /users/login`

Purpose:

- Authenticates a user through the legacy login flow.

Request body:

- `name`: username
- `pass`: password

Typical response:

- JSON payload containing user information, roles, or authentication status.

Example:

```http
POST /users/login
Content-Type: application/json

{
  "name": "student",
  "pass": "secret"
}
```

## 4. `instruments`

### `GET /instruments`

Purpose:

- Lists the instruments retrieved from the upstream Signal K integration.

Typical response:

- JSON object keyed by station or instrument identifier.

Example:

```http
GET /instruments
```

### `GET /instruments/<identification>`

Purpose:

- Returns a single instrument payload by identifier.

Path parameter:

- `identification`: instrument id such as a station code.

Example:

```http
GET /instruments/station-01
```

## 5. `webcam`

### `GET /webcam/<place>/<location>/<cam>`

Purpose:

- Returns the latest webcam image for the selected place, location, and camera.

Path parameters:

- `place`: place code
- `location`: webcam location folder
- `cam`: webcam name without extension

Response:

- JPEG image

Example:

```http
GET /webcam/com63049/castelsantelmo/nord
```

## 6. `box`

### `GET /box/today/<place>`

Purpose:

- Returns the current “box” content for a place.

Path parameter:

- `place`: place identifier

Example:

```http
GET /box/today/com63049
```

## 7. `places`

### `GET /places`

Purpose:

- Returns the complete places collection.

Typical response:

- JSON array of place objects.

Example:

```http
GET /places
```

### `GET /places/search/byname/<name>`

Purpose:

- Searches places by free-text name.

Path parameter:

- `name`: search term, for example `Napoli`

Typical response:

- JSON array of matching places.

Example:

```http
GET /places/search/byname/Napoli
```

### `GET /places/search/byname/autocomplete`

Purpose:

- Returns compact autocomplete suggestions for search boxes.

Query parameters:

- `term`: the search prefix typed by the user

Typical response:

- JSON array of objects containing at least `label` and `id`.

Example:

```http
GET /places/search/byname/autocomplete?term=nap
```

### `GET /places/<identifier>`

Purpose:

- Returns a single place by its canonical id.

Path parameter:

- `identifier`: place code such as `com63049`

Example:

```http
GET /places/com63049
```

### `GET /places/search/bycoords/<latitude>/<longitude>`

Purpose:

- Finds places near the given coordinates.

Path parameters:

- `latitude`: decimal latitude
- `longitude`: decimal longitude

Typical response:

- JSON array of nearby places.

Example:

```http
GET /places/search/bycoords/40.78783/14.352
```

### `GET /places/search/byboundingbox/<minLatitude>/<minLongitude>/<maxLatitude>/<maxLongitude>`

Purpose:

- Lists places contained inside a geographic bounding box.

Path parameters:

- `minLatitude`: south boundary
- `minLongitude`: west boundary
- `maxLatitude`: north boundary
- `maxLongitude`: east boundary

Typical response:

- JSON array of places inside the bounding box.

Example:

```http
GET /places/search/byboundingbox/40.78/14.35/41.22/16.87
```

## 8. `apps`

### `GET /apps/owm/<prod>/<placeprefix>/<z>/<x>/<y>.geojson`

Purpose:

- Returns application tile data in a GeoJSON-like structure for a given forecast product.

Path parameters:

- `prod`: product code such as `wrf5`
- `placeprefix`: prefix used to filter the dataset, such as `prov`
- `z`, `x`, `y`: tile coordinates

Typical response:

- JSON or GeoJSON-like payload representing weather features for the requested tile.

Example:

```http
GET /apps/owm/wrf5/prov/10/552/384.geojson
```

### `GET /apps/sais/index`

Purpose:

- Returns SAIS application data loaded from a JSON source file.

Typical response:

- JSON object with a `sam3` key.

Example:

```http
GET /apps/sais/index
```

## 9. `products`

### `GET /products`

Purpose:

- Lists all forecast products known to the API.

Typical response:

- JSON object with a `products` field.

Example:

```http
GET /products
```

### `GET /products/<prod>`

Purpose:

- Returns the metadata block for one product.

Path parameter:

- `prod`: product code, for example `wrf5`

Example:

```http
GET /products/wrf5
```

### `GET /products/<prod>/outputs`

Purpose:

- Lists the outputs available for a product.

Example:

```http
GET /products/wrf5/outputs
```

### `GET /products/<prod>/fields`

Purpose:

- Lists the fields available for a product.

Example:

```http
GET /products/wrf5/fields
```

### `GET /products/maps`

Purpose:

- Returns map metadata used by forecast visualizations.

Example:

```http
GET /products/maps
```

### `GET /products/<prod>/maps/themes`

Purpose:

- Returns theme definitions for a selected product.

Example:

```http
GET /products/wrf5/maps/themes
```

### `GET /products/<prod>/<place>/avail`

Purpose:

- Returns a summary of product availability for a place.

Example:

```http
GET /products/rdr1/ca001/avail
```

### `GET /products/<prod>/<place>/avail/calendar`

Purpose:

- Returns the same availability idea in a calendar-oriented format.

Example:

```http
GET /products/rdr1/ca001/avail/calendar
```

### `GET /products/<prod>/forecast/<place>`

Purpose:

- Returns the main forecast payload for a product and place.

Path parameters:

- `prod`: product code such as `wrf5`, `ww33`, `rdr1`
- `place`: place identifier

Typical response:

- JSON object with forecast data, metadata, fields, and possibly place information.

Examples:

```http
GET /products/wrf5/forecast/com63049
```

```http
GET /products/ww33/forecast/ca001?date=20250317Z1200
```

### `GET /products/<prod>/forecast/<place>/plot/image`

Purpose:

- Returns a rendered PNG plot for a place.

Response:

- PNG image

Examples:

```http
GET /products/ww33/forecast/ca001/plot/image
```

```http
GET /products/wrf5/forecast/com63049/plot/image?date=20250317Z1200
```

### `GET /products/wrf5/forecast/plot/SkewT/image`

Purpose:

- Returns a Skew-T meteorological diagram as a PNG image.

Typical use:

- atmospheric profile diagnostics
- teaching and advanced meteorological analysis

Examples:

```http
GET /products/wrf5/forecast/plot/SkewT/image
```

```http
GET /products/wrf5/forecast/plot/SkewT/image?date=20250915Z1000
```

### `GET /products/<prod>/forecast/<place>/plot/alt`

Purpose:

- Returns alternative descriptive data for a forecast plot.

Typical response:

- JSON or structured text payload useful for accessibility or compact summaries.

Example:

```http
GET /products/wrf5/forecast/com63049/plot/alt
```

### `GET /products/<prod>/forecast/<domain>/grib/text`

Purpose:

- Returns a text export derived from the GRIB/NetCDF product data.

Path parameters:

- `prod`: product code
- `domain`: domain code such as `d01` or `d02`

Example:

```http
GET /products/wrf5/forecast/d02/grib/text
```

### `GET /products/<prod>/forecast/<domain>/grib/json`

Purpose:

- Returns a JSON export derived from the same GRIB-oriented data source.

Example:

```http
GET /products/wrf5/forecast/d02/grib/json
```

### `GET /products/<prod>/forecast/<place>/plot`

Purpose:

- Returns plot metadata, and optionally inline binary image content depending on query parameters.

Typical response:

- JSON with map links, image names, and optional forecast fields
- or a PNG response if `dry=false`

Examples:

```http
GET /products/ww33/forecast/ca001/plot
```

```http
GET /products/ww33/forecast/ca001/plot?dry=false
```

### `GET /products/<prod>/forecast/legend/<position>/<output>`

Purpose:

- Returns a legend image for a specific output field.

Path parameters:

- `position`: legend position such as `left`, `right`, `top`, `bottom`
- `output`: output code

Example:

```http
GET /products/ww33/forecast/legend/right/waveheight
```

### `GET /products/<prod>/forecast/legend/<position>/<output>/ncwms`

Purpose:

- Returns the legend image using the ncWMS-oriented generation path.

Example:

```http
GET /products/ww33/forecast/legend/right/waveheight/ncwms
```

### `GET /products/<prod>/plot/<output>/metacharts`

Purpose:

- Returns plotting metadata used by frontend chart systems.

Example:

```http
GET /products/wrf5/plot/gen/metacharts
```

### `GET /products/<prod>/timeseries/<place>`

Purpose:

- Returns a time-series payload for a product and place.

Typical response:

- JSON object containing time steps, fields, and values.

Example:

```http
GET /products/ww33/timeseries/ca001
```

### `GET /products/<prod>/timeseries/<place>/csv`

Purpose:

- Returns the same time-series information as CSV.

Response:

- `text/csv`

Example:

```http
GET /products/wrf5/timeseries/ca001/csv
```

### `GET /products/<prod>/forecast/<place>/map/image`

Purpose:

- Legacy image endpoint kept for older clients.

Response:

- PNG image

Example:

```http
GET /products/ww33/forecast/ca001/map/image
```

### `GET /products/resource/forecast/<icon>`

Purpose:

- Returns one of the static icon images bundled with the API.

Example:

```http
GET /products/resource/forecast/sunny.png
```

## 10. `v2`

### `GET /v2/weatherreports/latest/json`

Purpose:

- Returns the latest weather report.

Example:

```http
GET /v2/weatherreports/latest/json
```

### `GET /v2/weatherreports/latest/<field>/json`

Purpose:

- Returns one field from the latest weather report.

Example:

```http
GET /v2/weatherreports/latest/title/json
```

### `GET /v2/weatherreports/json`

Purpose:

- Returns the collection of weather reports.

Example:

```http
GET /v2/weatherreports/json
```

### `GET /v2/slurm/storage`

Purpose:

- Returns storage-related information from the Slurm environment.

Example:

```http
GET /v2/slurm/storage
```

### `GET /v2/slurm/info`

Purpose:

- Returns general Slurm cluster information.

Example:

```http
GET /v2/slurm/info
```

### `GET /v2/slurm/queue`

Purpose:

- Returns the Slurm job queue snapshot.

Example:

```http
GET /v2/slurm/queue
```

### `GET /v2/carousel`

Purpose:

- Returns CMS carousel items, typically filtered by authenticated roles.

Authentication:

- Bearer token recommended

Example:

```http
GET /v2/carousel
Authorization: Bearer <token>
```

### `GET /v2/cards`

Purpose:

- Returns CMS card items.

Example:

```http
GET /v2/cards
Authorization: Bearer <token>
```

### `GET /v2/basemaps`

Purpose:

- Lists all basemap definitions.

Example:

```http
GET /v2/basemaps
```

### `GET /v2/basemaps/<name>`

Purpose:

- Returns one basemap definition.

Example:

```http
GET /v2/basemaps/osm
```

### `GET /v2/layers`

Purpose:

- Lists available layer definitions.

Example:

```http
GET /v2/layers
```

### `GET /v2/layers/<name>`

Purpose:

- Returns one layer definition by name.

Example:

```http
GET /v2/layers/info
```

### `GET /v2/maps`

Purpose:

- Lists available high-level map definitions.

Example:

```http
GET /v2/maps
```

### `GET /v2/maps/<name>`

Purpose:

- Returns one map definition by name.

Example:

```http
GET /v2/maps/weather
```

### `GET /v2/navbar`

Purpose:

- Returns navbar content used by the frontend.

Example:

```http
GET /v2/navbar
Authorization: Bearer <token>
```

### `GET /v2/pages`

Purpose:

- Lists CMS pages available to the caller.

Example:

```http
GET /v2/pages
Authorization: Bearer <token>
```

### `GET /v2/pages/<page>`

Purpose:

- Returns one CMS page by page id.

Example:

```http
GET /v2/pages/about_us
Authorization: Bearer <token>
```

### `POST /v2/pages/<page>`

Purpose:

- Creates or updates a CMS page.

Authentication:

- Bearer token expected

Example:

```http
POST /v2/pages/about_us
Authorization: Bearer <token>
Content-Type: application/json

{
  "_id": "about_us",
  "author": "teacher01"
}
```

### `GET /v2/auth/login`

Purpose:

- Resolves authentication information from the bearer token sent in the request header.

Example:

```http
GET /v2/auth/login
Authorization: Bearer <token>
```

## Practical First Calls

If you are trying the API for the first time, a good order is:

1. `GET /version`
2. `GET /legal/disclaimer`
3. `GET /places/search/byname/Napoli`
4. `GET /products`
5. `GET /products/wrf5`
6. `GET /products/wrf5/forecast/com63049`
7. `GET /products/wrf5/timeseries/com63049`

## Related Documentation

- [OPERATIONS_AND_USAGE.md](OPERATIONS_AND_USAGE.md)
- [PRODUCTION_SETUP.md](PRODUCTION_SETUP.md)
- [PYTHON_API_TUTORIAL.md](PYTHON_API_TUTORIAL.md)
