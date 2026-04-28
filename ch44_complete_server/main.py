"""Chapter 39: The complete Mini-GitHub server.

Assembles all Part II features:
  - SQLite (swap DATABASE_URL for PostgreSQL in production)
  - APIRouter organization
  - POST with 201 + Location
  - PATCH / DELETE
  - Custom error handlers
  - Pagination with Link headers + X-Total-Count
  - Authentication (Bearer token)
  - Rate limiting (slowapi)
  - Search endpoints
  - File upload / download (avatar, README)
  - Health check

Run:  uvicorn main:app --reload
Docs: http://localhost:8000/docs

Test with the Part I client:
  from src.ch20_complete_client.github import GitHubClient
  client = GitHubClient(base_url="http://localhost:8000", token="test-token-octocat")
"""
import io
import os
import re
import shutil
import sys
sys.path.insert(0, ".")

from contextlib import asynccontextmanager
from fastapi import (FastAPI, HTTPException, Depends, Request, Response,
                     Query, UploadFile, File, status)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import func
from sqlalchemy.orm import Session

import orm_models
import database
import crud
from auth import get_current_user
from pagination import build_link_header
from models import (UserCreate, UserUpdate, UserResponse,
                    RepoCreate, RepoUpdate, RepoResponse,
                    IssueCreate, IssueUpdate, IssueResponse)

AVATAR_DIR = "/tmp/mini-github-avatars"
os.makedirs(AVATAR_DIR, exist_ok=True)

orm_models.Base.metadata.create_all(bind=database.engine)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Mini-GitHub",
    version="2.0.0",
    description="A GitHub-compatible REST API. See /docs for the interactive reference.",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ---------------------------------------------------------------------------
# Consistent error responses
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code},
        headers=getattr(exc, "headers", None) or {},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [{"field": ".".join(str(l) for l in e["loc"]), "message": e["msg"]}
               for e in exc.errors()]
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation failed", "status_code": 422, "errors": errors},
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Users
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


@app.get("/users/{username}", response_model=UserResponse, name="get_user", tags=["users"])
@limiter.limit("60/minute")
def get_user(request: Request, username: str, db: Session = Depends(database.get_db)):
    user = crud.get_user(db, username)
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    return user


@app.patch("/users/{username}", response_model=UserResponse, tags=["users"])
def update_user(username: str, user_in: UserUpdate,
                current_user: str = Depends(get_current_user),
                db: Session = Depends(database.get_db)):
    if current_user != username:
        raise HTTPException(status_code=403, detail="Cannot modify another user's profile")
    if not crud.get_user(db, username):
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    return crud.update_user(db, username, user_in.model_dump(exclude_unset=True))


# ---------------------------------------------------------------------------
# Avatar
# ---------------------------------------------------------------------------

@app.put("/users/{username}/avatar", tags=["users"])
async def upload_avatar(username: str, file: UploadFile = File(...),
                        db: Session = Depends(database.get_db)):
    if not crud.get_user(db, username):
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    header = await file.read(8)
    await file.seek(0)
    if not (header[:2] == b"\xff\xd8" or header[:4] == b"\x89PNG"):
        raise HTTPException(status_code=422, detail="File must be a JPEG or PNG image")
    dest = os.path.join(AVATAR_DIR, username)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    user = crud.get_user(db, username)
    user.avatar_path = dest
    db.commit()
    return {"message": "Avatar uploaded"}


@app.get("/users/{username}/avatar", tags=["users"])
def get_avatar(username: str, db: Session = Depends(database.get_db)):
    user = crud.get_user(db, username)
    if not user or not user.avatar_path or not os.path.exists(user.avatar_path):
        raise HTTPException(status_code=404, detail="No avatar found")
    return FileResponse(user.avatar_path, media_type="image/png")


# ---------------------------------------------------------------------------
# Repos
# ---------------------------------------------------------------------------

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


@app.patch("/repos/{owner}/{repo}", response_model=RepoResponse, tags=["repos"])
def update_repo(owner: str, repo: str, repo_in: RepoUpdate,
                current_user: str = Depends(get_current_user),
                db: Session = Depends(database.get_db)):
    if current_user != owner:
        raise HTTPException(status_code=403, detail="Cannot modify another user's repository")
    if not crud.get_repo(db, owner, repo):
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")
    return crud.update_repo(db, owner, repo, repo_in.model_dump(exclude_unset=True))


@app.delete("/repos/{owner}/{repo}", status_code=204, tags=["repos"])
def delete_repo(owner: str, repo: str,
                current_user: str = Depends(get_current_user),
                db: Session = Depends(database.get_db)):
    if current_user != owner:
        raise HTTPException(status_code=403, detail="Cannot delete another user's repository")
    if not crud.delete_repo(db, owner, repo):
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")


# ---------------------------------------------------------------------------
# README
# ---------------------------------------------------------------------------

@app.put("/repos/{owner}/{repo}/readme", tags=["repos"])
async def upload_readme(owner: str, repo: str, file: UploadFile = File(...),
                        db: Session = Depends(database.get_db)):
    r = crud.get_repo(db, owner, repo)
    if not r:
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")
    content = await file.read()
    r.readme = content.decode("utf-8", errors="replace")
    db.commit()
    return {"message": "README uploaded", "size": len(content)}


@app.get("/repos/{owner}/{repo}/readme", tags=["repos"])
def get_readme(owner: str, repo: str, db: Session = Depends(database.get_db)):
    r = crud.get_repo(db, owner, repo)
    if not r or not r.readme:
        raise HTTPException(status_code=404, detail="README not found")
    content = r.readme.encode()
    return StreamingResponse(io.BytesIO(content),
                              media_type="text/plain; charset=utf-8",
                              headers={"Content-Length": str(len(content))})


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------

@app.get("/repos/{owner}/{repo}/issues", response_model=list[IssueResponse], tags=["issues"])
@limiter.limit("60/minute")
def list_issues(
    request: Request, owner: str, repo: str, state: str = "open",
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=30, ge=1, le=100),
    response: Response = None,
    db: Session = Depends(database.get_db),
):
    if not crud.get_repo(db, owner, repo):
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")
    total = crud.count_repo_issues(db, owner, repo, state=state)
    issues = crud.get_repo_issues(db, owner, repo, state=state,
                                  skip=(page - 1) * per_page, limit=per_page)
    response.headers["X-Total-Count"] = str(total)
    if link := build_link_header(request, page, per_page, total):
        response.headers["Link"] = link
    return issues


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


@app.patch("/repos/{owner}/{repo}/issues/{number}", response_model=IssueResponse, tags=["issues"])
def update_issue(owner: str, repo: str, number: int, issue_in: IssueUpdate,
                 current_user: str = Depends(get_current_user),
                 db: Session = Depends(database.get_db)):
    if not crud.get_repo(db, owner, repo):
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")
    issue = crud.update_issue(db, owner, repo, number, issue_in.model_dump(exclude_unset=True))
    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue #{number} not found")
    return issue


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

QUALIFIER_RE = re.compile(r"(\w+):([^\s]+)")

from pydantic import BaseModel as _BaseModel

class RepoSearchResult(_BaseModel):
    total_count: int
    items: list[RepoResponse]

class IssueSearchResult(_BaseModel):
    total_count: int
    items: list[IssueResponse]


@app.get("/search/repositories", response_model=RepoSearchResult, tags=["search"])
@limiter.limit("30/minute")
def search_repositories(
    request: Request,
    q: str = Query(min_length=1),
    sort: str = Query(default="stars", pattern="^(stars|updated|created|name)$"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    per_page: int = Query(default=30, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    db: Session = Depends(database.get_db),
):
    from orm_models import Repo as _Repo
    qry = db.query(_Repo).filter(_Repo.private.is_(False))
    for key, value in QUALIFIER_RE.findall(q):
        if key == "language":
            qry = qry.filter(_Repo.language.ilike(value))
        elif key == "stars" and value.startswith(">"):
            qry = qry.filter(_Repo.stargazers_count > int(value[1:]))
        elif key == "stars" and value.startswith("<"):
            qry = qry.filter(_Repo.stargazers_count < int(value[1:]))
    for kw in QUALIFIER_RE.sub("", q).split():
        qry = qry.filter((_Repo.name.ilike(f"%{kw}%")) | (_Repo.description.ilike(f"%{kw}%")))
    total = qry.with_entities(func.count(_Repo.id)).scalar()
    sort_col = {"stars": _Repo.stargazers_count, "updated": _Repo.updated_at,
                "created": _Repo.created_at, "name": _Repo.name}.get(sort, _Repo.stargazers_count)
    qry = qry.order_by(sort_col.asc() if order == "asc" else sort_col.desc())
    return {"total_count": total, "items": qry.offset((page - 1) * per_page).limit(per_page).all()}


@app.get("/search/issues", response_model=IssueSearchResult, tags=["search"])
@limiter.limit("30/minute")
def search_issues(
    request: Request,
    q: str = Query(min_length=1),
    sort: str = Query(default="created", pattern="^(created|updated)$"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    per_page: int = Query(default=30, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    db: Session = Depends(database.get_db),
):
    from orm_models import Issue as _Issue
    qry = db.query(_Issue)
    for key, value in QUALIFIER_RE.findall(q):
        if key == "is" and value in ("open", "closed"):
            qry = qry.filter(_Issue.state == value)
        elif key == "author":
            qry = qry.filter(_Issue.author.ilike(value))
    for kw in QUALIFIER_RE.sub("", q).split():
        qry = qry.filter((_Issue.title.ilike(f"%{kw}%")) | (_Issue.body.ilike(f"%{kw}%")))
    total = qry.with_entities(func.count(_Issue.id)).scalar()
    sort_col = {"created": _Issue.created_at, "updated": _Issue.updated_at}.get(sort, _Issue.created_at)
    qry = qry.order_by(sort_col.asc() if order == "asc" else sort_col.desc())
    return {"total_count": total, "items": qry.offset((page - 1) * per_page).limit(per_page).all()}
