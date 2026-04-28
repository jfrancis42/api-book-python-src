"""Chapter 32: API key authentication on write endpoints."""
import sys
sys.path.insert(0, ".")

from fastapi import FastAPI, HTTPException, Depends, Request, Response, Query, status
from sqlalchemy.orm import Session
import orm_models, database, crud
from auth import get_current_user
from pagination import build_link_header
from models import (UserCreate, UserUpdate, UserResponse,
                    RepoCreate, RepoUpdate, RepoResponse,
                    IssueCreate, IssueUpdate, IssueResponse)

orm_models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Mini-GitHub", version="1.2.0")


# ---------------------------------------------------------------------------
# Users — read is public, write requires auth
# ---------------------------------------------------------------------------

@app.get("/users/{username}", response_model=UserResponse, name="get_user", tags=["users"])
def get_user(username: str, db: Session = Depends(database.get_db)):
    user = crud.get_user(db, username)
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    return user


@app.post("/users", response_model=UserResponse, status_code=201, tags=["users"])
def create_user(user_in: UserCreate, request: Request, response: Response,
                db: Session = Depends(database.get_db)):
    if crud.get_user(db, user_in.login):
        raise HTTPException(status_code=409, detail=f"User '{user_in.login}' already exists")
    user = crud.create_user(db, **user_in.model_dump())
    response.headers["Location"] = str(request.url_for("get_user", username=user.login))
    return user


# ---------------------------------------------------------------------------
# Repos — create/update/delete require auth and ownership check
# ---------------------------------------------------------------------------

@app.get("/repos/{owner}/{repo}", response_model=RepoResponse, name="get_repo", tags=["repos"])
def get_repo(owner: str, repo: str, db: Session = Depends(database.get_db)):
    r = crud.get_repo(db, owner, repo)
    if not r:
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")
    return r


@app.get("/users/{username}/repos", response_model=list[RepoResponse], tags=["repos"])
def list_user_repos(
    username: str,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=30, ge=1, le=100),
    request: Request = None, response: Response = None,
    db: Session = Depends(database.get_db),
):
    if not crud.get_user(db, username):
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    total = crud.count_user_repos(db, username)
    repos = crud.get_user_repos(db, username, skip=(page - 1) * per_page, limit=per_page)
    response.headers["X-Total-Count"] = str(total)
    if link := build_link_header(request, page, per_page, total):
        response.headers["Link"] = link
    return repos


@app.post("/users/{username}/repos", response_model=RepoResponse, status_code=201, tags=["repos"])
def create_repo(
    username: str, repo_in: RepoCreate,
    request: Request, response: Response,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    if current_user != username:
        raise HTTPException(status_code=403, detail="Cannot create repos for another user")
    if not crud.get_user(db, username):
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    if crud.get_repo(db, username, repo_in.name):
        raise HTTPException(status_code=409,
                            detail=f"Repository '{username}/{repo_in.name}' already exists")
    repo = crud.create_repo(db, owner=username, **repo_in.model_dump())
    response.headers["Location"] = str(request.url_for("get_repo", owner=username, repo=repo.name))
    return repo


@app.patch("/repos/{owner}/{repo}", response_model=RepoResponse, tags=["repos"])
def update_repo(
    owner: str, repo: str, repo_in: RepoUpdate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    if current_user != owner:
        raise HTTPException(status_code=403, detail="Cannot modify another user's repository")
    if not crud.get_repo(db, owner, repo):
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")
    return crud.update_repo(db, owner, repo, repo_in.model_dump(exclude_unset=True))


@app.delete("/repos/{owner}/{repo}", status_code=204, tags=["repos"])
def delete_repo(
    owner: str, repo: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    if current_user != owner:
        raise HTTPException(status_code=403, detail="Cannot delete another user's repository")
    if not crud.delete_repo(db, owner, repo):
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------

@app.get("/repos/{owner}/{repo}/issues", response_model=list[IssueResponse], tags=["issues"])
def list_issues(owner: str, repo: str, state: str = "open",
                db: Session = Depends(database.get_db)):
    if not crud.get_repo(db, owner, repo):
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")
    return crud.get_repo_issues(db, owner, repo, state=state)


@app.post("/repos/{owner}/{repo}/issues", response_model=IssueResponse,
          status_code=201, name="create_issue", tags=["issues"])
def create_issue(
    owner: str, repo: str, issue_in: IssueCreate,
    request: Request, response: Response,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    if not crud.get_repo(db, owner, repo):
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")
    issue = crud.create_issue(db, owner=owner, repo=repo, author=current_user,
                              title=issue_in.title, body=issue_in.body, labels=issue_in.labels)
    response.headers["Location"] = str(
        request.url_for("get_issue", owner=owner, repo=repo, number=issue.number)
    )
    return issue


@app.get("/repos/{owner}/{repo}/issues/{number}", response_model=IssueResponse,
         name="get_issue", tags=["issues"])
def get_issue(owner: str, repo: str, number: int, db: Session = Depends(database.get_db)):
    issue = crud.get_issue(db, owner, repo, number)
    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue #{number} not found")
    return issue
