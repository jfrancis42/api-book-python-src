from fastapi import APIRouter, HTTPException, Depends, Request, Response
from sqlalchemy.orm import Session
import sys; sys.path.insert(0, "..")
import database, crud
from models import RepoCreate, RepoUpdate, RepoResponse

router = APIRouter(tags=["repos"])


@router.get("/repos/{owner}/{repo}", response_model=RepoResponse, name="get_repo")
def get_repo(owner: str, repo: str, db: Session = Depends(database.get_db)):
    r = crud.get_repo(db, owner, repo)
    if not r:
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")
    return r


@router.post("/users/{username}/repos", response_model=RepoResponse, status_code=201)
def create_repo(username: str, repo_in: RepoCreate, request: Request, response: Response,
                db: Session = Depends(database.get_db)):
    if not crud.get_user(db, username):
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    if crud.get_repo(db, username, repo_in.name):
        raise HTTPException(status_code=409,
                            detail=f"Repository '{username}/{repo_in.name}' already exists")
    repo = crud.create_repo(db, owner=username, **repo_in.model_dump())
    response.headers["Location"] = str(
        request.url_for("get_repo", owner=username, repo=repo.name)
    )
    return repo


@router.patch("/repos/{owner}/{repo}", response_model=RepoResponse)
def update_repo(owner: str, repo: str, repo_in: RepoUpdate,
                db: Session = Depends(database.get_db)):
    if not crud.get_repo(db, owner, repo):
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")
    updates = repo_in.model_dump(exclude_unset=True)
    return crud.update_repo(db, owner, repo, updates)


@router.delete("/repos/{owner}/{repo}", status_code=204)
def delete_repo(owner: str, repo: str, db: Session = Depends(database.get_db)):
    if not crud.delete_repo(db, owner, repo):
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")
