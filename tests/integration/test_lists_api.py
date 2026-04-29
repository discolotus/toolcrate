"""Integration tests for /lists CRUD endpoints."""


def test_create_spotify_list_via_paste_url(client, auth_headers):
    r = client.post("/api/v1/lists",
                    headers=auth_headers,
                    json={"name": "Late Night",
                          "source_url": "https://open.spotify.com/playlist/abc123"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["source_type"] == "spotify_playlist"
    assert body["external_id"] == "abc123"


def test_list_returns_created(client, auth_headers):
    client.post("/api/v1/lists", headers=auth_headers,
                json={"name": "x", "source_type": "manual"})
    r = client.get("/api/v1/lists", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1


def test_get_missing_returns_404(client, auth_headers):
    r = client.get("/api/v1/lists/9999", headers=auth_headers)
    assert r.status_code == 404


def test_patch_updates_field(client, auth_headers):
    create = client.post("/api/v1/lists", headers=auth_headers,
                         json={"name": "x", "source_type": "manual"}).json()
    r = client.patch(f"/api/v1/lists/{create['id']}", headers=auth_headers,
                     json={"name": "renamed"})
    assert r.status_code == 200
    assert r.json()["name"] == "renamed"


def test_delete_removes_list(client, auth_headers):
    create = client.post("/api/v1/lists", headers=auth_headers,
                         json={"name": "x", "source_type": "manual"}).json()
    r = client.delete(f"/api/v1/lists/{create['id']}", headers=auth_headers)
    assert r.status_code == 204
    r = client.get(f"/api/v1/lists/{create['id']}", headers=auth_headers)
    assert r.status_code == 404


def test_unauthorized_request_rejected(client):
    r = client.get("/api/v1/lists", headers={"Host": "localhost"})
    assert r.status_code == 401
