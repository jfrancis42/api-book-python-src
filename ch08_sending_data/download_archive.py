import os
import requests
from dotenv import load_dotenv

load_dotenv()


def download_repo_archive(owner, repo, ref="main", dest="."):
    """Download a repository's source as a zip archive.

    Uses stream=True to avoid loading the entire file into memory.
    Returns the local file path.
    """
    response = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/zipball/{ref}",
        headers={
            "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
            "Accept": "application/vnd.github+json",
        },
        stream=True,
    )
    response.raise_for_status()

    filename = f"{owner}-{repo}-{ref}.zip"
    filepath = os.path.join(dest, filename)

    written = 0
    with open(filepath, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            written += len(chunk)

    return filepath, written


if __name__ == "__main__":
    # Download a small repo to demonstrate streaming
    path, size = download_repo_archive("github", "gitignore", ref="main", dest="/tmp")
    print(f"Downloaded: {path}")
    print(f"Size: {size:,} bytes")
