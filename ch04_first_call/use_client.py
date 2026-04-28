from github import GitHubClient

client = GitHubClient()

print(client.get_zen())

user = client.get_user("torvalds")
print(f"{user['name']} has {user['public_repos']} public repositories.")

repo = client.get_repo("torvalds", "linux")
print(f"linux: {repo['stargazers_count']:,} stars, {repo['open_issues_count']:,} open issues")
