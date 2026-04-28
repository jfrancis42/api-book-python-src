from github import GitHubClient

client = GitHubClient()

me = client.get_authenticated_user()
if me:
    print(f"Authenticated as: {me['login']}")
    print(f"Name: {me['name']}")
else:
    print("No token set -- running unauthenticated.")

repo = client.get_repo("torvalds", "linux")
print(f"linux stars: {repo['stargazers_count']:,}")
