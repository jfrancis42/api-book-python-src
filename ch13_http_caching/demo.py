"""Demonstrate ETag-based conditional requests.

Run twice in quick succession to see the cache at work:
  python demo.py

The second run of get_user("octocat") should be served from the
ETag cache (revalidation) or from Cache-Control freshness (hit).
"""
import logging
import os
from github import GitHubClient

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")

client = GitHubClient(os.environ["GITHUB_TOKEN"])

print("\n--- First fetch (expected: miss) ---")
user = client.get_user("octocat")
print(f"login: {user['login']}, public_repos: {user['public_repos']}")
print("stats:", client.cache_stats())

print("\n--- Second fetch (expected: hit or revalidation) ---")
user2 = client.get_user("octocat")
print(f"login: {user2['login']}, public_repos: {user2['public_repos']}")
print("stats:", client.cache_stats())

print("\n--- Repo fetch (expected: miss) ---")
repo = client.get_repo("octocat", "hello-world")
print(f"repo: {repo['full_name']}, stars: {repo['stargazers_count']}")

print("\n--- Repo re-fetch (expected: hit or revalidation) ---")
repo2 = client.get_repo("octocat", "hello-world")
print(f"repo: {repo2['full_name']}")
print("final stats:", client.cache_stats())
