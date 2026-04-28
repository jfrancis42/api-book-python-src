"""Chapter 23: Pydantic models for request and response."""
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# User models
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    """Request body for creating a user."""
    login: str = Field(min_length=1, max_length=39, pattern=r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$")
    name: Optional[str] = Field(default=None, max_length=255)
    bio: Optional[str] = Field(default=None, max_length=160)
    email: Optional[str] = Field(default=None)

    @field_validator("login")
    @classmethod
    def login_not_reserved(cls, v: str) -> str:
        reserved = {"admin", "root", "api", "www", "git"}
        if v.lower() in reserved:
            raise ValueError(f"'{v}' is a reserved username")
        return v.lower()


class UserResponse(BaseModel):
    login: str
    id: int
    name: Optional[str] = None
    bio: Optional[str] = None
    email: Optional[str] = None
    public_repos: int = 0
    followers: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Repository models
# ---------------------------------------------------------------------------

VALID_LANGUAGES = {
    "Python", "JavaScript", "TypeScript", "Go", "Rust",
    "C", "C++", "Java", "Ruby", "PHP", None,
}

class RepoCreate(BaseModel):
    """Request body for creating a repository."""
    name: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9._-]+$")
    description: Optional[str] = Field(default=None, max_length=350)
    language: Optional[str] = None
    private: bool = False

    @field_validator("language")
    @classmethod
    def language_must_be_known(cls, v):
        if v is not None and v not in VALID_LANGUAGES:
            raise ValueError(f"Unknown language '{v}'")
        return v


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


# ---------------------------------------------------------------------------
# Issue models
# ---------------------------------------------------------------------------

class IssueCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(default="", max_length=65536)
    labels: list[str] = Field(default_factory=list)


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
