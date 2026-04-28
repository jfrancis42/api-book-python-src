"""Demonstrate HMAC request signing (common in AWS, Stripe, etc.)."""
import hmac
import hashlib
import time
import requests
from requests.auth import AuthBase


class HMACAuth(AuthBase):
    """Signs requests with HMAC-SHA256.

    Typical pattern used by payment APIs and webhooks:
    - Concatenate method + path + timestamp + body
    - Sign with the secret key
    - Send signature in a header
    """

    def __init__(self, key_id, secret):
        self.key_id = key_id
        self.secret = secret.encode() if isinstance(secret, str) else secret

    def __call__(self, r):
        timestamp = str(int(time.time()))
        body = r.body or b""
        if isinstance(body, str):
            body = body.encode()

        message = f"{r.method}\n{r.path_url}\n{timestamp}\n".encode() + body
        signature = hmac.new(self.secret, message, hashlib.sha256).hexdigest()

        r.headers["X-Timestamp"] = timestamp
        r.headers["X-Key-Id"] = self.key_id
        r.headers["X-Signature"] = signature
        return r


# Demo: shows what the signed headers look like (can't verify without a real server)
fake_auth = HMACAuth("my-key-id", "super-secret-key")

req = requests.Request(
    "POST",
    "https://api.example.com/charges",
    json={"amount": 1000, "currency": "usd"},
    auth=fake_auth,
)
prepared = req.prepare()
print("Signed headers:")
for name, value in prepared.headers.items():
    if name.startswith("X-"):
        print(f"  {name}: {value}")
