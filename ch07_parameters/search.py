from github import GitHubClient

client = GitHubClient()

results = client.search_repos("http api client language:python stars:>500")
print(f"Total results: {results['total_count']:,}")
print()
for repo in results["items"]:
    print(f"{repo['full_name']:45} {repo['stargazers_count']:>8,} stars")
