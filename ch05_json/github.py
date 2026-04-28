import requests
from datetime import datetime, timezone


def _parse_dt(s):
    """Parse a GitHub ISO 8601 date string to a UTC-aware datetime."""
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


class GitHubClient:
    """GitHub API client -- Chapter 5 version.

    Changes from Chapter 4:
    - get_user() returns created_at as a datetime object.
    - get_repo() returns created_at/updated_at/pushed_at as datetime objects.
    """

    BASE_URL = "https://api.github.com"

    def __init__(self):
        pass  # Chapter 6 adds token auth here

    def _get(self, path, **kwargs):
        url = f"{self.BASE_URL}{path}"
        response = requests.get(url, **kwargs)
        response.raise_for_status()
        return response

    def get_zen(self):
        return self._get("/zen").text

    def get_user(self, username):
        data = self._get(f"/users/{username}").json()
        data["created_at"] = _parse_dt(data["created_at"])
        data["updated_at"] = _parse_dt(data["updated_at"])
        return data

    def get_repo(self, owner, repo):
        data = self._get(f"/repos/{owner}/{repo}").json()
        for field in ("created_at", "updated_at", "pushed_at"):
            if data.get(field):
                data[field] = _parse_dt(data[field])
        return data

    def list_repos(self, username, **params):
        """Return a list of public repos for a user.

        Accepts any query parameters supported by the API,
        e.g. sort="updated", per_page=10.
        """
        return self._get(
            f"/users/{username}/repos",
            params=params,
        ).json()
