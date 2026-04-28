from github import GitHubClient
from exceptions import NotFoundError

client = GitHubClient()

# NotFoundError for a non-existent repository
try:
    client.get_repo("this-owner-does-not-exist-xyz", "also-fake")
except NotFoundError as e:
    print(f"NotFoundError: {e} (status {e.status_code})")

# Successful request still works
repo = client.get_repo("torvalds", "linux")
print(f"Success: {repo['full_name']}, {repo['stargazers_count']:,} stars")
