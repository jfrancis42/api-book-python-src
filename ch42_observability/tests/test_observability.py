import sys
sys.path.insert(0, "..")

import json
import pytest
from fastapi.testclient import TestClient
from main import app, _users
from metrics import metrics
from logging_config import JsonFormatter
import logging


@pytest.fixture(autouse=True)
def reset_state():
    _users.clear()
    metrics.reset()
    yield
    _users.clear()
    metrics.reset()


@pytest.fixture
def client():
    return TestClient(app)


# ------------------------------------------------------------------ #
# Middleware / request ID
# ------------------------------------------------------------------ #

def test_response_has_request_id_header(client):
    r = client.get("/health")
    assert "X-Request-Id" in r.headers
    assert len(r.headers["X-Request-Id"]) > 0


def test_correlation_id_echoed(client):
    r = client.get("/health", headers={"X-Correlation-Id": "my-trace-id"})
    assert r.headers["X-Request-Id"] == "my-trace-id"


def test_different_requests_get_different_ids(client):
    r1 = client.get("/health")
    r2 = client.get("/health")
    assert r1.headers["X-Request-Id"] != r2.headers["X-Request-Id"]


# ------------------------------------------------------------------ #
# Health endpoint
# ------------------------------------------------------------------ #

def test_health_returns_200(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "uptime_s" in data


# ------------------------------------------------------------------ #
# Metrics
# ------------------------------------------------------------------ #

def test_metrics_records_requests(client):
    client.post("/users", json={"login": "octocat", "name": "The Octocat"})
    client.get("/users/octocat")
    client.get("/users/nobody")
    # give middleware a moment (TestClient is sync so it's immediate)
    summary = client.get("/metrics").json()
    counts = summary["requests"]
    # Verify at least one GET and one POST were recorded
    total = sum(counts.values())
    assert total >= 3


def test_metrics_tracks_status_codes(client):
    client.post("/users", json={"login": "octocat", "name": "The Octocat"})
    client.get("/users/octocat")       # 200
    client.get("/users/nobody")        # 404
    summary = client.get("/metrics").json()
    counts = summary["requests"]
    # Find a 200 and a 404 entry
    statuses = [int(k.split()[-1]) for k in counts.keys()]
    assert 200 in statuses
    assert 404 in statuses


# ------------------------------------------------------------------ #
# JSON formatter
# ------------------------------------------------------------------ #

def test_json_formatter_produces_valid_json():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="hello world", args=(), exc_info=None,
    )
    output = formatter.format(record)
    obj = json.loads(output)
    assert obj["msg"] == "hello world"
    assert obj["level"] == "INFO"
    assert "ts" in obj


def test_json_formatter_includes_extra_fields():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="api", level=logging.INFO, pathname="", lineno=0,
        msg="request", args=(), exc_info=None,
    )
    record.request_id = "abc123"
    record.status = 200
    output = json.loads(formatter.format(record))
    assert output["request_id"] == "abc123"
    assert output["status"] == 200
