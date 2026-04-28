"""Chapter 30: JSON:API formatted responses alongside plain JSON.

The server serves both formats. Send Accept: application/vnd.api+json
to get JSON:API; omit it for plain JSON.

Run: uvicorn main:app --reload
"""
import sys
sys.path.insert(0, ".")

from fastapi import FastAPI, HTTPException, Depends, Request, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
import orm_models, database, crud
from routers import users, repos, issues
from models import RepoResponse

orm_models.Base.metadata.create_all(bind=database.engine)

JSONAPI_CONTENT_TYPE = "application/vnd.api+json"

app = FastAPI(title="Mini-GitHub", version="1.0.0")

# Standard JSON endpoints
app.include_router(users.router)
app.include_router(repos.router)
app.include_router(issues.router)


# ---------------------------------------------------------------------------
# JSON:API document models
# ---------------------------------------------------------------------------

class ResourceObject(BaseModel):
    type: str
    id: str
    attributes: dict
    relationships: dict = {}
    links: dict = {}


class JsonApiDocument(BaseModel):
    data: ResourceObject | list[ResourceObject] | None = None
    errors: list[dict] | None = None
    meta: dict = {}
    links: dict = {}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def repo_to_resource(repo, request: Request) -> ResourceObject:
    return ResourceObject(
        type="repos",
        id=str(repo.id),
        attributes={
            "name": repo.name,
            "full_name": repo.full_name,
            "description": repo.description,
            "private": repo.private,
            "stargazers_count": repo.stargazers_count,
            "created_at": repo.created_at.isoformat(),
            "updated_at": repo.updated_at.isoformat(),
        },
        relationships={
            "owner": {
                "data": {"type": "users", "id": repo.owner},
                "links": {"related": f"/users/{repo.owner}"},
            }
        },
        links={"self": f"/repos/{repo.owner}/{repo.name}"},
    )


# ---------------------------------------------------------------------------
# JSON:API endpoints — separate URL prefix /jsonapi/
# ---------------------------------------------------------------------------

@app.get("/jsonapi/repos/{owner}/{repo}")
def get_repo_jsonapi(owner: str, repo: str, request: Request, response: Response,
                     db: Session = Depends(database.get_db)):
    r = crud.get_repo(db, owner, repo)
    if not r:
        response.status_code = 404
        response.headers["Content-Type"] = JSONAPI_CONTENT_TYPE
        return JsonApiDocument(errors=[{
            "status": "404", "title": "Not Found",
            "detail": f"Repository {owner}/{repo} not found",
        }])
    response.headers["Content-Type"] = JSONAPI_CONTENT_TYPE
    return JsonApiDocument(data=repo_to_resource(r, request))


@app.get("/jsonapi/users/{username}/repos")
def list_repos_jsonapi(username: str, request: Request, response: Response,
                       page: int = 1, per_page: int = 30,
                       db: Session = Depends(database.get_db)):
    if not crud.get_user(db, username):
        response.status_code = 404
        response.headers["Content-Type"] = JSONAPI_CONTENT_TYPE
        return JsonApiDocument(errors=[{"status": "404", "title": "Not Found"}])

    repos = crud.get_user_repos(db, username, skip=(page - 1) * per_page, limit=per_page)

    base = f"/jsonapi/users/{username}/repos"
    links: dict = {"self": f"{base}?page={page}"}
    if len(repos) == per_page:
        links["next"] = f"{base}?page={page + 1}"
    if page > 1:
        links["prev"] = f"{base}?page={page - 1}"
        links["first"] = f"{base}?page=1"

    response.headers["Content-Type"] = JSONAPI_CONTENT_TYPE
    return JsonApiDocument(
        data=[repo_to_resource(r, request) for r in repos],
        links=links,
    )
