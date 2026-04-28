import requests


class GitHubClient:
    """A client for the GitHub REST API.

    This class grows chapter by chapter. Each addition encapsulates
    a concern -- authentication, rate limits, retries -- so callers
    don't have to handle it themselves.
    """

    BASE_URL = "https://api.github.com"

    def __init__(self):
        pass  # Chapter 6 adds token auth here

    def _get(self, path, **kwargs):
        """Make a GET request to the GitHub API.

        Raises requests.HTTPError for 4xx and 5xx responses.
        """
        url = f"{self.BASE_URL}{path}"
        response = requests.get(url, **kwargs)
        response.raise_for_status()
        return response

    # --- Public methods ---

    def get_zen(self):
        """Return a random GitHub engineering aphorism."""
        return self._get("/zen").text

    def get_user(self, username):
        """Return a dict of public information about a GitHub user."""
        return self._get(f"/users/{username}").json()

    def get_repo(self, owner, repo):
        """Return a dict of information about a GitHub repository."""
        return self._get(f"/repos/{owner}/{repo}").json()
