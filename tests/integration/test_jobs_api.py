"""Integration tests for the jobs router."""

from __future__ import annotations

import pytest


def test_list_jobs_empty(client, auth_headers):
    r = client.get("/api/v1/jobs", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["items"] == []


def test_get_missing_job_404(client, auth_headers):
    r = client.get("/api/v1/jobs/9999", headers=auth_headers)
    assert r.status_code == 404


def test_cancel_job(client, auth_headers):
    list_create = client.post(
        "/api/v1/lists", headers=auth_headers,
        json={"name": "x", "source_type": "manual"},
    ).json()
    sync = client.post(
        f"/api/v1/lists/{list_create['id']}/sync", headers=auth_headers
    )
    job_id = sync.json()["job_id"]
    r = client.post(f"/api/v1/jobs/{job_id}/cancel", headers=auth_headers)
    assert r.status_code == 200
    fetched = client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers).json()
    assert fetched["state"] == "cancelled"
