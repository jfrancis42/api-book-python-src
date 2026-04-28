"""Demonstrate different authentication schemes with requests."""
import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


# --- 1. API Key as query parameter (common in older APIs) ---
# Don't do this -- tokens in URLs end up in logs and browser history
# response = requests.get("https://api.example.com/data?api_key=secret")


# --- 2. API Key as header ---
response = requests.get(
    "https://api.github.com/user",
    headers={"Authorization": f"Bearer {GITHUB_TOKEN}"},
)
print(f"Bearer auth: {response.json()['login']}")


# --- 3. HTTP Basic Auth ---
# requests has a built-in shorthand: auth=(username, password)
# GitHub accepts token as the password with any username
response = requests.get(
    "https://api.github.com/user",
    auth=("unused", GITHUB_TOKEN),
)
print(f"Basic auth: {response.json()['login']}")

# What requests sends under the hood:
credentials = base64.b64encode(b"unused:" + GITHUB_TOKEN.encode()).decode()
print(f"Basic header: Authorization: Basic {credentials[:20]}...")


# --- 4. Using a requests.auth.AuthBase subclass ---
from requests.auth import AuthBase

class BearerAuth(AuthBase):
    """Attaches a Bearer token to the request Authorization header."""
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers["Authorization"] = f"Bearer {self.token}"
        return r

response = requests.get(
    "https://api.github.com/zen",
    auth=BearerAuth(GITHUB_TOKEN),
)
print(f"AuthBase: {response.text!r}")
