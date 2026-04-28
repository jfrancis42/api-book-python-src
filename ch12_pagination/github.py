import os
import time
import random
import logging
from datetime import datetime

import requests
from dotenv import load_dotenv

from exceptions import (
    GitHubError, NotFoundError, AuthenticationError,
    PermissionError, RateLimitError, ServerError, ValidationError,
)
from link_header import parse_link_header

load_dotenv()

log = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_STATUSES = {500, 502, 503, 504}


def _parse_dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _backoff(attempt, base=1.0, cap=30.0):
    wait = min(base * (2 ** attempt), cap)
    return wait * random.uniform(0.75, 1.25)


class GitHubClient:
    """GitHub API client -- Chapter 12 version.

    Changes from Chapter 11:
    - _request() now accepts a full URL or a path (for following Link headers).
    - paginate() generator yields all items from multi-page endpoints.
    - list_repos() accepts page_all=True to return all pages automatically.
    - rate_limit dict tracks current limit state after each request.
    """

    BASE_URL = "https://api.github.com"

    def __init__(self, token=None):
        self._token = token or os.getenv("GITHUB_TOKEN")
        self.rate_limit = {"remaining": None, "reset_at": None, "resource": None}

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

    def _update_rate_limit(self, response):
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset = response.headers.get("X-RateLimit-Reset")
        resource = response.headers.get("X-RateLimit-Resource", "core")
        if remaining is not None:
            self.rate_limit = {
                "remaining": int(remaining),
                "reset_at": datetime.fromtimestamp(int(reset)) if reset else None,
                "resource": resource,
            }

    def _request(self, method, path_or_url, **kwargs):
        # Accept either a full URL (from a Link header) or a path fragment
        if path_or_url.startswith("https://"):
            url = path_or_url
        else:
            url = f"{self.BASE_URL}{path_or_url}"

        headers = {**self._base_headers(), **kwargs.pop("headers", {})}

        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = requests.request(method, url, headers=headers, **kwargs)
            except (requests.Timeout, requests.ConnectionError) as e:
                last_error = GitHubError(f"Network error: {e}")
                if attempt < MAX_RETRIES:
                    wait = _backoff(attempt)
                    log.warning("Network error on attempt %d, retrying in %.1fs: %s",
                                attempt + 1, wait, e)
                    time.sleep(wait)
                continue

            if response.status_code in RETRY_STATUSES and attempt < MAX_RETRIES:
                wait = _backoff(attempt)
                log.warning("Server error %d on attempt %d, retrying in %.1fs",
                            response.status_code, attempt + 1, wait)
                time.sleep(wait)
                continue

            self._raise_for_response(response)
            self._update_rate_limit(response)
            return response

        if last_error:
            raise last_error
        raise ServerError(
            f"Server error after {MAX_RETRIES} retries",
            status_code=response.status_code,
        )

    def _get(self, path_or_url, **kwargs):
        return self._request("GET", path_or_url, **kwargs)

    def _post(self, path, **kwargs):
        return self._request("POST", path, **kwargs)

    def _patch(self, path, **kwargs):
        return self._request("PATCH", path, **kwargs)

    def _delete(self, path, **kwargs):
        return self._request("DELETE", path, **kwargs)

    def paginate(self, path, params=None, key=None):
        """Yield all items from a paginated GitHub endpoint.

        path:   API path or full URL
        params: initial query parameters (per_page defaults to 100)
        key:    if set, extract response[key] instead of the whole response list
                (use "items" for search endpoints)
        """
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
            params = {}   # next URL already contains all query params

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
        """Return one page of repos (up to per_page, max 100)."""
        return self._get(
            f"/users/{username}/repos",
            params={"sort": sort, "per_page": per_page, "type": type},
        ).json()

    def list_all_repos(self, username, sort="updated", type="public"):
        """Yield every public repo for username, following pagination automatically."""
        yield from self.paginate(
            f"/users/{username}/repos",
            params={"sort": sort, "type": type},
        )

    def search_repos(self, query, sort="stars", order="desc", per_page=10):
        """Search repositories (one page)."""
        return self._get(
            "/search/repositories",
            params={"q": query, "sort": sort, "order": order, "per_page": per_page},
        ).json()

    def search_all_repos(self, query, sort="stars", order="desc"):
        """Yield every matching repository, following pagination automatically."""
        yield from self.paginate(
            "/search/repositories",
            params={"q": query, "sort": sort, "order": order},
            key="items",
        )

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
