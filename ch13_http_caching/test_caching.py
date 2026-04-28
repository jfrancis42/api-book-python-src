"""Tests for the Chapter 13 ETag caching layer."""
import json
import pytest
from unittest.mock import MagicMock, patch
from github import GitHubClient, _parse_max_age, _synthetic_response


def make_response(status=200, body=None, etag=None, cache_control=None):
    import requests
    resp = requests.Response()
    resp.status_code = status
    resp._content = json.dumps(body or {}).encode()
    resp.headers["Content-Type"] = "application/json"
    if etag:
        resp.headers["ETag"] = etag
    if cache_control:
        resp.headers["Cache-Control"] = cache_control
    return resp


def test_parse_max_age_present():
    assert _parse_max_age("public, max-age=60, s-maxage=60") == 60


def test_parse_max_age_absent():
    assert _parse_max_age("no-cache") is None


def test_parse_max_age_malformed():
    assert _parse_max_age("max-age=abc") is None


def test_first_request_is_miss():
    client = GitHubClient(token="fake")
    resp_data = {"login": "octocat"}
    mock_resp = make_response(200, resp_data, etag='"abc123"', cache_control="max-age=60")

    with patch("requests.request", return_value=mock_resp):
        result = client._request("GET", "/users/octocat")

    assert result.json() == resp_data
    assert client.cache_stats()["misses"] == 1
    assert client.cache_stats()["hits"] == 0


def test_second_request_within_max_age_is_hit():
    client = GitHubClient(token="fake")
    resp_data = {"login": "octocat"}
    mock_resp = make_response(200, resp_data, etag='"abc123"', cache_control="max-age=3600")

    with patch("requests.request", return_value=mock_resp):
        client._request("GET", "/users/octocat")

    # Second call should not hit the network at all
    with patch("requests.request", side_effect=AssertionError("should not call network")):
        result = client._request("GET", "/users/octocat")

    assert result.json() == resp_data
    stats = client.cache_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1


def test_304_response_is_revalidation():
    import time
    client = GitHubClient(token="fake")
    resp_data = {"login": "octocat"}

    # First: populate cache with expired entry (max-age=0)
    first_resp = make_response(200, resp_data, etag='"abc123"', cache_control="max-age=0")
    with patch("requests.request", return_value=first_resp):
        client._request("GET", "/users/octocat")

    # Second: server returns 304
    import requests as req_module
    not_modified = req_module.Response()
    not_modified.status_code = 304
    not_modified._content = b""

    with patch("requests.request", return_value=not_modified):
        result = client._request("GET", "/users/octocat")

    assert result.json() == resp_data
    stats = client.cache_stats()
    assert stats["revalidations"] == 1
    assert stats["misses"] == 1


def test_if_none_match_sent_on_stale_cache():
    """Verify that If-None-Match is attached when cache is stale."""
    import time
    client = GitHubClient(token="fake")
    resp_data = {"login": "octocat"}

    first_resp = make_response(200, resp_data, etag='"abc123"', cache_control="max-age=0")
    captured_headers = {}

    def capture(method, url, headers=None, **kwargs):
        captured_headers.update(headers or {})
        return first_resp

    with patch("requests.request", side_effect=capture):
        client._request("GET", "/users/octocat")

    second_resp = make_response(200, {"login": "octocat"}, etag='"def456"')
    with patch("requests.request", side_effect=lambda m, u, headers=None, **kw: (
        captured_headers.update(headers or {}) or second_resp
    )):
        client._request("GET", "/users/octocat")

    assert "If-None-Match" in captured_headers
    assert captured_headers["If-None-Match"] == '"abc123"'


def test_synthetic_response_is_200():
    r = _synthetic_response({"key": "value"})
    assert r.status_code == 200
    assert r.json() == {"key": "value"}
