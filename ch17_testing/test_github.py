"""Tests for GitHubClient using the responses library to mock HTTP calls."""
import pytest
import responses as resp

from github import GitHubClient
from exceptions import NotFoundError, AuthenticationError, RateLimitError


GITHUB_API = "https://api.github.com"


@resp.activate
def test_get_zen():
    resp.add(
        resp.GET,
        f"{GITHUB_API}/zen",
        body="Keep it logically awesome.",
        status=200,
        content_type="text/plain;charset=utf-8",
    )
    client = GitHubClient(token="fake-token")
    assert client.get_zen() == "Keep it logically awesome."


@resp.activate
def test_get_user_returns_parsed_dates():
    resp.add(
        resp.GET,
        f"{GITHUB_API}/users/octocat",
        json={
            "login": "octocat",
            "id": 1,
            "followers": 12345,
            "created_at": "2011-01-25T18:44:36Z",
            "updated_at": "2024-01-01T00:00:00Z",
        },
        status=200,
    )
    client = GitHubClient(token="fake-token")
    user = client.get_user("octocat")
    assert user["login"] == "octocat"
    # created_at should be a datetime, not a string
    from datetime import datetime, timezone
    assert isinstance(user["created_at"], datetime)
    assert user["created_at"].tzinfo == timezone.utc


@resp.activate
def test_get_user_not_found_raises():
    resp.add(
        resp.GET,
        f"{GITHUB_API}/users/nonexistent-user-xyz",
        json={"message": "Not Found", "documentation_url": "https://docs.github.com"},
        status=404,
    )
    client = GitHubClient(token="fake-token")
    with pytest.raises(NotFoundError) as exc_info:
        client.get_user("nonexistent-user-xyz")
    assert exc_info.value.status_code == 404


@resp.activate
def test_bad_token_raises_authentication_error():
    resp.add(
        resp.GET,
        f"{GITHUB_API}/user",
        json={"message": "Bad credentials"},
        status=401,
    )
    client = GitHubClient(token="bad-token")
    with pytest.raises(AuthenticationError):
        client.get_authenticated_user()


@resp.activate
def test_rate_limit_headers_are_tracked():
    resp.add(
        resp.GET,
        f"{GITHUB_API}/zen",
        body="It's not fully shipped until it's fast.",
        status=200,
        content_type="text/plain;charset=utf-8",
        headers={
            "X-RateLimit-Remaining": "4995",
            "X-RateLimit-Reset": "1714320000",
            "X-RateLimit-Resource": "core",
        },
    )
    client = GitHubClient(token="fake-token")
    client.get_zen()
    assert client.rate_limit["remaining"] == 4995
    assert client.rate_limit["resource"] == "core"


@resp.activate
def test_list_repos_returns_list():
    resp.add(
        resp.GET,
        f"{GITHUB_API}/users/octocat/repos",
        json=[
            {"name": "Hello-World", "stargazers_count": 2000, "language": "C"},
            {"name": "Spoon-Knife", "stargazers_count": 1000, "language": None},
        ],
        status=200,
    )
    client = GitHubClient(token="fake-token")
    repos = client.list_repos("octocat")
    assert len(repos) == 2
    assert repos[0]["name"] == "Hello-World"


@resp.activate
def test_paginate_follows_link_header():
    # First page
    resp.add(
        resp.GET,
        f"{GITHUB_API}/users/octocat/repos",
        json=[{"name": "repo-1"}, {"name": "repo-2"}],
        status=200,
        headers={
            "Link": (
                f'<{GITHUB_API}/users/octocat/repos?page=2&per_page=100>; rel="next", '
                f'<{GITHUB_API}/users/octocat/repos?page=2&per_page=100>; rel="last"'
            )
        },
    )
    # Second page (no Link header = last page)
    resp.add(
        resp.GET,
        f"{GITHUB_API}/users/octocat/repos",
        json=[{"name": "repo-3"}],
        status=200,
    )
    client = GitHubClient(token="fake-token")
    repos = list(client.paginate("/users/octocat/repos"))
    assert len(repos) == 3
    assert repos[0]["name"] == "repo-1"
    assert repos[2]["name"] == "repo-3"
