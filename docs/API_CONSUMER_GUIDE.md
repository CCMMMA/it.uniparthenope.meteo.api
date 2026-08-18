# API v1 Consumer Migration and Authentication Guide

## Audience and contract

This guide is the external integration contract for application developers,
research groups, and institutional data consumers. API v1 is rooted at
`/api/v1`; a response from that contract carries `API-Version: 1`.

Product catalogue, metadata, maps, fields, outputs, and availability remain
public during adoption. Structured forecast and time-series resources require an
API key. Image, GRIB, place, and operational resources remain on their documented
legacy paths until functional v1 replacements are published.

## Obtaining and handling a key

Credential requests are currently reviewed out of band by the API operator.
Provide a responsible person's name and email, organization, research or service
purpose, required scopes, expected request volume, and intended retention of
meteorological data. There is deliberately no public issuance endpoint yet.

The operator returns a credential once. Store it in a secret manager or runtime
environment variable; never commit it, embed it in a mobile binary, place it in a
URL, or log it. Send it only over TLS:

```http
X-API-Key: meteo_<environment>_<public-id>.<secret>
```

Use `forecast:read` for structured forecasts and `timeseries:read` for JSON or
CSV time series. Missing and invalid keys return `401`; a valid key without the
required scope returns `403`. Clients should treat either response as a
configuration problem, not as a transient retry condition.

Browser and mobile packages cannot keep a shared secret. Public clients must use
a trusted backend or an operator-approved broker; CORS support does not make it
safe to expose an API key in JavaScript, an APK, or an application bundle.

## Endpoint migration

| Legacy | API v1 | Scope |
| --- | --- | --- |
| `/products/{prod}/forecast/{place}` | `/api/v1/products/{prod}/forecast/{place}` | `forecast:read` |
| `/products/{prod}/timeseries/{place}` | `/api/v1/products/{prod}/timeseries/{place}` | `timeseries:read` |
| `/products/{prod}/timeseries/{place}/csv` | `/api/v1/products/{prod}/timeseries/{place}/csv` | `timeseries:read` |

The v1 handlers use the same canonical caches, parameter normalization, payload
envelopes, and CSV serialization as their legacy equivalents. Migrate the URL and
add authentication while retaining the existing decoder. Validate status,
`Content-Type`, `API-Version`, and a representative payload in staging before
production rollout.

```python
import os
import requests

response = requests.get(
    "https://api.meteo.uniparthenope.it/api/v1/products/wrf5/forecast/com63049",
    headers={"X-API-Key": os.environ["METEO_API_KEY"]},
    timeout=10,
)
response.raise_for_status()
assert response.headers["API-Version"] == "1"
forecast = response.json()
```

## Deprecation interpretation

A legacy route is marked only after a functional v1 replacement and parity
coverage exist. Such responses contain `Deprecation: true` and a `Link` whose
relation is `successor-version`. A `Sunset` header appears only after an HTTP-date
has been formally approved and announced. `Deprecation` is a migration signal;
it is not itself a removal date.

Consumers should inventory calls by endpoint, migrate one resource family at a
time, compare results, deploy independently, and monitor `401`, `403`, and schema
decoding failures. Rotation creates a new credential and invalidates the previous
one immediately, so deployments must support atomic secret replacement.

## Privacy and support

Authenticated calls are attributed to the key identity, owner, and organization.
Telemetry records method, route template, API version, status, duration, and
time. It excludes the secret, query string, body, raw IP address, and user agent.
Usage supports capacity planning, abuse analysis, migration measurement, and
credential incident response. Contact the API operator to correct ownership,
rotate a suspected credential, revoke unused access, or request a telemetry
inquiry under the applicable institutional policy.
