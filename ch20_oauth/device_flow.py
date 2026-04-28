"""
GitHub OAuth Device Flow demo.

The Device Flow allows CLI tools and headless applications to authenticate
users without redirecting them to a local web server. Instead:

1. App requests a device code from GitHub
2. User is shown a URL and a user code
3. User visits the URL and enters the code in their browser
4. App polls GitHub until the user completes authorization
5. App receives an access token

This is the flow used by the GitHub CLI (gh auth login).

To run:
  GITHUB_CLIENT_ID=<your OAuth App client ID> python device_flow.py

Note: your OAuth App must be configured with "Device Flow" enabled.
See: https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#device-flow
"""
import os
import sys
import time
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
if not CLIENT_ID:
    sys.exit("Set GITHUB_CLIENT_ID environment variable")

SCOPES = "read:user"


def request_device_code(client_id, scope):
    response = requests.post(
        "https://github.com/login/device/code",
        headers={"Accept": "application/json"},
        json={"client_id": client_id, "scope": scope},
    )
    response.raise_for_status()
    return response.json()


def poll_for_token(client_id, device_code, interval):
    while True:
        time.sleep(interval)
        response = requests.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            json={
                "client_id": client_id,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
        )
        data = response.json()

        match data.get("error"):
            case "authorization_pending":
                print(".", end="", flush=True)   # user hasn't authorized yet
            case "slow_down":
                interval += 5   # GitHub asked us to slow down
            case "expired_token":
                return None, "Device code expired"
            case "access_denied":
                return None, "User denied authorization"
            case None:
                return data.get("access_token"), None
            case other:
                return None, f"Unknown error: {other}"


def main():
    # Step 1: Get device and user codes
    device_data = request_device_code(CLIENT_ID, SCOPES)
    device_code = device_data["device_code"]
    user_code = device_data["user_code"]
    verification_uri = device_data["verification_uri"]
    interval = device_data.get("interval", 5)
    expires_in = device_data.get("expires_in", 900)

    print(f"\n  1. Open: {verification_uri}")
    print(f"  2. Enter code: {user_code}")
    print(f"\nWaiting for authorization (expires in {expires_in}s)...", end="", flush=True)

    # Step 2: Poll until authorized or expired
    token, error = poll_for_token(CLIENT_ID, device_code, interval)

    if error:
        print(f"\nFailed: {error}")
        sys.exit(1)

    print("\n\nAuthorized!")

    # Step 3: Use the token
    user = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    print(f"Logged in as: {user['login']}")


if __name__ == "__main__":
    main()
