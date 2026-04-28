"""Chapter 37: FastAPI with async SQLAlchemy and PostgreSQL.

Requires: pip install asyncpg sqlalchemy[asyncio]
Run:      DATABASE_URL=postgresql+asyncpg://... uvicorn main:app --reload
"""
from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, field_validator

import crud
from database import engine, get_db
from orm_models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Mini-GitHub (async)", version="2.0.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Pydantic models (inline for self-contained demo)
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    login: str = Field(min_length=1, max_length=39)
    name: Optional[str] = None

    @field_validator("login")
    @classmethod
    def login_not_reserved(cls, v):
        if v.lower() in {"admin", "root", "api"}:
            raise ValueError(f"'{v}' is reserved")
        return v.lower()


class UserResponse(BaseModel):
    id: int
    login: str
    name: Optional[str] = None
    public_repos: int = 0
    created_at: datetime
    model_config = {"from_attributes": True}


class RepoCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    language: Optional[str] = None
    private: bool = False


class RepoResponse(BaseModel):
    id: int
    name: str
    full_name: str
    owner: str
    description: Optional[str] = None
    language: Optional[str] = None
    private: bool = False
    stargazers_count: int = 0
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class IssueCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str = ""
    labels: list[str] = []


class IssueResponse(BaseModel):
    id: int
    number: int
    title: str
    body: str
    state: str
    owner: str
    repo: str
    author: str
    labels: list[str]
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Async endpoints
# ---------------------------------------------------------------------------

@app.post("/users", response_model=UserResponse, status_code=201, tags=["users"])
async def create_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    if await crud.get_user(db, user_in.login):
        raise HTTPException(status_code=409, detail=f"User '{user_in.login}' already exists")
    return await crud.create_user(db, login=user_in.login, name=user_in.name)


@app.get("/users/{username}", response_model=UserResponse, tags=["users"])
async def get_user(username: str, db: AsyncSession = Depends(get_db)):
    user = await crud.get_user(db, username)
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    return user


@app.get("/users/{username}/repos", response_model=list[RepoResponse], tags=["repos"])
async def list_user_repos(username: str, db: AsyncSession = Depends(get_db)):
    if not await crud.get_user(db, username):
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    return await crud.get_user_repos(db, username)


@app.post("/users/{username}/repos", response_model=RepoResponse,
          status_code=201, tags=["repos"])
async def create_repo(username: str, repo_in: RepoCreate, db: AsyncSession = Depends(get_db)):
    if not await crud.get_user(db, username):
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    if await crud.get_repo(db, username, repo_in.name):
        raise HTTPException(status_code=409,
                            detail=f"Repository '{username}/{repo_in.name}' already exists")
    return await crud.create_repo(db, owner=username, **repo_in.model_dump())


@app.get("/repos/{owner}/{repo}", response_model=RepoResponse, tags=["repos"])
async def get_repo(owner: str, repo: str, db: AsyncSession = Depends(get_db)):
    r = await crud.get_repo(db, owner, repo)
    if not r:
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")
    return r


@app.get("/repos/{owner}/{repo}/issues", response_model=list[IssueResponse], tags=["issues"])
async def list_issues(owner: str, repo: str, state: str = "open",
                      db: AsyncSession = Depends(get_db)):
    if not await crud.get_repo(db, owner, repo):
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")
    return await crud.get_repo_issues(db, owner, repo, state=state)


@app.post("/repos/{owner}/{repo}/issues", response_model=IssueResponse,
          status_code=201, tags=["issues"])
async def create_issue(owner: str, repo: str, issue_in: IssueCreate,
                       db: AsyncSession = Depends(get_db)):
    if not await crud.get_repo(db, owner, repo):
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")
    return await crud.create_issue(db, owner=owner, repo=repo, author="anonymous",
                                   title=issue_in.title, body=issue_in.body,
                                   labels=issue_in.labels)


@app.get("/health")
async def health():
    return {"status": "ok"}
