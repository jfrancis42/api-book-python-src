"""Chapter 24: Mini-GitHub with SQLAlchemy database backend.

Run:
    uvicorn main:app --reload

First run creates minigithub.db automatically.
"""
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

import database
import orm_models
import crud

# Create tables on startup
orm_models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Mini-GitHub", version="0.4.0")


# ---------------------------------------------------------------------------
# Pydantic models (inline for self-contained chapter)
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    login: str = Field(min_length=1, max_length=39)
    name: Optional[str] = None
    bio: Optional[str] = None
    email: Optional[str] = None

    @field_validator("login")
    @classmethod
    def normalize_login(cls, v):
        return v.lower()


class UserResponse(BaseModel):
    login: str
    id: int
    name: Optional[str] = None
    bio: Optional[str] = None
    public_repos: int
    followers: int
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
    private: bool
    stargazers_count: int
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/users/{username}", response_model=UserResponse)
def get_user(username: str, db: Session = Depends(database.get_db)):
    user = crud.get_user(db, username)
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    return user


@app.get("/users", response_model=list[UserResponse])
def list_users(skip: int = 0, limit: int = 30, db: Session = Depends(database.get_db)):
    return crud.get_users(db, skip=skip, limit=limit)


@app.post("/users", response_model=UserResponse, status_code=201)
def create_user(user_in: UserCreate, db: Session = Depends(database.get_db)):
    existing = crud.get_user(db, user_in.login)
    if existing:
        raise HTTPException(status_code=422, detail=f"User '{user_in.login}' already exists")
    return crud.create_user(db, **user_in.model_dump())


@app.get("/users/{username}/repos", response_model=list[RepoResponse])
def list_user_repos(username: str, db: Session = Depends(database.get_db)):
    if not crud.get_user(db, username):
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    return crud.get_user_repos(db, username)


@app.get("/repos/{owner}/{repo}", response_model=RepoResponse)
def get_repo(owner: str, repo: str, db: Session = Depends(database.get_db)):
    r = crud.get_repo(db, owner, repo)
    if not r:
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")
    return r


@app.post("/users/{username}/repos", response_model=RepoResponse, status_code=201)
def create_repo(username: str, repo_in: RepoCreate, db: Session = Depends(database.get_db)):
    if not crud.get_user(db, username):
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    if crud.get_repo(db, username, repo_in.name):
        raise HTTPException(status_code=422, detail=f"Repository '{username}/{repo_in.name}' already exists")
    return crud.create_repo(db, owner=username, **repo_in.model_dump())
