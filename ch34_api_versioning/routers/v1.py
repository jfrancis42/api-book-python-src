from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

router = APIRouter(tags=["v1"])

_users: dict[str, dict] = {}


class UserV1(BaseModel):
    login: str
    name: str
    public_repos: int = 0


class UserCreateV1(BaseModel):
    login: str
    name: str


@router.post("/users", response_model=UserV1, status_code=201)
def create_user_v1(user_in: UserCreateV1):
    if user_in.login in _users:
        raise HTTPException(409, f"User '{user_in.login}' already exists")
    _users[user_in.login] = {
        "login": user_in.login,
        "name": user_in.name,
        "public_repos": 0,
    }
    return _users[user_in.login]


@router.get("/users/{login}", response_model=UserV1)
def get_user_v1(login: str, response: Response):
    if login not in _users:
        raise HTTPException(404, f"User '{login}' not found")
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "Sat, 01 Jan 2028 00:00:00 GMT"
    response.headers["Link"] = f'</v2/users/{login}>; rel="successor-version"'
    return _users[login]
