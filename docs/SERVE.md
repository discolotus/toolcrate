# `toolcrate serve` — backend daemon (Phase 1)

`toolcrate serve` runs a FastAPI app on localhost. It is the source of
truth for source lists, jobs, schedules, and downloads. It does **not**
replace the existing `toolcrate sldl` / `toolcrate shazam-tool` CLI
commands — those keep working as before.

## First run

1. Migrate any existing flat-file state into the DB:
   ```bash
   uv run toolcrate migrate
   ```
2. Start the daemon:
   ```bash
   uv run toolcrate serve
   ```
3. Note the API token printed on first start. It is also saved to
   `~/.config/toolcrate/api-token` (mode 0600).

## Endpoints

All endpoints are under `/api/v1/`. Browse them at
`http://127.0.0.1:48721/api/docs`.

| Method | Path                                       | Purpose                              |
|--------|--------------------------------------------|--------------------------------------|
| GET    | `/api/v1/health`                           | unauthenticated liveness             |
| GET    | `/api/v1/info`                             | version, paths                       |
| GET    | `/api/v1/lists`                            | list all source lists                |
| POST   | `/api/v1/lists`                            | create from URL or manual            |
| PATCH  | `/api/v1/lists/{id}`                       | update fields                        |
| DELETE | `/api/v1/lists/{id}`                       | delete                               |
| POST   | `/api/v1/lists/{id}/sync`                  | enqueue a sync_list job              |
| GET    | `/api/v1/lists/{id}/tracks`                | list tracks                          |
| POST   | `/api/v1/lists/{id}/tracks/{tid}/skip`     | mark track skipped                   |
| POST   | `/api/v1/lists/{id}/tracks/{tid}/download` | enqueue a download_track job         |
| GET    | `/api/v1/jobs`                             | list jobs                            |
| GET    | `/api/v1/jobs/{id}/log`                    | paged log lines                      |
| POST   | `/api/v1/jobs/{id}/cancel`                 | cancel running/pending job           |
| POST   | `/api/v1/jobs/{id}/retry`                  | reset a failed job                   |
| GET    | `/api/v1/events`                           | SSE stream                           |

## Quick paste-URL example

```bash
TOKEN=$(cat ~/.config/toolcrate/api-token)
curl -X POST http://127.0.0.1:48721/api/v1/lists \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Late Night","source_url":"https://open.spotify.com/playlist/<id>"}'
```

## Limits in Phase 1

- No frontend UI; Phase 1 is API only.
- Spotify private playlists / Liked Songs require OAuth (Phase 3).
- DJ-set recognition is wired into the data model but not exposed as an
  API verb yet (Phase 4).
- Library scan runs only by manual job creation (Phase 5 adds dedicated
  endpoint).

## Architecture

Single FastAPI process hosts:
- HTTP API + OpenAPI docs
- APScheduler-style asyncio job worker (single, drains DB-backed queue)
- SSE event bus
- SQLite via SQLAlchemy 2.x async + Alembic migrations

Domain services in `toolcrate.core.*`. HTTP routers in
`toolcrate.web.routers.*`. Persistence in `toolcrate.db.*`.

See `docs/superpowers/specs/2026-04-27-frontend-music-manager-design.md`
for the full design and `docs/superpowers/plans/2026-04-27-phase-1-backend-foundations.md`
for the implementation plan.
