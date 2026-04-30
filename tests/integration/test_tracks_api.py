"""Integration tests for the tracks router."""

from __future__ import annotations

import asyncio


def test_list_tracks_for_list(client, auth_headers, session_factory):
    r = client.post(
        "/api/v1/lists", headers=auth_headers,
        json={"name": "x", "source_type": "manual"},
    )
    assert r.status_code == 201
    list_id = r.json()["id"]
    r = client.get(f"/api/v1/lists/{list_id}/tracks", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["items"] == []


def test_track_skip_marks_status(client, auth_headers, session_factory):
    from toolcrate.db.models import TrackEntry

    create = client.post(
        "/api/v1/lists", headers=auth_headers,
        json={"name": "x", "source_type": "manual"},
    ).json()

    async def seed():
        async with session_factory() as session:
            t = TrackEntry(
                source_list_id=create["id"], position=1, artist="A", title="B"
            )
            session.add(t)
            await session.commit()
            await session.refresh(t)
            return t.id

    track_id = asyncio.run(seed())

    r = client.post(
        f"/api/v1/lists/{create['id']}/tracks/{track_id}/skip",
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["download_status"] == "skipped"
