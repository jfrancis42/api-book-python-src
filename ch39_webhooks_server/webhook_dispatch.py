"""Webhook dispatch — Chapter 39.

Signs and delivers webhook events to subscribers in background threads.
"""
import hashlib
import hmac
import json
import logging
import threading
import time
import uuid

import requests

log = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAYS = [5, 30, 120]


def sign_payload(secret: str, body: bytes) -> str:
    """Return 'sha256=<hex>' HMAC for the payload."""
    mac = hmac.new(secret.encode(), body, hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


def build_delivery(event: str, payload: dict) -> tuple[str, bytes]:
    """Return (delivery_id, json_body)."""
    delivery_id = str(uuid.uuid4())
    body = json.dumps({"event": event, **payload}).encode()
    return delivery_id, body


def dispatch_event(owner: str, repo: str, event: str, payload: dict,
                   subscriptions: list[dict]) -> None:
    """Fire-and-forget: dispatch to matching active subscriptions."""
    for sub in subscriptions:
        if not sub["active"]:
            continue
        sub_events = json.loads(sub["events"])
        if event not in sub_events and "*" not in sub_events:
            continue
        delivery_id, body = build_delivery(event, payload)
        signature = sign_payload(sub["secret"], body)
        thread = threading.Thread(
            target=_deliver,
            args=(sub["payload_url"], delivery_id, event, body, signature),
            daemon=True,
        )
        thread.start()


def _deliver(url: str, delivery_id: str, event: str,
             body: bytes, signature: str) -> None:
    headers = {
        "Content-Type": "application/json",
        "X-MiniGitHub-Event": event,
        "X-MiniGitHub-Delivery": delivery_id,
        "X-Hub-Signature-256": signature,
    }
    for attempt, delay in enumerate(RETRY_DELAYS):
        try:
            r = requests.post(url, data=body, headers=headers, timeout=10)
            if r.status_code < 300:
                log.info("Delivered %s to %s (attempt %d)",
                         delivery_id, url, attempt + 1)
                return
            log.warning("Delivery %s got %d from %s, retrying",
                        delivery_id, r.status_code, url)
        except requests.RequestException as e:
            log.warning("Delivery %s failed: %s, retrying", delivery_id, e)
        if attempt < len(RETRY_DELAYS) - 1:
            time.sleep(delay)

    log.error("Delivery %s permanently failed after %d attempts",
              delivery_id, MAX_RETRIES)
