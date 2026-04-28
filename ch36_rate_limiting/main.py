"""Chapter 33: Rate limiting with slowapi.

Install: pip install slowapi
Run:     uvicorn main:app --reload

Test limits by hitting the same endpoint repeatedly.
"""
import sys
sys.path.insert(0, ".")

from fastapi import FastAPI, HTTPException, Depends, Request, Response, Query
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session
import orm_models, database, crud
from auth import get_current_user
from pagination import build_link_header
from models import (UserCreate, UserResponse, RepoCreate, RepoResponse,
                    IssueCreate, IssueResponse, RepoUpdate, IssueUpdate)

orm_models.Base.metadata.create_all(bind=database.engine)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Mini-GitHub", version="1.3.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ---------------------------------------------------------------------------
# Rate-limited read endpoints
# ---------------------------------------------------------------------------

@app.get("/users/{username}", response_model=UserResponse, name="get_user", tags=["users"])
@limiter.limit("60/minute")
def get_user(request: Request, username: str, db: Session = Depends(database.get_db)):
    user = crud.get_user(db, username)
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    return user


@app.get("/users/{username}/repos", response_model=list[RepoResponse], tags=["repos"])
@limiter.limit("60/minute")
def list_user_repos(
    request: Request, username: str,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=30, ge=1, le=100),
    response: Response = None,
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


@app.get("/repos/{owner}/{repo}", response_model=RepoResponse, name="get_repo", tags=["repos"])
@limiter.limit("60/minute")
def get_repo(request: Request, owner: str, repo: str, db: Session = Depends(database.get_db)):
    r = crud.get_repo(db, owner, repo)
    if not r:
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")
    return r


# ---------------------------------------------------------------------------
# Write endpoints (auth required, higher rate limit)
# ---------------------------------------------------------------------------

@app.post("/users", response_model=UserResponse, status_code=201, tags=["users"])
@limiter.limit("10/minute")
def create_user(request: Request, user_in: UserCreate, response: Response,
                db: Session = Depends(database.get_db)):
    if crud.get_user(db, user_in.login):
        raise HTTPException(status_code=409, detail=f"User '{user_in.login}' already exists")
    user = crud.create_user(db, **user_in.model_dump())
    response.headers["Location"] = str(request.url_for("get_user", username=user.login))
    return user


@app.post("/users/{username}/repos", response_model=RepoResponse, status_code=201, tags=["repos"])
@limiter.limit("10/minute")
def create_repo(
    request: Request, username: str, repo_in: RepoCreate, response: Response,
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


@app.delete("/repos/{owner}/{repo}", status_code=204, tags=["repos"])
@limiter.limit("10/minute")
def delete_repo(
    request: Request, owner: str, repo: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    if current_user != owner:
        raise HTTPException(status_code=403, detail="Cannot delete another user's repository")
    if not crud.delete_repo(db, owner, repo):
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")


@app.get("/repos/{owner}/{repo}/issues", response_model=list[IssueResponse], tags=["issues"])
@limiter.limit("60/minute")
def list_issues(request: Request, owner: str, repo: str, state: str = "open",
                db: Session = Depends(database.get_db)):
    if not crud.get_repo(db, owner, repo):
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")
    return crud.get_repo_issues(db, owner, repo, state=state)


@app.post("/repos/{owner}/{repo}/issues", response_model=IssueResponse,
          status_code=201, name="create_issue", tags=["issues"])
@limiter.limit("10/minute")
def create_issue(
    request: Request, owner: str, repo: str, issue_in: IssueCreate, response: Response,
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
@limiter.limit("60/minute")
def get_issue(request: Request, owner: str, repo: str, number: int,
              db: Session = Depends(database.get_db)):
    issue = crud.get_issue(db, owner, repo, number)
    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue #{number} not found")
    return issue
