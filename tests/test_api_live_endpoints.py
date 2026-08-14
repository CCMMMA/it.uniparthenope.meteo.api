"""Optional live API checks against one or two deployed base URLs."""

from __future__ import annotations

import hashlib
import json
import time

import pytest
import requests

from tests.api_cases import IMAGE_CASES, JSON_GET_CASES


def _require_live_base_url(live_base_url: str | None):
    """Skip the test module when no live target was requested."""
    if not live_base_url:
        pytest.skip("set --live-base-url to run the live API checks")


def _full_url(base_url: str, path: str) -> str:
    """Join a base URL and endpoint path."""
    return f"{base_url}{path}"


def _content_type(response: requests.Response) -> str:
    """Return the MIME type without charset suffixes."""
    return response.headers.get("Content-Type", "").split(";", 1)[0]


def _json_payload(response: requests.Response):
    """Decode a JSON response for comparison and diagnostics."""
    return response.json()


def _binary_digest(body: bytes) -> str:
    """Return a stable digest for binary response comparison."""
    return hashlib.sha256(body).hexdigest()


def _request(session, method, url, timeout, headers=None, json_body=None):
    """Perform one timed HTTP request."""
    started = time.perf_counter()
    response = session.request(method, url, timeout=timeout, headers=headers or {}, json=json_body)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return response, elapsed_ms


def _compare_json_payloads(path, primary, secondary):
    """Assert that two JSON payloads are identical."""
    assert primary == secondary, (
        f"JSON payload mismatch for {path}\n"
        f"primary={json.dumps(primary, indent=2, sort_keys=True, ensure_ascii=True)}\n"
        f"secondary={json.dumps(secondary, indent=2, sort_keys=True, ensure_ascii=True)}"
    )


def _compare_binary_payloads(path, primary, secondary):
    """Assert that two binary payloads are identical."""
    primary_digest = _binary_digest(primary)
    secondary_digest = _binary_digest(secondary)
    assert primary_digest == secondary_digest, (
        f"Binary payload mismatch for {path}: "
        f"primary_sha256={primary_digest} secondary_sha256={secondary_digest}"
    )


@pytest.fixture(scope="module")
def live_session():
    """Return a requests session for live endpoint checks."""
    with requests.Session() as session:
        yield session


def test_live_grib_text_endpoint(live_base_url, compare_base_url, live_timeout, live_session, invocation_recorder):
    """Ensure the text-oriented GRIB export endpoint responds on live targets."""
    _require_live_base_url(live_base_url)
    path = "/products/wrf5/forecast/d02/grib/text"

    primary_response, primary_elapsed = _request(live_session, "GET", _full_url(live_base_url, path), live_timeout)
    invocation_recorder("GET", "live-primary", _full_url(live_base_url, path), primary_elapsed, primary_response.status_code)

    assert primary_response.status_code == 200
    assert _content_type(primary_response) == "text/plain"

    if compare_base_url:
        secondary_response, secondary_elapsed = _request(live_session, "GET", _full_url(compare_base_url, path), live_timeout)
        invocation_recorder("GET", "live-compare", _full_url(compare_base_url, path), secondary_elapsed, secondary_response.status_code)
        assert secondary_response.status_code == 200
        assert _content_type(secondary_response) == "text/plain"
        assert primary_response.text == secondary_response.text


def test_live_timeseries_csv_endpoint(live_base_url, compare_base_url, live_timeout, live_session, invocation_recorder):
    """Ensure the CSV time-series endpoint responds on live targets."""
    _require_live_base_url(live_base_url)
    path = "/products/wrf5/timeseries/com63049/csv"

    primary_response, primary_elapsed = _request(live_session, "GET", _full_url(live_base_url, path), live_timeout)
    invocation_recorder("GET", "live-primary", _full_url(live_base_url, path), primary_elapsed, primary_response.status_code)

    assert primary_response.status_code == 200
    assert _content_type(primary_response) == "text/csv"

    if compare_base_url:
        secondary_response, secondary_elapsed = _request(live_session, "GET", _full_url(compare_base_url, path), live_timeout)
        invocation_recorder("GET", "live-compare", _full_url(compare_base_url, path), secondary_elapsed, secondary_response.status_code)
        assert secondary_response.status_code == 200
        assert _content_type(secondary_response) == "text/csv"
        assert primary_response.text == secondary_response.text


@pytest.mark.parametrize("path,headers,_assert_payload", JSON_GET_CASES)
def test_live_json_get_endpoints(
    live_base_url,
    compare_base_url,
    live_timeout,
    live_session,
    path,
    headers,
    _assert_payload,
    invocation_recorder,
):
    """Exercise every JSON-style GET endpoint against one or two live targets."""
    _require_live_base_url(live_base_url)

    primary_response, primary_elapsed = _request(live_session, "GET", _full_url(live_base_url, path), live_timeout, headers=headers)
    invocation_recorder("GET", "live-primary", _full_url(live_base_url, path), primary_elapsed, primary_response.status_code)

    assert primary_response.status_code == 200
    assert _content_type(primary_response).endswith("/json")

    primary_payload = _json_payload(primary_response)

    if compare_base_url:
        secondary_response, secondary_elapsed = _request(live_session, "GET", _full_url(compare_base_url, path), live_timeout, headers=headers)
        invocation_recorder("GET", "live-compare", _full_url(compare_base_url, path), secondary_elapsed, secondary_response.status_code)

        assert secondary_response.status_code == 200
        assert _content_type(secondary_response).endswith("/json")
        _compare_json_payloads(path, primary_payload, _json_payload(secondary_response))


@pytest.mark.parametrize("path,expected_mimetype,_expected_body", IMAGE_CASES)
def test_live_binary_endpoints(
    live_base_url,
    compare_base_url,
    live_timeout,
    live_session,
    path,
    expected_mimetype,
    _expected_body,
    invocation_recorder,
):
    """Exercise every binary/image endpoint against one or two live targets."""
    _require_live_base_url(live_base_url)

    primary_response, primary_elapsed = _request(live_session, "GET", _full_url(live_base_url, path), live_timeout)
    invocation_recorder("GET", "live-primary", _full_url(live_base_url, path), primary_elapsed, primary_response.status_code)

    assert primary_response.status_code == 200
    assert _content_type(primary_response) == expected_mimetype

    if compare_base_url:
        secondary_response, secondary_elapsed = _request(live_session, "GET", _full_url(compare_base_url, path), live_timeout)
        invocation_recorder("GET", "live-compare", _full_url(compare_base_url, path), secondary_elapsed, secondary_response.status_code)

        assert secondary_response.status_code == 200
        assert _content_type(secondary_response) == expected_mimetype
        _compare_binary_payloads(path, primary_response.content, secondary_response.content)
