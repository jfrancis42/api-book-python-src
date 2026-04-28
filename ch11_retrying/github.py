"""Chapter 11: GitHubClient with exponential backoff retry logic."""
import os
import time
import random
import logging
import requests
from dotenv import load_dotenv
from exceptions import (
    GitHubError, NotFoundError, RateLimitError,
    AuthError, ServerError, ClientError,
)
from link_header import parse_link_header

load_dotenv()

log = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_STATUSES = {500, 502, 503, 504}


def _backoff(attempt: int, base: float = 1.0, cap: float = 30.0) -> float:
    """Exponential backoff with ±25% jitter."""
    wait = min(base * (2 ** attempt), cap)
    return wait * random.uniform(0.75, 1.25)


class GitHubClient:
    BASE_URL = "https://api.github.com"
    DEFAULT_TIMEOUT = (5, 30)

    def __init__(self, token: str | None = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.rate_limit: dict = {}
        self._session = requests.Session()
        self._session.headers.update(self._base_headers())

    def _base_headers(self) -> dict:
        headers = {"Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _update_rate_limit(self, response: requests.Response) -> None:
        remaining = response.headers.get("X-RateLimit-Remaining")
        limit = response.headers.get("X-RateLimit-Limit")
        reset = response.headers.get("X-RateLimit-Reset")
        if remaining is not None:
            self.rate_limit = {
                "remaining": int(remaining),
                "limit": int(limit) if limit else None,
                "reset": int(reset) if reset else None,
            }

    def _raise_for_response(self, response: requests.Response) -> None:
        if response.ok:
            return
        try:
            detail = response.json().get("message", response.text)
        except Exception:
            detail = response.text
        status = response.status_code
        if status == 401:
            raise AuthError(detail, status_code=status)
        if status == 403:
            if "rate limit" in detail.lower():
                raise RateLimitError(detail, status_code=status)
            raise AuthError(detail, status_code=status)
        if status == 404:
            raise NotFoundError(detail, status_code=status)
        if status == 422:
            raise ClientError(detail, status_code=status)
        if status >= 500:
            raise ServerError(detail, status_code=status)
        raise GitHubError(detail, status_code=status)

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.BASE_URL}{path}"
        kwargs.setdefault("timeout", self.DEFAULT_TIMEOUT)

        last_exc: Exception | None = None
        response: requests.Response | None = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self._session.request(method, url, **kwargs)
            except (requests.Timeout, requests.ConnectionError) as e:
                last_exc = GitHubError(f"Network error: {e}")
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

        if last_exc:
            raise last_exc
        raise ServerError(f"Server error after {MAX_RETRIES} retries",
                          status_code=response.status_code if response else 0)

    def get(self, path: str, **kwargs) -> requests.Response:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self._request("POST", path, **kwargs)

    def get_user(self, username: str) -> dict:
        return self.get(f"/users/{username}").json()

    def get_repos(self, username: str) -> list[dict]:
        return self.get(f"/users/{username}/repos").json()

    def paginate(self, path: str, key: str | None = None, **kwargs):
        url: str | None = f"{self.BASE_URL}{path}"
        while url:
            if url.startswith(self.BASE_URL):
                r = self._session.request("GET", url,
                                          headers=self._base_headers(),
                                          timeout=self.DEFAULT_TIMEOUT,
                                          **kwargs)
            else:
                r = self._session.request("GET", url,
                                          headers=self._base_headers(),
                                          timeout=self.DEFAULT_TIMEOUT)
            self._raise_for_response(r)
            self._update_rate_limit(r)
            data = r.json()
            items = data[key] if key else data
            yield from items
            links = parse_link_header(r.headers.get("Link", ""))
            url = links.get("next")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._session.close()

    def close(self):
        self._session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    client = GitHubClient()
    user = client.get_user("octocat")
    print(f"{user['login']}: {user['public_repos']} repos")
    print(f"Rate limit remaining: {client.rate_limit.get('remaining')}")
