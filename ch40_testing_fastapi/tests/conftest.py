"""Shared fixtures for the Mini-GitHub test suite (Chapter 36)."""
import sys
sys.path.insert(0, "..")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
import database
from orm_models import Base

# StaticPool forces all connections to share the same in-memory database.
# Without it, each new connection gets a fresh empty database.
_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestingSession = sessionmaker(bind=_engine)


def override_get_db():
    db = _TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[database.get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_db():
    """Drop and recreate all tables before each test."""
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def octocat(client):
    """A pre-created user."""
    client.post("/users", json={"login": "octocat", "name": "The Octocat"})
    return "octocat"


@pytest.fixture
def hello_repo(client, octocat):
    """A pre-created repo owned by octocat."""
    client.post(
        "/users/octocat/repos",
        json={"name": "hello-world", "description": "My first repo"},
        headers={"Authorization": "Bearer test-token-octocat"},
    )
    return ("octocat", "hello-world")
