"""Compare sequential vs parallel API fetching."""
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, ".")
from github import GitHubClient

USERNAMES = [
    "torvalds", "gvanrossum", "antirez", "tpope",
    "fabpot", "ry", "sindresorhus", "addyosmani",
]


def main():
    # Sequential
    client = GitHubClient()
    start = time.perf_counter()
    sequential_results = [client.get_user(u) for u in USERNAMES]
    sequential_time = time.perf_counter() - start
    client.close()

    # Parallel (shared session -- thread-safe for reads)
    client = GitHubClient()
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=8) as pool:
        parallel_results = list(pool.map(client.get_user, USERNAMES))
    parallel_time = time.perf_counter() - start
    client.close()

    print(f"Sequential: {sequential_time:.2f}s")
    print(f"Parallel:   {parallel_time:.2f}s")
    print(f"Speedup:    {sequential_time / parallel_time:.1f}x")


if __name__ == "__main__":
    main()
