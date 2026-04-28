import os
import asyncio
import logging
from datetime import datetime

import httpx
from dotenv import load_dotenv

from exceptions import (
    GitHubError, NotFoundError, AuthenticationError,
    PermissionError, RateLimitError, ServerError, ValidationError,
)
from link_header import parse_link_header

load_dotenv()

log = logging.getLogger(__name__)

RETRY_STATUSES = {500, 502, 503, 504}


def _parse_dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


class AsyncGitHubClient:
    """Async GitHub API client using httpx.

    Usage:
        async with AsyncGitHubClient() as client:
            user = await client.get_user("torvalds")
    """

    BASE_URL = "https://api.github.com"
    DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)

    def __init__(self, token=None, timeout=None):
        self._token = token or os.getenv("GITHUB_TOKEN")
        self._timeout = timeout or self.DEFAULT_TIMEOUT
        self._client = None

    async def __aenter__(self):
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        self._client = httpx.AsyncClient(
            headers=headers,
            timeout=self._timeout,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
        return self

    async def __aexit__(self, *args):
        await self._client.aclose()

    def _raise_for_response(self, response):
        if response.is_success:
            return
        try:
            body = response.json()
            message = body.get("message", response.reason_phrase)
        except Exception:
            message = response.text or response.reason_phrase

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

    async def _request(self, method, path_or_url, **kwargs):
        url = (path_or_url if path_or_url.startswith("https://")
               else f"{self.BASE_URL}{path_or_url}")
        try:
            response = await self._client.request(method, url, **kwargs)
        except httpx.TimeoutException as e:
            raise GitHubError(f"Request to {url} timed out: {e}")
        except httpx.NetworkError as e:
            raise GitHubError(f"Network error: {e}")
        self._raise_for_response(response)
        return response

    async def _get(self, path_or_url, **kwargs):
        return await self._request("GET", path_or_url, **kwargs)

    async def _post(self, path, **kwargs):
        return await self._request("POST", path, **kwargs)

    async def _patch(self, path, **kwargs):
        return await self._request("PATCH", path, **kwargs)

    async def paginate(self, path, params=None, key=None):
        params = dict(params or {})
        params.setdefault("per_page", 100)
        url = path if path.startswith("https://") else f"{self.BASE_URL}{path}"
        while url:
            response = await self._get(url, params=params)
            page = response.json()
            items = page[key] if key else page
            for item in items:
                yield item
            link = parse_link_header(response.headers.get("link", ""))
            url = link.get("next")
            params = {}

    # ------------------------------------------------------------------ #
    # Public API methods
    # ------------------------------------------------------------------ #

    async def get_zen(self):
        return (await self._get("/zen")).text

    async def get_user(self, username):
        data = (await self._get(f"/users/{username}")).json()
        data["created_at"] = _parse_dt(data["created_at"])
        data["updated_at"] = _parse_dt(data["updated_at"])
        return data

    async def get_authenticated_user(self):
        if not self._token:
            return None
        data = (await self._get("/user")).json()
        data["created_at"] = _parse_dt(data["created_at"])
        return data

    async def get_repo(self, owner, repo):
        data = (await self._get(f"/repos/{owner}/{repo}")).json()
        for field in ("created_at", "updated_at", "pushed_at"):
            if data.get(field):
                data[field] = _parse_dt(data[field])
        return data

    async def list_all_repos(self, username, sort="updated", type="public"):
        async for repo in self.paginate(
            f"/users/{username}/repos",
            params={"sort": sort, "type": type},
        ):
            yield repo

    async def search_repos(self, query, sort="stars", order="desc", per_page=10):
        return (await self._get(
            "/search/repositories",
            params={"q": query, "sort": sort, "order": order, "per_page": per_page},
        )).json()
