"""Tests for the Chapter 21 webhook receiver."""
import hashlib
import hmac
import json
import pytest
from receiver import app, WEBHOOK_SECRET


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def make_headers(body: bytes, event: str = "push") -> dict:
    mac = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256)
    return {
        "X-GitHub-Event": event,
        "X-GitHub-Delivery": "test-delivery-id",
        "X-Hub-Signature-256": f"sha256={mac.hexdigest()}",
        "Content-Type": "application/json",
    }


def test_push_event_accepted(client):
    payload = {
        "ref": "refs/heads/main",
        "repository": {"full_name": "octocat/hello-world"},
        "commits": [{"id": "abc"}],
    }
    body = json.dumps(payload).encode()
    r = client.post("/webhook", data=body, headers=make_headers(body, "push"))
    assert r.status_code == 200
    assert r.get_json()["ok"] is True


def test_invalid_signature_rejected(client):
    body = b'{"ref": "refs/heads/main", "repository": {"full_name": "x/y"}, "commits": []}'
    headers = {
        "X-GitHub-Event": "push",
        "X-GitHub-Delivery": "bad-delivery",
        "X-Hub-Signature-256": "sha256=badhash",
        "Content-Type": "application/json",
    }
    r = client.post("/webhook", data=body, headers=headers)
    assert r.status_code == 403


def test_missing_signature_rejected(client):
    body = b'{"ref": "refs/heads/main"}'
    r = client.post("/webhook", data=body,
                    headers={"Content-Type": "application/json"})
    assert r.status_code == 403


def test_ping_event_accepted(client):
    payload = {"zen": "Keep it logically awesome.", "hook_id": 1}
    body = json.dumps(payload).encode()
    r = client.post("/webhook", data=body, headers=make_headers(body, "ping"))
    assert r.status_code == 200


def test_issues_event_accepted(client):
    payload = {
        "action": "opened",
        "issue": {"number": 42, "title": "Something broken"},
        "repository": {"full_name": "octocat/hello-world"},
    }
    body = json.dumps(payload).encode()
    r = client.post("/webhook", data=body, headers=make_headers(body, "issues"))
    assert r.status_code == 200


def test_wrong_prefix_in_signature_rejected(client):
    payload = {"zen": "test"}
    body = json.dumps(payload).encode()
    mac = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256)
    headers = make_headers(body, "ping")
    # Use sha1= prefix instead of sha256=
    headers["X-Hub-Signature-256"] = f"sha1={mac.hexdigest()}"
    r = client.post("/webhook", data=body, headers=headers)
    assert r.status_code == 403
