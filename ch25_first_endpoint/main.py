"""Chapter 22: Path parameters and Pydantic response models.

Run: uvicorn main:app --reload
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Mini-GitHub", version="0.2.0")


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class UserResponse(BaseModel):
    login: str
    id: int
    name: Optional[str] = None
    bio: Optional[str] = None
    public_repos: int = 0
    followers: int = 0
    created_at: datetime


class RepoResponse(BaseModel):
    id: int
    name: str
    full_name: str
    owner: str
    description: Optional[str] = None
    language: Optional[str] = None
    stargazers_count: int = 0
    created_at: datetime


# ---------------------------------------------------------------------------
# In-memory data store (replaced by a database in Chapter 24)
# ---------------------------------------------------------------------------

_USERS: dict[str, dict] = {
    "octocat": {
        "login": "octocat",
        "id": 1,
        "name": "The Octocat",
        "bio": "GitHub mascot",
        "public_repos": 8,
        "followers": 12000,
        "created_at": datetime(2011, 1, 25, 18, 44, 36, tzinfo=timezone.utc),
    },
    "torvalds": {
        "login": "torvalds",
        "id": 2,
        "name": "Linus Torvalds",
        "bio": "Just a random Finnish dude",
        "public_repos": 11,
        "followers": 250000,
        "created_at": datetime(2011, 9, 3, 15, 26, 22, tzinfo=timezone.utc),
    },
}

_REPOS: list[dict] = [
    {
        "id": 1,
        "name": "Hello-World",
        "full_name": "octocat/Hello-World",
        "owner": "octocat",
        "description": "My first repository",
        "language": "C",
        "stargazers_count": 2000,
        "created_at": datetime(2011, 1, 26, tzinfo=timezone.utc),
    },
    {
        "id": 2,
        "name": "linux",
        "full_name": "torvalds/linux",
        "owner": "torvalds",
        "description": "Linux kernel source tree",
        "language": "C",
        "stargazers_count": 231000,
        "created_at": datetime(2011, 9, 4, tzinfo=timezone.utc),
    },
]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {"message": "Mini-GitHub API"}


@app.get("/users/{username}", response_model=UserResponse)
def get_user(username: str):
    user = _USERS.get(username.lower())
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    return user


@app.get("/repos/{owner}/{repo}", response_model=RepoResponse)
def get_repo(owner: str, repo: str):
    for r in _REPOS:
        if r["owner"].lower() == owner.lower() and r["name"].lower() == repo.lower():
            return r
    raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")


@app.get("/users/{username}/repos", response_model=list[RepoResponse])
def list_user_repos(username: str):
    if username.lower() not in _USERS:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    return [r for r in _REPOS if r["owner"].lower() == username.lower()]
