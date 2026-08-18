# Migrating Clients to API Version 1

## Purpose and scope

API version 1 provides a governed contract under `/api/v1`. Migration is
incremental: a resource family becomes canonical only after its v1 endpoints,
legacy parity tests, endpoint reference, compatibility matrix, and client
examples are published together.

The first operational family covers product discovery, product metadata, and
availability. Forecast, time-series, image, GRIB, place, and operational routes
remain on their documented legacy paths until equivalent v1 contracts are
released.

## Compatibility model

The initial v1 product endpoints are additive aliases at the contract level.
They call the same application-owned meteorological service and intentionally
preserve the legacy JSON response schemas. They do not issue redirects, because
redirects can alter cache behavior, client authorization forwarding, and error
handling.

Every v1 response includes:

```http
API-Version: 1
```

Legacy responses do not receive this header and remain unchanged.

## Product endpoint mapping

| Legacy request | Canonical v1 request |
| --- | --- |
| `/products` | `/api/v1/products` |
| `/products/maps` | `/api/v1/products/maps` |
| `/products/{prod}/maps/themes` | `/api/v1/products/{prod}/maps/themes` |
| `/products/{prod}` | `/api/v1/products/{prod}` |
| `/products/{prod}/outputs` | `/api/v1/products/{prod}/outputs` |
| `/products/{prod}/fields` | `/api/v1/products/{prod}/fields` |
| `/products/{prod}/{place}/avail` | `/api/v1/products/{prod}/{place}/availability` |
| `/products/{prod}/{place}/avail/calendar` | `/api/v1/products/{prod}/{place}/availability/calendar` |

## Safe migration procedure

1. Change only the base path and the documented `avail` → `availability`
   spelling where applicable.
2. Keep the existing response decoder; v1 currently preserves the legacy
   envelope for this family.
3. Verify the HTTP status and `API-Version` header in pre-production.
4. Compare representative legacy and v1 JSON payloads using the same query
   parameters.
5. Deploy the client change independently of any future legacy deprecation.

Example:

```python
legacy = requests.get(f"{base_url}/products/wrf5/outputs", timeout=10)
versioned = requests.get(f"{base_url}/api/v1/products/wrf5/outputs", timeout=10)

legacy.raise_for_status()
versioned.raise_for_status()
assert versioned.headers["API-Version"] == "1"
assert versioned.json() == legacy.json()
```

## Deprecation boundary

Publication of a v1 equivalent does not by itself deprecate its legacy route.
Legacy deprecation begins only after a separate policy release defines notice,
telemetry, migration support, and sunset dates. Clients should migrate early,
but must not infer a removal date that has not been explicitly announced.
