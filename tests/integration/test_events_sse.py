"""Integration tests for the SSE /events endpoint."""

from __future__ import annotations


def test_events_endpoint_requires_auth(client):
    """No bearer token => 401 (router auth dependency works)."""
    r = client.get("/api/v1/events", headers={"Host": "localhost"})
    assert r.status_code == 401


def test_events_endpoint_registered_in_openapi(client, auth_headers):
    """Route is mounted at /api/v1/events.

    NOTE: live consumption of the SSE stream is brittle under TestClient +
    EventSourceResponse (the generator holds the connection open and the
    test never sees an end-of-stream). Bus pub/sub is covered in
    tests/unit/core/test_events.py; here we only verify the route exists.
    """
    spec = client.get("/api/openapi.json", headers=auth_headers).json()
    assert "/api/v1/events" in spec.get("paths", {})
