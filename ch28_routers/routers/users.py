from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import sys; sys.path.insert(0, "..")
import database, crud
from models import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
def list_users(skip: int = 0, limit: int = 30, db: Session = Depends(database.get_db)):
    return crud.get_users(db, skip=skip, limit=limit)


@router.post("", response_model=UserResponse, status_code=201)
def create_user(user_in: UserCreate, db: Session = Depends(database.get_db)):
    if crud.get_user(db, user_in.login):
        raise HTTPException(status_code=422, detail=f"User '{user_in.login}' already exists")
    return crud.create_user(db, **user_in.model_dump())


@router.get("/{username}", response_model=UserResponse)
def get_user(username: str, db: Session = Depends(database.get_db)):
    user = crud.get_user(db, username)
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    return user


@router.get("/{username}/repos")
def list_user_repos(username: str, db: Session = Depends(database.get_db)):
    if not crud.get_user(db, username):
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    return crud.get_user_repos(db, username)
