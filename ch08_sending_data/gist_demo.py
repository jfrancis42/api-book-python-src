"""
Demonstrates POST, PATCH, and DELETE using the GitHub Gist API.
Gists are a safe sandbox: easy to create and delete, same HTTP
patterns as issues and other GitHub resources.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def create_gist(description, files, public=False):
    payload = {
        "description": description,
        "public": public,
        "files": {name: {"content": content} for name, content in files.items()},
    }
    response = requests.post(
        "https://api.github.com/gists",
        headers=HEADERS,
        json=payload,
    )
    response.raise_for_status()
    return response.json()


def update_gist(gist_id, description=None, files=None):
    payload = {}
    if description is not None:
        payload["description"] = description
    if files is not None:
        payload["files"] = {name: {"content": content} for name, content in files.items()}
    response = requests.patch(
        f"https://api.github.com/gists/{gist_id}",
        headers=HEADERS,
        json=payload,
    )
    response.raise_for_status()
    return response.json()


def delete_gist(gist_id):
    response = requests.delete(
        f"https://api.github.com/gists/{gist_id}",
        headers=HEADERS,
    )
    response.raise_for_status()
    return response.status_code == 204


if __name__ == "__main__":
    # Create
    gist = create_gist(
        description="API book test gist",
        files={"hello.py": 'print("hello from the API book")'},
    )
    gist_id = gist["id"]
    print(f"Created: {gist['html_url']}")

    # Update
    updated = update_gist(gist_id, description="API book test gist (updated)")
    print(f"Updated description: {updated['description']}")

    # Delete
    deleted = delete_gist(gist_id)
    print(f"Deleted: {deleted}")
