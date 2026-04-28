from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from routers.v1 import _users

router = APIRouter(tags=["v2"])


class UserV2(BaseModel):
    handle: str
    display_name: str
    public_repos: int = 0


class UserCreateV2(BaseModel):
    handle: str
    display_name: str


def _to_v2(raw: dict) -> dict:
    return {
        "handle": raw["login"],
        "display_name": raw["name"],
        "public_repos": raw["public_repos"],
    }


@router.post("/users", response_model=UserV2, status_code=201)
def create_user_v2(user_in: UserCreateV2):
    if user_in.handle in _users:
        raise HTTPException(409, f"User '{user_in.handle}' already exists")
    _users[user_in.handle] = {
        "login": user_in.handle,
        "name": user_in.display_name,
        "public_repos": 0,
    }
    return _to_v2(_users[user_in.handle])


@router.get("/users/{handle}", response_model=UserV2)
def get_user_v2(handle: str):
    if handle not in _users:
        raise HTTPException(404, f"User '{handle}' not found")
    return _to_v2(_users[handle])
