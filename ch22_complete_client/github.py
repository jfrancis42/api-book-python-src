"""Complete GitHubClient -- Chapter 20 capstone version.

Incorporates all techniques from Part I:
- requests.Session with connection pooling (ch13)
- Default timeout (ch13)
- Context manager protocol (ch13)
- Exponential backoff retry via urllib3 (ch11, ch13)
- Full exception hierarchy (ch09)
- Rate limit tracking (ch10)
- Link header pagination (ch12)
- Thread-safe rate limit updates (ch14)
"""
import os
import threading
import logging
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
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


class GitHubClient:
    """Complete GitHub API client.

    Usage:
        with GitHubClient() as client:
            user = client.get_user("torvalds")
            for repo in client.list_all_repos("torvalds"):
                print(repo["name"])
    """

    BASE_URL = "https://api.github.com"
    DEFAULT_TIMEOUT = (5, 30)

    def __init__(self, token=None, timeout=None, max_retries=3):
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
            total=max_retries,
            backoff_factor=1.0,
            status_forcelist=RETRY_STATUSES,
            allowed_methods={"GET"},
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_maxsize=20)
        self._session.mount("https://", adapter)

        self.rate_limit: dict = {"remaining": None, "reset_at": None, "resource": None}
        self._rate_limit_lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # Context manager and lifecycle
    # ------------------------------------------------------------------ #

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self._session.close()

    # ------------------------------------------------------------------ #
    # Internal machinery
    # ------------------------------------------------------------------ #

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

    def _put(self, path, **kwargs):
        return self._request("PUT", path, **kwargs)

    def _delete(self, path, **kwargs):
        return self._request("DELETE", path, **kwargs)

    def paginate(self, path, params=None, key=None):
        """Yield all items from a paginated endpoint."""
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
    # User methods
    # ------------------------------------------------------------------ #

    def get_zen(self):
        return self._get("/zen").text

    def get_user(self, username):
        data = self._get(f"/users/{username}").json()
        data["created_at"] = _parse_dt(data.get("created_at"))
        data["updated_at"] = _parse_dt(data.get("updated_at"))
        return data

    def get_authenticated_user(self):
        if not self._token:
            return None
        data = self._get("/user").json()
        data["created_at"] = _parse_dt(data.get("created_at"))
        return data

    # ------------------------------------------------------------------ #
    # Repository methods
    # ------------------------------------------------------------------ #

    def get_repo(self, owner, repo):
        data = self._get(f"/repos/{owner}/{repo}").json()
        for field in ("created_at", "updated_at", "pushed_at"):
            data[field] = _parse_dt(data.get(field))
        return data

    def list_repos(self, username, sort="updated", per_page=30, type="public"):
        """Return one page of repos."""
        return self._get(
            f"/users/{username}/repos",
            params={"sort": sort, "per_page": per_page, "type": type},
        ).json()

    def list_all_repos(self, username, sort="updated", type="public"):
        """Yield all repos for username across all pages."""
        yield from self.paginate(
            f"/users/{username}/repos",
            params={"sort": sort, "type": type},
        )

    def get_repo_languages(self, owner, repo):
        """Return dict of {language: bytes_of_code}."""
        return self._get(f"/repos/{owner}/{repo}/languages").json()

    def get_readme(self, owner, repo, ref=None):
        """Return the decoded README content as a string."""
        params = {}
        if ref:
            params["ref"] = ref
        data = self._get(
            f"/repos/{owner}/{repo}/readme",
            params=params,
            headers={"Accept": "application/vnd.github.raw+json"},
        )
        return data.text

    # ------------------------------------------------------------------ #
    # Issue methods
    # ------------------------------------------------------------------ #

    def list_issues(self, owner, repo, state="open", per_page=30):
        """Return one page of issues."""
        return self._get(
            f"/repos/{owner}/{repo}/issues",
            params={"state": state, "per_page": per_page},
        ).json()

    def list_all_issues(self, owner, repo, state="open"):
        """Yield all issues across all pages."""
        yield from self.paginate(
            f"/repos/{owner}/{repo}/issues",
            params={"state": state},
        )

    def get_issue(self, owner, repo, number):
        return self._get(f"/repos/{owner}/{repo}/issues/{number}").json()

    def create_issue(self, owner, repo, title, body="", labels=None, assignees=None):
        payload = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees
        return self._post(f"/repos/{owner}/{repo}/issues", json=payload).json()

    def update_issue(self, owner, repo, number, **kwargs):
        """Update fields of an issue. Pass title=, body=, state=, labels=, etc."""
        return self._patch(
            f"/repos/{owner}/{repo}/issues/{number}", json=kwargs
        ).json()

    def close_issue(self, owner, repo, number):
        return self.update_issue(owner, repo, number, state="closed")

    def add_comment(self, owner, repo, issue_number, body):
        return self._post(
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
            json={"body": body},
        ).json()

    # ------------------------------------------------------------------ #
    # Search methods
    # ------------------------------------------------------------------ #

    def search_repos(self, query, sort="stars", order="desc", per_page=10):
        """Search repositories (one page)."""
        return self._get(
            "/search/repositories",
            params={"q": query, "sort": sort, "order": order, "per_page": per_page},
        ).json()

    def search_all_repos(self, query, sort="stars", order="desc"):
        """Yield all search results across pages."""
        yield from self.paginate(
            "/search/repositories",
            params={"q": query, "sort": sort, "order": order},
            key="items",
        )

    def search_code(self, query, per_page=10):
        """Search code (one page)."""
        return self._get(
            "/search/code",
            params={"q": query, "per_page": per_page},
        ).json()

    def search_issues(self, query, sort="created", order="desc", per_page=10):
        """Search issues and pull requests (one page)."""
        return self._get(
            "/search/issues",
            params={"q": query, "sort": sort, "order": order, "per_page": per_page},
        ).json()

    # ------------------------------------------------------------------ #
    # Gist methods (useful for testing write operations)
    # ------------------------------------------------------------------ #

    def create_gist(self, description, files, public=False):
        """Create a gist. files: {filename: {"content": "..."}}."""
        return self._post(
            "/gists",
            json={"description": description, "public": public, "files": files},
        ).json()

    def update_gist(self, gist_id, description=None, files=None):
        payload = {}
        if description is not None:
            payload["description"] = description
        if files is not None:
            payload["files"] = files
        return self._patch(f"/gists/{gist_id}", json=payload).json()

    def delete_gist(self, gist_id):
        self._delete(f"/gists/{gist_id}")

    # ------------------------------------------------------------------ #
    # Archive download
    # ------------------------------------------------------------------ #

    def download_archive(self, owner, repo, ref="HEAD", format="zipball"):
        """Download a repository archive, returning the response for streaming."""
        return self._get(
            f"/repos/{owner}/{repo}/{format}/{ref}",
            timeout=(5, 120),
            stream=True,
        )
