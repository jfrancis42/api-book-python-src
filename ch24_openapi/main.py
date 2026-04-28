"""Chapter 22: FastAPI with customized OpenAPI schema.

Run:  uvicorn main:app --reload
Docs: http://localhost:8000/docs
Schema: http://localhost:8000/openapi.json
"""
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="Mini-GitHub API",
    version="1.0.0",
    description="""
A GitHub-compatible REST API for learning.

## Resources

- **Users** — developer accounts
- **Repos** — source code repositories
""",
    contact={"name": "API Support", "email": "api@example.com"},
    license_info={"name": "MIT"},
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    detail: str

    model_config = {"json_schema_extra": {"example": {"detail": "User 'nobody' not found"}}}


class UserCreate(BaseModel):
    login: str = Field(..., min_length=1, max_length=39,
                       examples=["octocat"],
                       description="The user's login handle (unique).")
    name: Optional[str] = Field(default=None, examples=["The Octocat"])

    model_config = {
        "json_schema_extra": {
            "example": {"login": "octocat", "name": "The Octocat"}
        }
    }


class UserResponse(BaseModel):
    login: str = Field(examples=["octocat"])
    name: Optional[str] = Field(default=None, examples=["The Octocat"])
    public_repos: int = Field(default=0, examples=[8])

    model_config = {"from_attributes": True}


# In-memory store for demo purposes
_users: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Endpoints with full OpenAPI metadata
# ---------------------------------------------------------------------------

@app.get(
    "/users/{username}",
    response_model=UserResponse,
    summary="Get a user",
    description="Returns the public profile of a user identified by their login name.",
    response_description="The user's public profile.",
    responses={
        404: {
            "description": "User not found",
            "model": ErrorResponse,
        }
    },
    tags=["users"],
    operation_id="get_user",
)
def get_user(username: str):
    if username not in _users:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    return _users[username]


@app.post(
    "/users",
    response_model=UserResponse,
    status_code=201,
    summary="Create a user",
    description="Creates a new user. The login must be unique.",
    responses={
        409: {
            "description": "Login already taken",
            "model": ErrorResponse,
        },
        422: {"description": "Validation error"},
    },
    tags=["users"],
    operation_id="create_user",
)
def create_user(user_in: UserCreate, request: Request):
    if user_in.login in _users:
        raise HTTPException(status_code=409, detail=f"User '{user_in.login}' already exists")
    _users[user_in.login] = {"login": user_in.login, "name": user_in.name, "public_repos": 0}
    return _users[user_in.login]


@app.get(
    "/health",
    summary="Health check",
    include_in_schema=False,   # hidden from public docs
)
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Explore the generated schema
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    import urllib.request

    url = "http://localhost:8000/openapi.json"
    with urllib.request.urlopen(url) as r:
        schema = json.loads(r.read())

    print("=== Endpoints ===")
    for path, methods in schema["paths"].items():
        for method in methods:
            op = methods[method]
            print(f"  {method.upper():6} {path}  ({op.get('operationId', '?')})")

    print("\n=== Schemas ===")
    for name in schema.get("components", {}).get("schemas", {}):
        print(f"  {name}")
