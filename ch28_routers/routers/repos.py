from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import sys; sys.path.insert(0, "..")
import database, crud
from models import RepoCreate, RepoResponse

router = APIRouter(tags=["repos"])


@router.get("/repos/{owner}/{repo}", response_model=RepoResponse)
def get_repo(owner: str, repo: str, db: Session = Depends(database.get_db)):
    r = crud.get_repo(db, owner, repo)
    if not r:
        raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found")
    return r


@router.post("/users/{username}/repos", response_model=RepoResponse, status_code=201)
def create_repo(username: str, repo_in: RepoCreate, db: Session = Depends(database.get_db)):
    if not crud.get_user(db, username):
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    if crud.get_repo(db, username, repo_in.name):
        raise HTTPException(status_code=422, detail=f"Repository '{username}/{repo_in.name}' already exists")
    return crud.create_repo(db, owner=username, **repo_in.model_dump())
