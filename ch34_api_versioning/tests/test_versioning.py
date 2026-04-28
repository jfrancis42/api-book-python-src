import sys
sys.path.insert(0, "..")

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_users():
    from routers.v1 import _users
    _users.clear()
    yield
    _users.clear()


def test_v1_create_and_get():
    r = client.post("/v1/users", json={"login": "octocat", "name": "The Octocat"})
    assert r.status_code == 201
    data = r.json()
    assert data["login"] == "octocat"
    assert data["name"] == "The Octocat"

    r = client.get("/v1/users/octocat")
    assert r.status_code == 200
    assert r.json()["login"] == "octocat"


def test_v2_create_and_get():
    r = client.post("/v2/users",
                    json={"handle": "hubot", "display_name": "Hubot"})
    assert r.status_code == 201
    data = r.json()
    assert data["handle"] == "hubot"
    assert data["display_name"] == "Hubot"
    assert "login" not in data

    r = client.get("/v2/users/hubot")
    assert r.status_code == 200
    assert r.json()["handle"] == "hubot"


def test_v1_user_visible_in_v2():
    client.post("/v1/users", json={"login": "octocat", "name": "The Octocat"})
    r = client.get("/v2/users/octocat")
    assert r.status_code == 200
    data = r.json()
    assert data["handle"] == "octocat"
    assert data["display_name"] == "The Octocat"


def test_v1_response_has_v1_fields_only():
    client.post("/v1/users", json={"login": "octocat", "name": "The Octocat"})
    data = client.get("/v1/users/octocat").json()
    assert "login" in data
    assert "name" in data
    assert "handle" not in data
    assert "display_name" not in data


def test_v2_response_has_v2_fields_only():
    client.post("/v2/users", json={"handle": "hubot", "display_name": "Hubot"})
    data = client.get("/v2/users/hubot").json()
    assert "handle" in data
    assert "display_name" in data
    assert "login" not in data
    assert "name" not in data


def test_v1_404():
    assert client.get("/v1/users/nobody").status_code == 404


def test_v2_404():
    assert client.get("/v2/users/nobody").status_code == 404


def test_v1_duplicate_returns_409():
    client.post("/v1/users", json={"login": "octocat", "name": "The Octocat"})
    r = client.post("/v1/users", json={"login": "octocat", "name": "Other"})
    assert r.status_code == 409


def test_v1_deprecation_headers_present():
    client.post("/v1/users", json={"login": "octocat", "name": "The Octocat"})
    r = client.get("/v1/users/octocat")
    assert r.headers.get("Deprecation") == "true"
    assert "Sunset" in r.headers


def test_v2_no_deprecation_headers():
    client.post("/v2/users", json={"handle": "hubot", "display_name": "Hubot"})
    r = client.get("/v2/users/hubot")
    assert "Deprecation" not in r.headers
