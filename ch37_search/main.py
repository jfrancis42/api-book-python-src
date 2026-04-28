"""Chapter 34: Search endpoints.

Run: uvicorn main:app --reload
Try: GET /search/repositories?q=language:python
     GET /search/repositories?q=stars:>5
     GET /search/issues?q=is:open
"""
import sys
sys.path.insert(0, ".")

import re
from fastapi import FastAPI, HTTPException, Depends, Request, Response, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel
import orm_models, database, crud
from auth import get_current_user
from models import (UserCreate, UserResponse, RepoCreate, RepoResponse,
                    IssueCreate, IssueResponse)

orm_models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Mini-GitHub", version="1.4.0")


# ---------------------------------------------------------------------------
# Search result model
# ---------------------------------------------------------------------------

class SearchResult(BaseModel):
    total_count: int
    items: list[RepoResponse] | list[IssueResponse]


class RepoSearchResult(BaseModel):
    total_count: int
    items: list[RepoResponse]


class IssueSearchResult(BaseModel):
    total_count: int
    items: list[IssueResponse]


# ---------------------------------------------------------------------------
# Search CRUD
# ---------------------------------------------------------------------------

QUALIFIER_RE = re.compile(r"(\w+):([^\s]+)")


def search_repos(db: Session, query: str, sort: str = "stars",
                 order: str = "desc", skip: int = 0, limit: int = 30):
    from orm_models import Repo
    q = db.query(Repo).filter(Repo.private.is_(False))

    qualifiers = QUALIFIER_RE.findall(query)
    keywords = QUALIFIER_RE.sub("", query).split()

    for key, value in qualifiers:
        if key == "language":
            q = q.filter(Repo.language.ilike(value))
        elif key == "stars" and value.startswith(">"):
            q = q.filter(Repo.stargazers_count > int(value[1:]))
        elif key == "stars" and value.startswith("<"):
            q = q.filter(Repo.stargazers_count < int(value[1:]))

    for kw in keywords:
        q = q.filter(
            (Repo.name.ilike(f"%{kw}%")) | (Repo.description.ilike(f"%{kw}%"))
        )

    total = q.with_entities(func.count(Repo.id)).scalar()

    sort_col = {"stars": Repo.stargazers_count, "updated": Repo.updated_at,
                "created": Repo.created_at, "name": Repo.name}.get(sort, Repo.stargazers_count)
    q = q.order_by(sort_col.asc() if order == "asc" else sort_col.desc())
    return q.offset(skip).limit(limit).all(), total


def search_issues(db: Session, query: str, sort: str = "created",
                  order: str = "desc", skip: int = 0, limit: int = 30):
    from orm_models import Issue
    q = db.query(Issue)

    qualifiers = QUALIFIER_RE.findall(query)
    keywords = QUALIFIER_RE.sub("", query).split()

    for key, value in qualifiers:
        if key == "is" and value in ("open", "closed"):
            q = q.filter(Issue.state == value)
        elif key == "author":
            q = q.filter(Issue.author.ilike(value))

    for kw in keywords:
        q = q.filter(
            (Issue.title.ilike(f"%{kw}%")) | (Issue.body.ilike(f"%{kw}%"))
        )

    total = q.with_entities(func.count(Issue.id)).scalar()
    sort_col = {"created": Issue.created_at, "updated": Issue.updated_at}.get(sort, Issue.created_at)
    q = q.order_by(sort_col.asc() if order == "asc" else sort_col.desc())
    return q.offset(skip).limit(limit).all(), total


# ---------------------------------------------------------------------------
# Search endpoints
# ---------------------------------------------------------------------------

@app.get("/search/repositories", response_model=RepoSearchResult, tags=["search"])
def search_repositories(
    q: str = Query(min_length=1, description="Search query"),
    sort: str = Query(default="stars", pattern="^(stars|forks|updated|created|name)$"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    per_page: int = Query(default=30, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    db: Session = Depends(database.get_db),
):
    results, total = search_repos(db, q, sort=sort, order=order,
                                  skip=(page - 1) * per_page, limit=per_page)
    return {"total_count": total, "items": results}


@app.get("/search/issues", response_model=IssueSearchResult, tags=["search"])
def search_issues_endpoint(
    q: str = Query(min_length=1),
    sort: str = Query(default="created", pattern="^(created|updated)$"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    per_page: int = Query(default=30, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    db: Session = Depends(database.get_db),
):
    results, total = search_issues(db, q, sort=sort, order=order,
                                   skip=(page - 1) * per_page, limit=per_page)
    return {"total_count": total, "items": results}


# ---------------------------------------------------------------------------
# Standard CRUD (abbreviated — see ch32_auth for full version)
# ---------------------------------------------------------------------------

@app.post("/users", response_model=UserResponse, status_code=201, tags=["users"])
def create_user(user_in: UserCreate, request: Request, response: Response,
                db: Session = Depends(database.get_db)):
    if crud.get_user(db, user_in.login):
        raise HTTPException(status_code=409, detail=f"User '{user_in.login}' already exists")
    user = crud.create_user(db, **user_in.model_dump())
    return user


@app.get("/users/{username}", response_model=UserResponse, name="get_user", tags=["users"])
def get_user(username: str, db: Session = Depends(database.get_db)):
    user = crud.get_user(db, username)
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    return user


@app.post("/users/{username}/repos", response_model=RepoResponse, status_code=201, tags=["repos"])
def create_repo(username: str, repo_in: RepoCreate, request: Request, response: Response,
                db: Session = Depends(database.get_db)):
    if not crud.get_user(db, username):
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    if crud.get_repo(db, username, repo_in.name):
        raise HTTPException(status_code=409,
                            detail=f"Repository '{username}/{repo_in.name}' already exists")
    return crud.create_repo(db, owner=username, **repo_in.model_dump())


@app.get("/repos/{owner}/{repo}", response_model=RepoResponse, name="get_repo", tags=["repos"])
def get_repo(owner: str, repo: str, db: Session = Depends(database.get_db)):
    r = crud.get_repo(db, owner, repo)
    if not r:
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")
    return r


@app.post("/repos/{owner}/{repo}/issues", response_model=IssueResponse,
          status_code=201, name="create_issue", tags=["issues"])
def create_issue(owner: str, repo: str, issue_in: IssueCreate,
                 request: Request, response: Response,
                 db: Session = Depends(database.get_db)):
    if not crud.get_repo(db, owner, repo):
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")
    return crud.create_issue(db, owner=owner, repo=repo, author="anonymous",
                             title=issue_in.title, body=issue_in.body, labels=issue_in.labels)


@app.get("/repos/{owner}/{repo}/issues/{number}", response_model=IssueResponse,
         name="get_issue", tags=["issues"])
def get_issue(owner: str, repo: str, number: int, db: Session = Depends(database.get_db)):
    issue = crud.get_issue(db, owner, repo, number)
    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue #{number} not found")
    return issue
