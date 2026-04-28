"""GitHub webhook receiver — Chapter 21.

Start with:  flask --app receiver run --port 9000
Expose via:  ngrok http 9000
"""
import hashlib
import hmac
import json
import os
from flask import Flask, abort, request

app = Flask(__name__)

WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "dev-secret")


def verify_signature(secret: str, body: bytes, sig_header: str) -> bool:
    """Return True when the payload HMAC matches X-Hub-Signature-256."""
    if not sig_header.startswith("sha256="):
        return False
    expected = sig_header[len("sha256="):]
    mac = hmac.new(secret.encode(), body, hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), expected)


@app.post("/webhook")
def webhook():
    raw_body = request.get_data()
    sig = request.headers.get("X-Hub-Signature-256", "")

    if not verify_signature(WEBHOOK_SECRET, raw_body, sig):
        abort(403, "Invalid signature")

    event = request.headers.get("X-GitHub-Event", "unknown")
    delivery = request.headers.get("X-GitHub-Delivery", "")
    payload = json.loads(raw_body)

    handle_event(event, delivery, payload)
    return {"ok": True}, 200


def handle_event(event: str, delivery: str, payload: dict) -> None:
    match event:
        case "push":
            repo = payload["repository"]["full_name"]
            ref = payload["ref"]
            commits = len(payload.get("commits", []))
            print(f"[{delivery[:8]}] push to {repo} {ref}: {commits} commit(s)")

        case "issues":
            action = payload["action"]
            issue = payload["issue"]
            print(f"[{delivery[:8]}] issue #{issue['number']} {action}: {issue['title']}")

        case "ping":
            print(f"[{delivery[:8]}] ping — zen: {payload.get('zen', '')}")

        case _:
            print(f"[{delivery[:8]}] unhandled event: {event}")
