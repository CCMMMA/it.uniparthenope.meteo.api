# API Testing Guide

## Purpose

This document explains how to run, understand, and evaluate the automated API tests for `it.uniparthenope.meteo.api`.

The repository uses the most standard Python approach for HTTP API unit testing:

- `pytest` as the test runner
- Flask's built-in test client for request execution
- dependency mocking to keep tests deterministic, fast, and independent from production services

Related documents:

- Main project overview: [../README.md](../README.md)
- Operations and development guide: [OPERATIONS_AND_USAGE.md](OPERATIONS_AND_USAGE.md)
- Endpoint reference: [API_ENDPOINTS.md](API_ENDPOINTS.md)
- Cache guide: [CACHE.md](CACHE.md)

## What Is Tested

The endpoint suite lives in:

- [../tests/test_api_endpoints.py](../tests/test_api_endpoints.py)
- [../tests/conftest.py](../tests/conftest.py)

The suite is aligned with the public Swagger surface exposed by:

- [https://api.meteo.uniparthenope.it/swagger.json](https://api.meteo.uniparthenope.it/swagger.json)

Coverage currently includes:

- JSON endpoints such as `version`, `legal`, `places`, `products`, `apps`, `instruments`, and `v2`
- binary endpoints such as plot images, legends, webcam responses, and static icons
- CSV export endpoints
- POST endpoints such as user login and `v2/pages/<page>`

The suite is designed to validate route registration, response codes, content types, and basic response structure for every public endpoint-method combination.

## Testing Philosophy

These tests are unit-style API tests, not full production integration tests.

That means:

- the Flask app is started in a test configuration
- external systems such as memcached, MongoDB, PostgreSQL, Signal K, Slurm, and large archive files are mocked
- the tests confirm that the route layer behaves correctly and consistently
- the tests do not prove that production infrastructure is healthy

This is intentional. The unit suite should be fast, repeatable, and safe to run on any development machine or CI environment.

## Step-By-Step Setup

### 1. Open the project directory

```bash
cd /path/to/it.uniparthenope.meteo.api
```

### 2. Create a Python virtual environment

```bash
python3 -m venv .venv
```

### 3. Activate the virtual environment

On Linux or macOS:

```bash
. .venv/bin/activate
```

### 4. Install the dependencies

```bash
pip install -r requirements.txt
```

This step is important because the tests rely on:

- `pytest`
- `Flask`
- `flask-restx`
- other packages imported at application startup

If `pytest` is missing, the command will fail with an error similar to:

```text
No module named pytest
```

### 5. Check that the test files exist

You should see:

- `tests/conftest.py`
- `tests/test_api_endpoints.py`
- `pytest.ini`

### 6. Run the complete endpoint unit-test suite

```bash
pytest
```

This is the standard command that future contributors and agents should use.

### 7. Run only the API endpoint suite if needed

```bash
pytest tests/test_api_endpoints.py
```

This is useful when you only want to validate public routes.

### 8. Run a single test group during focused debugging

Examples:

```bash
pytest tests/test_api_endpoints.py -k json_get_endpoints
pytest tests/test_api_endpoints.py -k binary_endpoints
pytest tests/test_api_endpoints.py -k products
```

This helps when working on one namespace or one response family at a time.

## How The Test Bootstrap Works

The file [../tests/conftest.py](../tests/conftest.py) performs the following steps automatically:

1. creates a temporary test configuration file
2. points `APP_SETTINGS` to that temporary configuration
3. imports the Flask application using safe temporary paths
4. enables Flask testing mode
5. provides a Flask test client fixture

The test configuration avoids production dependencies by using temporary directories for:

- disk cache
- archive paths
- generated JSON
- skew-T output
- fallback image paths

## How Mocking Works

The endpoint suite replaces real service integrations with deterministic fake implementations.

This includes:

- `MeteoServices`
- `GribServices`
- `Tiles`
- `Places`
- `CMS`
- `LoginServices`
- `SlurmServices`
- cache handlers

The goal is to evaluate API behavior without requiring:

- real meteorological archives
- MongoDB access
- memcached access
- PostgreSQL access
- remote HTTP services
- Slurm connectivity

## How To Evaluate The Results

### A passing run

A successful run usually ends with output similar to:

```text
==================== 57 passed in 1.23s ====================
```

Interpretation:

- all public endpoint-method combinations tested by the suite behaved as expected
- route registration is intact
- content types and basic payload structure are stable
- no mocked dependency contract was broken by the recent changes

### A failing run

If the run fails, first identify which test category failed.

Common categories:

- `test_json_get_endpoints`
- `test_binary_endpoints`
- `test_post_endpoints`
- `test_grib_text_endpoint`
- `test_timeseries_csv_endpoint`

Interpretation guide:

- JSON endpoint failure: likely response structure, status code, or namespace routing changed
- binary endpoint failure: likely wrong MIME type, image payload path, or response construction
- POST endpoint failure: likely payload parsing, auth handling, or route registration changed
- GRIB text or CSV failure: likely response formatter or export behavior changed

### What to inspect when a test fails

1. Read the failing endpoint path shown by `pytest`.
2. Compare the actual response with the expected response in [../tests/test_api_endpoints.py](../tests/test_api_endpoints.py).
3. Check the corresponding handler under [../apis/](../apis).
4. Decide whether the code is wrong or the test expectation should be updated.
5. If the endpoint contract intentionally changed, update:
   - the tests
   - Swagger-visible documentation
   - [API_ENDPOINTS.md](API_ENDPOINTS.md)
   - [../README.md](../README.md) if the change affects top-level usage

## When A Test Failure Is Good

Sometimes a failure is useful.

Examples:

- you intentionally changed a response shape
- you removed a field from an endpoint
- you changed a MIME type from JSON to PNG
- you introduced a new validation rule for POST payloads

In those situations, the failure is telling you that public behavior changed. That is exactly what the suite is supposed to reveal.

## What The Unit Tests Do Not Replace

Even when `pytest` passes, you should still perform additional validation when changes are significant.

Recommended extra checks:

- open the Swagger UI at `/`
- manually try a lightweight endpoint such as `/version`
- manually inspect one `places` endpoint
- manually inspect one `products` endpoint
- validate cache behavior when changing memcache or disk-cache logic
- perform staging checks for endpoints that depend on real archives or external services

Use this suite as the first safety net, not the only validation step.

## Recommended Developer Workflow

For API changes, the safest workflow is:

1. edit the code
2. run syntax validation

```bash
python3 -m py_compile app.py tests/conftest.py tests/test_api_endpoints.py
```

3. run the endpoint tests

```bash
pytest
```

4. fix any failures
5. update documentation if the public contract changed
6. commit only after the suite is passing

## CI / Automation Recommendation

If this repository is connected to a CI system, the recommended minimal automated check is:

```bash
pytest
```

If a future CI pipeline is added, this command should be part of the default validation job for pull requests and branch updates.

## Maintenance Rules

When adding or changing endpoints:

- add or update a test in [../tests/test_api_endpoints.py](../tests/test_api_endpoints.py)
- keep the route inventory consistent with the live Swagger interface
- keep response assertions simple but meaningful
- prefer deterministic mocked responses over fragile external dependencies

When changing the testing workflow itself:

- update this document
- update [../AGENTS.md](../AGENTS.md) if the repository rule changes
- update [../requirements.txt](../requirements.txt) if new testing packages are added
