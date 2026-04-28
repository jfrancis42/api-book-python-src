import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from exceptions import (
    GitHubError, NotFoundError, AuthenticationError,
    PermissionError, RateLimitError, ServerError, ValidationError,
)

load_dotenv()


def _parse_dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


class GitHubClient:
    """GitHub API client -- Chapter 9 version.

    Changes from Chapter 8:
    - _get() replaced by _request(), supporting all HTTP methods.
    - All requests raise specific GitHubError subclasses on failure.
    """

    BASE_URL = "https://api.github.com"

    def __init__(self, token=None):
        self._token = token or os.getenv("GITHUB_TOKEN")

    def _base_headers(self):
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _raise_for_response(self, response):
        if response.ok:
            return
        try:
            body = response.json()
            message = body.get("message", response.reason)
        except ValueError:
            message = response.text or response.reason

        status = response.status_code
        kwargs = {"status_code": status, "response": response}

        match status:
            case 401:
                raise AuthenticationError(message, **kwargs)
            case 403:
                if "rate limit" in message.lower():
                    reset_ts = int(response.headers.get("X-RateLimit-Reset", 0))
                    reset_at = datetime.fromtimestamp(reset_ts) if reset_ts else None
                    raise RateLimitError(message, reset_at=reset_at, **kwargs)
                raise PermissionError(message, **kwargs)
            case 404:
                raise NotFoundError(message, **kwargs)
            case 422:
                raise ValidationError(message, **kwargs)
            case _ if 500 <= status < 600:
                raise ServerError(message, **kwargs)
            case _:
                raise GitHubError(message, **kwargs)

    def _request(self, method, path, **kwargs):
        url = f"{self.BASE_URL}{path}"
        headers = {**self._base_headers(), **kwargs.pop("headers", {})}
        try:
            response = requests.request(method, url, headers=headers, **kwargs)
        except requests.Timeout:
            raise GitHubError(f"Request to {url} timed out")
        except requests.ConnectionError as e:
            raise GitHubError(f"Connection failed: {e}")
        self._raise_for_response(response)
        return response

    def _get(self, path, **kwargs):
        return self._request("GET", path, **kwargs)

    def _post(self, path, **kwargs):
        return self._request("POST", path, **kwargs)

    def _patch(self, path, **kwargs):
        return self._request("PATCH", path, **kwargs)

    def _put(self, path, **kwargs):
        return self._request("PUT", path, **kwargs)

    def _delete(self, path, **kwargs):
        return self._request("DELETE", path, **kwargs)

    def get_zen(self):
        return self._get("/zen").text

    def get_user(self, username):
        data = self._get(f"/users/{username}").json()
        data["created_at"] = _parse_dt(data["created_at"])
        data["updated_at"] = _parse_dt(data["updated_at"])
        return data

    def get_authenticated_user(self):
        if not self._token:
            return None
        data = self._get("/user").json()
        data["created_at"] = _parse_dt(data["created_at"])
        return data

    def get_repo(self, owner, repo):
        data = self._get(f"/repos/{owner}/{repo}").json()
        for field in ("created_at", "updated_at", "pushed_at"):
            if data.get(field):
                data[field] = _parse_dt(data[field])
        return data

    def list_repos(self, username, sort="updated", per_page=30, type="public"):
        return self._get(
            f"/users/{username}/repos",
            params={"sort": sort, "per_page": per_page, "type": type},
        ).json()

    def search_repos(self, query, sort="stars", order="desc", per_page=10):
        return self._get(
            "/search/repositories",
            params={"q": query, "sort": sort, "order": order, "per_page": per_page},
        ).json()

    def create_issue(self, owner, repo, title, body="", labels=None):
        payload = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        return self._post(f"/repos/{owner}/{repo}/issues", json=payload).json()

    def close_issue(self, owner, repo, issue_number):
        return self._patch(
            f"/repos/{owner}/{repo}/issues/{issue_number}",
            json={"state": "closed"},
        ).json()
