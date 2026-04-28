"""Mini-GitHub API — Chapter 42: Observability demo."""
import time
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from logging_config import configure_logging
from middleware import RequestLoggingMiddleware
from metrics import metrics

configure_logging()

app = FastAPI(title="Mini-GitHub API — with observability")
app.add_middleware(RequestLoggingMiddleware)

_start_time = time.time()
_users: dict[str, dict] = {}


class UserCreate(BaseModel):
    login: str
    name: str


@app.post("/users", status_code=201)
def create_user(user_in: UserCreate):
    _users[user_in.login] = {"login": user_in.login, "name": user_in.name}
    return _users[user_in.login]


@app.get("/users/{login}")
def get_user(login: str):
    if login not in _users:
        return JSONResponse({"detail": "not found"}, status_code=404)
    return _users[login]


@app.get("/health", include_in_schema=False)
def health_check():
    return JSONResponse({
        "status": "ok",
        "uptime_s": int(time.time() - _start_time),
    })


@app.get("/metrics", include_in_schema=False)
def get_metrics():
    return metrics.summary()
