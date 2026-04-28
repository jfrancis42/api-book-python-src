"""Fetch multiple GitHub user profiles in parallel using ThreadPoolExecutor."""
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, ".")
from github import GitHubClient

USERNAMES = [
    "torvalds", "gvanrossum", "antirez", "tpope",
    "fabpot", "ry", "sindresorhus", "addyosmani",
    "mxcl", "oerdnj",
]


def fetch_one(username):
    # Each thread gets its own client (its own session)
    client = GitHubClient()
    try:
        return username, client.get_user(username), None
    except Exception as e:
        return username, None, e
    finally:
        client.close()


def main():
    start = time.perf_counter()

    results = []
    errors = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(fetch_one, u): u for u in USERNAMES}
        for future in as_completed(futures):
            username, user, error = future.result()
            if error:
                errors.append((username, error))
            else:
                results.append(user)

    elapsed = time.perf_counter() - start

    results.sort(key=lambda u: u["followers"], reverse=True)
    for user in results:
        print(f"  {user['login']:20s} {user['followers']:>8,} followers")
    for username, err in errors:
        print(f"  ERROR {username}: {err}")

    print(f"\nFetched {len(results)} users in {elapsed:.2f}s")


if __name__ == "__main__":
    main()
