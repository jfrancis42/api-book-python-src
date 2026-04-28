import os
import time
import random
import logging
import threading
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

from exceptions import (
    GitHubError, NotFoundError, AuthenticationError,
    PermissionError, RateLimitError, ServerError, ValidationError,
)
from link_header import parse_link_header

load_dotenv()

log = logging.getLogger(__name__)

RETRY_STATUSES = (500, 502, 503, 504)


def _parse_dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


class GitHubClient:
    """GitHub API client -- Chapter 14 version.

    Changes from Chapter 13:
    - _rate_limit_lock protects rate_limit dict from concurrent writes.
    - pool_maxsize increased to match max_workers for threaded use.
    """

    BASE_URL = "https://api.github.com"
    DEFAULT_TIMEOUT = (5, 30)   # (connect seconds, read seconds)

    def __init__(self, token=None, timeout=None):
        self._token = token or os.getenv("GITHUB_TOKEN")
        self._timeout = timeout or self.DEFAULT_TIMEOUT

        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        if self._token:
            self._session.headers["Authorization"] = f"Bearer {self._token}"

        retry = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=RETRY_STATUSES,
            allowed_methods={"GET"},
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_maxsize=20)
        self._session.mount("https://", adapter)

        self.rate_limit = {"remaining": None, "reset_at": None, "resource": None}
        self._rate_limit_lock = threading.Lock()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self._session.close()

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

    def _update_rate_limit(self, response):
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset = response.headers.get("X-RateLimit-Reset")
        resource = response.headers.get("X-RateLimit-Resource", "core")
        if remaining is not None:
            with self._rate_limit_lock:
                self.rate_limit = {
                    "remaining": int(remaining),
                    "reset_at": datetime.fromtimestamp(int(reset)) if reset else None,
                    "resource": resource,
                }

    def _request(self, method, path_or_url, **kwargs):
        url = (path_or_url if path_or_url.startswith("https://")
               else f"{self.BASE_URL}{path_or_url}")
        kwargs.setdefault("timeout", self._timeout)
        try:
            response = self._session.request(method, url, **kwargs)
        except requests.Timeout:
            raise GitHubError(f"Request to {url} timed out")
        except requests.ConnectionError as e:
            raise GitHubError(f"Connection failed: {e}")
        self._raise_for_response(response)
        self._update_rate_limit(response)
        return response

    def _get(self, path_or_url, **kwargs):
        return self._request("GET", path_or_url, **kwargs)

    def _post(self, path, **kwargs):
        return self._request("POST", path, **kwargs)

    def _patch(self, path, **kwargs):
        return self._request("PATCH", path, **kwargs)

    def _delete(self, path, **kwargs):
        return self._request("DELETE", path, **kwargs)

    def paginate(self, path, params=None, key=None):
        params = dict(params or {})
        params.setdefault("per_page", 100)
        url = path if path.startswith("https://") else f"{self.BASE_URL}{path}"
        while url:
            response = self._get(url, params=params)
            page = response.json()
            items = page[key] if key else page
            yield from items
            link = parse_link_header(response.headers.get("Link", ""))
            url = link.get("next")
            params = {}

    # ------------------------------------------------------------------ #
    # Public API methods
    # ------------------------------------------------------------------ #

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

    def list_all_repos(self, username, sort="updated", type="public"):
        yield from self.paginate(
            f"/users/{username}/repos",
            params={"sort": sort, "type": type},
        )

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
