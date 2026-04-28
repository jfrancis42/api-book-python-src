"""Tests for repo endpoints including auth and pagination (Chapter 36)."""

AUTH = {"Authorization": "Bearer test-token-octocat"}
WRONG_AUTH = {"Authorization": "Bearer test-token-hubot"}


def test_create_repo(client, octocat):
    r = client.post("/users/octocat/repos",
                    json={"name": "hello-world"}, headers=AUTH)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "hello-world"
    assert data["full_name"] == "octocat/hello-world"
    assert "Location" in r.headers


def test_create_repo_no_auth(client, octocat):
    r = client.post("/users/octocat/repos", json={"name": "hello-world"})
    assert r.status_code == 401


def test_create_repo_wrong_user(client, octocat):
    client.post("/users", json={"login": "hubot", "name": "Hubot"})
    r = client.post("/users/hubot/repos",
                    json={"name": "secret"}, headers=AUTH)
    assert r.status_code == 403


def test_create_duplicate_repo(client, hello_repo):
    r = client.post("/users/octocat/repos",
                    json={"name": "hello-world"}, headers=AUTH)
    assert r.status_code == 409


def test_get_repo(client, hello_repo):
    r = client.get("/repos/octocat/hello-world")
    assert r.status_code == 200
    assert r.json()["full_name"] == "octocat/hello-world"


def test_get_missing_repo(client):
    r = client.get("/repos/octocat/nonexistent")
    assert r.status_code == 404


def test_delete_repo(client, hello_repo):
    r = client.delete("/repos/octocat/hello-world", headers=AUTH)
    assert r.status_code == 204
    assert client.get("/repos/octocat/hello-world").status_code == 404


def test_delete_repo_wrong_user(client, hello_repo):
    r = client.delete("/repos/octocat/hello-world", headers=WRONG_AUTH)
    assert r.status_code == 403


def test_pagination_link_header(client, octocat):
    for i in range(5):
        client.post(f"/users/octocat/repos",
                    json={"name": f"repo-{i}"}, headers=AUTH)
    r = client.get("/users/octocat/repos?per_page=2")
    assert r.status_code == 200
    assert len(r.json()) == 2
    assert r.headers["X-Total-Count"] == "5"
    assert 'rel="next"' in r.headers["Link"]
    assert 'rel="last"' in r.headers["Link"]


def test_pagination_last_page(client, octocat):
    for i in range(5):
        client.post(f"/users/octocat/repos",
                    json={"name": f"repo-{i}"}, headers=AUTH)
    r = client.get("/users/octocat/repos?per_page=2&page=3")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert 'rel="next"' not in r.headers.get("Link", "")
