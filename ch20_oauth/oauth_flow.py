"""
GitHub OAuth 2.0 Authorization Code flow demo.

This is a minimal Flask app that demonstrates the complete OAuth dance:
1. User visits /login -- redirected to GitHub authorization page
2. User approves -- GitHub redirects back to /callback with ?code=...
3. App exchanges code for access token
4. App uses access token to fetch user info

To run this demo:
1. Create a GitHub OAuth App at https://github.com/settings/applications/new
   - Homepage URL: http://localhost:5000
   - Callback URL: http://localhost:5000/callback
2. Set environment variables:
   GITHUB_CLIENT_ID=<your client id>
   GITHUB_CLIENT_SECRET=<your client secret>
3. Run: python oauth_flow.py
4. Visit http://localhost:5000
"""
import os
import secrets
import requests
from flask import Flask, redirect, request, session, url_for
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_URL = "https://api.github.com"

SCOPES = "read:user"


@app.route("/")
def index():
    user = session.get("user")
    if user:
        return f"<h1>Hello, {user['login']}!</h1><p><a href='/logout'>Logout</a></p>"
    return "<h1>Not logged in</h1><p><a href='/login'>Login with GitHub</a></p>"


@app.route("/login")
def login():
    # Generate a random state parameter to prevent CSRF
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state

    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": url_for("callback", _external=True),
        "scope": SCOPES,
        "state": state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return redirect(f"{GITHUB_AUTHORIZE_URL}?{query}")


@app.route("/callback")
def callback():
    # Verify state to prevent CSRF
    state = request.args.get("state")
    if state != session.pop("oauth_state", None):
        return "State mismatch -- possible CSRF attack", 400

    code = request.args.get("code")
    if not code:
        error = request.args.get("error_description", "Access denied")
        return f"Authorization failed: {error}", 400

    # Exchange authorization code for access token
    token_response = requests.post(
        GITHUB_TOKEN_URL,
        headers={"Accept": "application/json"},
        json={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "redirect_uri": url_for("callback", _external=True),
        },
    )
    token_data = token_response.json()

    access_token = token_data.get("access_token")
    if not access_token:
        return f"Token exchange failed: {token_data}", 400

    # Use the access token to fetch user info
    user_response = requests.get(
        f"{GITHUB_API_URL}/user",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        },
    )
    user = user_response.json()

    # Store in session (in production, store in database)
    session["user"] = {"login": user["login"], "token": access_token}

    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
