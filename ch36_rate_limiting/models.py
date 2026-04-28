"""Chapter 28: Pydantic models including Update (PATCH) variants."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

VALID_LANGUAGES = {
    "Python", "JavaScript", "TypeScript", "Go", "Rust",
    "C", "C++", "Java", "Ruby", "PHP", None,
}


# ---------------------------------------------------------------------------
# User models
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    login: str = Field(min_length=1, max_length=39,
                       pattern=r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$")
    name: Optional[str] = Field(default=None, max_length=255)
    bio: Optional[str] = Field(default=None, max_length=160)
    email: Optional[str] = None

    @field_validator("login")
    @classmethod
    def login_not_reserved(cls, v):
        if v.lower() in {"admin", "root", "api", "www", "git"}:
            raise ValueError(f"'{v}' is a reserved username")
        return v.lower()


class UserUpdate(BaseModel):
    """All fields optional — only provided fields are updated."""
    name: Optional[str] = Field(default=None, max_length=255)
    bio: Optional[str] = Field(default=None, max_length=160)
    email: Optional[str] = None


class UserResponse(BaseModel):
    login: str
    id: int
    name: Optional[str] = None
    bio: Optional[str] = None
    email: Optional[str] = None
    public_repos: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Repository models
# ---------------------------------------------------------------------------

class RepoCreate(BaseModel):
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


class RepoUpdate(BaseModel):
    description: Optional[str] = Field(default=None, max_length=350)
    language: Optional[str] = None
    private: Optional[bool] = None

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


class IssueUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    body: Optional[str] = Field(default=None, max_length=65536)
    state: Optional[str] = Field(default=None, pattern="^(open|closed)$")
    labels: Optional[list[str]] = None


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
