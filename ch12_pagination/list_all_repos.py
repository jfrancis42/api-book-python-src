"""Demonstrate pagination by listing all repos for a user with many repos."""
import sys
sys.path.insert(0, ".")

from github import GitHubClient

client = GitHubClient()

# A user with many repositories makes a good pagination demo
username = "torvalds"

print(f"Fetching all repos for {username}...\n")

repos = list(client.list_all_repos(username))
print(f"Total repos fetched: {len(repos)}")
for repo in sorted(repos, key=lambda r: r["stargazers_count"], reverse=True)[:5]:
    print(f"  {repo['name']:40s} {repo['stargazers_count']:>8,} stars")

remaining = client.rate_limit.get("remaining")
if remaining is not None:
    print(f"\nRate limit remaining: {remaining}")
