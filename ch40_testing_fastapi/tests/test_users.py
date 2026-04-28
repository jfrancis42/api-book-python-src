"""Tests for user endpoints (Chapter 36)."""


def test_create_user(client):
    r = client.post("/users", json={"login": "octocat", "name": "The Octocat"})
    assert r.status_code == 201
    data = r.json()
    assert data["login"] == "octocat"
    assert data["name"] == "The Octocat"
    assert data["public_repos"] == 0
    assert "Location" in r.headers
    assert "/users/octocat" in r.headers["Location"]


def test_create_duplicate_user(client, octocat):
    r = client.post("/users", json={"login": "octocat", "name": "Other"})
    assert r.status_code == 409


def test_get_user(client, octocat):
    r = client.get("/users/octocat")
    assert r.status_code == 200
    assert r.json()["login"] == "octocat"


def test_get_missing_user(client):
    r = client.get("/users/nobody")
    assert r.status_code == 404
    assert "nobody" in r.json()["detail"]


def test_reserved_login(client):
    r = client.post("/users", json={"login": "admin"})
    assert r.status_code == 422


def test_invalid_login_pattern(client):
    r = client.post("/users", json={"login": "has space"})
    assert r.status_code == 422
