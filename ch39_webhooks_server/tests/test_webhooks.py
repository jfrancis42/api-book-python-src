import sys
sys.path.insert(0, "..")

import hashlib
import hmac as hmac_mod
import json
import time
import responses as resp_lib
import pytest
from webhook_dispatch import dispatch_event, sign_payload, build_delivery


def test_sign_payload_format():
    sig = sign_payload("secret", b"hello")
    assert sig.startswith("sha256=")
    assert len(sig) == len("sha256=") + 64


def test_sign_payload_correctness():
    expected = hmac_mod.new(b"secret", b"hello", hashlib.sha256).hexdigest()
    assert sign_payload("secret", b"hello") == f"sha256={expected}"


def test_build_delivery_includes_event():
    delivery_id, body = build_delivery("push", {"ref": "refs/heads/main"})
    parsed = json.loads(body)
    assert parsed["event"] == "push"
    assert parsed["ref"] == "refs/heads/main"
    assert len(delivery_id) == 36  # UUID4


@resp_lib.activate
def test_dispatch_posts_to_subscriber():
    resp_lib.add(resp_lib.POST, "https://example.com/hook", status=200)

    subs = [{"active": True, "events": '["issues"]',
              "secret": "mysecret", "payload_url": "https://example.com/hook"}]
    dispatch_event("octocat", "hello-world", "issues", {"action": "opened"}, subs)
    time.sleep(0.3)

    assert len(resp_lib.calls) == 1
    call = resp_lib.calls[0]
    assert call.request.headers["X-MiniGitHub-Event"] == "issues"
    assert call.request.headers["X-Hub-Signature-256"].startswith("sha256=")


@resp_lib.activate
def test_delivery_signature_is_valid():
    """Verify delivered signature matches what a subscriber would compute."""
    resp_lib.add(resp_lib.POST, "https://example.com/hook", status=200)
    secret = "subscriber-secret"
    subs = [{"active": True, "events": '["push"]',
              "secret": secret, "payload_url": "https://example.com/hook"}]
    dispatch_event("octocat", "hello-world", "push", {"ref": "refs/heads/main"}, subs)
    time.sleep(0.3)

    call = resp_lib.calls[0]
    body = call.request.body
    if isinstance(body, str):
        body = body.encode()
    sig_header = call.request.headers["X-Hub-Signature-256"]
    expected_hex = sig_header[len("sha256="):]
    actual_hex = hmac_mod.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert hmac_mod.compare_digest(actual_hex, expected_hex)


@resp_lib.activate
def test_dispatch_skips_inactive_subscription():
    resp_lib.add(resp_lib.POST, "https://example.com/hook", status=200)

    subs = [{"active": False, "events": '["issues"]',
              "secret": "mysecret", "payload_url": "https://example.com/hook"}]
    dispatch_event("octocat", "hello-world", "issues", {"action": "opened"}, subs)
    time.sleep(0.2)
    assert len(resp_lib.calls) == 0


@resp_lib.activate
def test_dispatch_skips_unsubscribed_event():
    resp_lib.add(resp_lib.POST, "https://example.com/hook", status=200)

    subs = [{"active": True, "events": '["push"]',
              "secret": "mysecret", "payload_url": "https://example.com/hook"}]
    dispatch_event("octocat", "hello-world", "issues", {"action": "opened"}, subs)
    time.sleep(0.2)
    assert len(resp_lib.calls) == 0


@resp_lib.activate
def test_dispatch_wildcard_event():
    resp_lib.add(resp_lib.POST, "https://example.com/hook", status=200)

    subs = [{"active": True, "events": '["*"]',
              "secret": "mysecret", "payload_url": "https://example.com/hook"}]
    dispatch_event("octocat", "hello-world", "issues", {"action": "opened"}, subs)
    time.sleep(0.3)
    assert len(resp_lib.calls) == 1


@resp_lib.activate
def test_dispatch_multiple_subscribers():
    resp_lib.add(resp_lib.POST, "https://a.example.com/hook", status=200)
    resp_lib.add(resp_lib.POST, "https://b.example.com/hook", status=200)

    subs = [
        {"active": True, "events": '["push"]',
         "secret": "s1", "payload_url": "https://a.example.com/hook"},
        {"active": True, "events": '["push"]',
         "secret": "s2", "payload_url": "https://b.example.com/hook"},
    ]
    dispatch_event("octocat", "hello-world", "push", {"ref": "refs/heads/main"}, subs)
    time.sleep(0.4)
    assert len(resp_lib.calls) == 2
