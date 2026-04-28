import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def _parse_dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


class GitHubClient:
    """GitHub API client -- Chapter 7 version.

    Changes from Chapter 6:
    - search_repos() added.
    - list_repos() now accepts sort, per_page, type parameters explicitly.
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

    def _get(self, path, **kwargs):
        url = f"{self.BASE_URL}{path}"
        headers = {**self._base_headers(), **kwargs.pop("headers", {})}
        response = requests.get(url, headers=headers, **kwargs)
        response.raise_for_status()
        return response

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
        """List public repositories for a user."""
        return self._get(
            f"/users/{username}/repos",
            params={"sort": sort, "per_page": per_page, "type": type},
        ).json()

    def search_repos(self, query, sort="stars", order="desc", per_page=10):
        """Search GitHub repositories.

        query: GitHub search query string, including optional qualifiers
               such as 'language:python' or 'stars:>1000'.
        Returns the full search result dict with 'items' and 'total_count'.
        """
        return self._get(
            "/search/repositories",
            params={
                "q": query,
                "sort": sort,
                "order": order,
                "per_page": per_page,
            },
        ).json()
