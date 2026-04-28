"""Fetch multiple GitHub user profiles concurrently with asyncio."""
import asyncio
import time

from async_github import AsyncGitHubClient

USERNAMES = [
    "torvalds", "gvanrossum", "antirez", "tpope",
    "fabpot", "ry", "sindresorhus", "addyosmani",
    "mxcl", "oerdnj",
]


async def main():
    async with AsyncGitHubClient() as client:
        start = time.perf_counter()

        tasks = [client.get_user(u) for u in USERNAMES]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        elapsed = time.perf_counter() - start

    users = []
    errors = []
    for username, result in zip(USERNAMES, results):
        if isinstance(result, Exception):
            errors.append((username, result))
        else:
            users.append(result)

    for user in sorted(users, key=lambda u: u["followers"], reverse=True):
        print(f"  {user['login']:20s} {user['followers']:>8,} followers")
    for username, err in errors:
        print(f"  ERROR {username}: {err}")

    print(f"\nFetched {len(users)} users in {elapsed:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
