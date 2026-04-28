"""Demo of the complete GitHubClient -- Chapter 20 capstone."""
import time
from concurrent.futures import ThreadPoolExecutor
from github import GitHubClient


def repo_summary(client, owner, repo):
    """Fetch a repo and its top languages."""
    r = client.get_repo(owner, repo)
    langs = client.get_repo_languages(owner, repo)
    top_lang = max(langs, key=langs.get) if langs else "unknown"
    return {
        "full_name": r["full_name"],
        "stars": r["stargazers_count"],
        "language": top_lang,
        "pushed_at": r["pushed_at"],
        "description": (r.get("description") or "")[:60],
    }


def main():
    with GitHubClient() as client:
        print(f"Connected: {client.get_zen()}\n")

        # Parallel fetch of several notable repos
        repos_to_check = [
            ("torvalds", "linux"),
            ("python", "cpython"),
            ("git", "git"),
            ("vim", "vim"),
            ("antirez", "redis"),
        ]

        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=5) as pool:
            summaries = list(pool.map(
                lambda args: repo_summary(client, *args),
                repos_to_check,
            ))
        elapsed = time.perf_counter() - start

        print(f"{'Repository':<30} {'Stars':>8}  {'Language':<12} {'Description'}")
        print("-" * 80)
        for s in sorted(summaries, key=lambda x: x["stars"], reverse=True):
            print(f"{s['full_name']:<30} {s['stars']:>8,}  {s['language']:<12} {s['description']}")

        print(f"\nFetched {len(summaries)} repos in {elapsed:.2f}s")
        print(f"Rate limit remaining: {client.rate_limit['remaining']}")


if __name__ == "__main__":
    main()
