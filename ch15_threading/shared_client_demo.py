"""Demonstrate sharing one GitHubClient across threads (session is thread-safe for reads)."""
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, ".")
from github import GitHubClient

USERNAMES = ["torvalds", "gvanrossum", "antirez", "tpope", "fabpot"]


def main():
    # One shared client -- session's connection pool is thread-safe
    with GitHubClient() as client:
        start = time.perf_counter()

        def fetch(username):
            return client.get_user(username)

        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(fetch, USERNAMES))

        elapsed = time.perf_counter() - start

        for user in sorted(results, key=lambda u: u["followers"], reverse=True):
            print(f"  {user['login']:20s} {user['followers']:>8,} followers")
        print(f"\nFetched {len(results)} users in {elapsed:.2f}s")


if __name__ == "__main__":
    main()
