# Frontend Music Manager — Design Spec

- **Date:** 2026-04-27
- **Author:** Brainstorm session (Claude + user)
- **Status:** Draft, ready for review
- **Scope:** Add a local web UI on top of toolcrate that manages Spotify playlists and YouTube DJ-set sources, periodically syncs them via sldl, runs Shazam-based recognition on DJ sets, and maintains a local file library. Backend-first design with a clean HTTP API so a future Swift macOS client can share it.

## 1. Goals & Non-Goals

### Goals

- Single-user, local-only web app for managing music sources and downloads.
- Two source types in v1: Spotify playlists (paste-URL, OAuth-optional) and YouTube DJ sets.
- Periodic background sync that resolves a source's track list, runs sldl, and updates a local on-disk library organized into per-list folders.
- Real-time UI feedback (sync progress, download status, recognition logs).
- Existing CLI flows (cron, `toolcrate sldl`, wishlist) continue to work; web UI is additive.
- Clean HTTP/JSON API and OpenAPI spec so a native Swift macOS client could be added later without backend rework.

### Non-Goals

- Multi-user, role-based access, or cloud hosting.
- Mobile / iOS / Swift apps in the initial scope (door is left open).
- AcoustID/chromaprint or other recognizers beyond Shazam in v1.
- Streaming playback in the browser, or pushing edits back to Spotify.
- Migrating users away from cron immediately (cron path is preserved).

## 2. High-Level Decisions

| Topic | Decision |
|---|---|
| Deploy model | Local-only single user, `127.0.0.1` |
| Frontend strategy | Backend-first, frontend-agnostic API; web UI v1, Swift client preserved as future option |
| Spotify | Paste-URL works without auth; OAuth is optional but available from v1 |
| Storage | SQLite primary, SQLAlchemy 2.x + Alembic migrations |
| Disk layout | Per-list configurable `download_path`; default template `~/Music/toolcrate/<source_type>/<slug>/` |
| Backend framework | FastAPI + Pydantic v2 |
| Scheduler | APScheduler in-process (jobstore in same SQLite) |
| Job queue | DB-backed `job` table, single asyncio worker drains serially |
| Frontend | React 18 + Vite + TypeScript, shadcn/ui (Radix + Tailwind), TanStack Query |
| Auth | Static API token at `~/.config/toolcrate/api-token` (auto-set on first launch); header auth + Origin/Host check middleware |
| Live updates | Server-Sent Events, single multiplexed stream |
| Layout | Master/detail (vibe B) for sources & playlists; tile grid (vibe A) for the Library view; dashboard cards for the home view |
| Download orchestration | Hybrid: metadata layer ours, sldl invoked at playlist-level for actual downloads, output reconciled back to per-track rows |
| Phasing | Five phases, each shippable: (1) backend foundations, (2) paste-URL playlists end-to-end UI, (3) Spotify OAuth, (4) DJ-set analyzer, (5) Library + polish |

## 3. Architecture

A single FastAPI daemon (`toolcrate serve`) hosts the API, scheduler, worker, and SSE bus in one process — appropriate for a local-only single-user deploy.

```
┌──────────────────────────────────────────────────────────┐
│ Browser (React SPA)                                      │
│  - served at /app, talks to /api/v1/* + /api/v1/events   │
└──────────────────────────────────────────────────────────┘
                       │ HTTP/SSE (token auth)
┌──────────────────────────────────────────────────────────┐
│ FastAPI app (toolcrate.web)                              │
│  - Routers: lists, tracks, jobs, schedule, oauth,        │
│    library, settings                                     │
│  - Static SPA mount + OpenAPI                            │
│  - SSE event bus                                         │
│  - API token auth + Origin/Host guard middleware         │
├──────────────────────────────────────────────────────────┤
│ Domain services (toolcrate.core)                         │
│  - SourceListService   - CRUD + folder management        │
│  - SyncService         - resolve tracks + run sldl       │
│      - SpotifyClient (public URL + OAuth)                │
│      - YouTubeClient  (yt-dlp metadata only)             │
│  - RecognitionService - DJ-set audio -> tracks           │
│      - ShazamRecognizer (wraps shazam-tool)              │
│  - DownloadService    - sldl invocation + reconcile      │
│      - SldlAdapter (subprocess wrapper)                  │
│  - LibraryService     - disk scan, dedup, reconcile      │
│  - JobQueue, EventBus                                    │
├──────────────────────────────────────────────────────────┤
│ Infrastructure                                           │
│  - SQLite (DB.sqlite) — SQLAlchemy + Alembic             │
│  - APScheduler        — jobstore in same DB              │
│  - Worker (asyncio task) — drains job table serially     │
└──────────────────────────────────────────────────────────┘
                       │ subprocess
            ┌──────────┴──────────┐
       sldl (slsk-batchdl)    shazam-tool, yt-dlp, ffmpeg
```

### Boundaries

- `core/` is pure Python services; no FastAPI imports. CLI commands and web routes both call `core/`.
- `web/` is thin: request validation, auth, glue to services, SSE fan-out.
- Existing `cli/`, `queue/`, `wishlist/`, `scripts/` are rewritten as thin shims over `core/` services. Cron path keeps working for users not on the web UI by calling the same services.
- `db/` holds SQLAlchemy models, Alembic env/versions, and a shared session factory.

### Process supervision

- `toolcrate serve` runs in foreground for dev.
- macOS launchd `.plist` template and Linux systemd unit shipped in `examples/` for autostart.
- API server's bound port is configurable in settings (default `48721`); must be stable for the Spotify OAuth redirect URI.

## 4. Data Model

SQLAlchemy 2.x models, SQLite with WAL mode, all timestamps stored UTC.

### Tables

```
source_list
  id              INTEGER PK
  name            TEXT          -- user label, slugified for default folder
  source_type     TEXT          -- 'spotify_playlist' | 'youtube_djset' | 'manual'
  source_url      TEXT
  external_id     TEXT          -- spotify playlist id / yt video id
  download_path   TEXT          -- absolute; default templated from source_type+slug
  enabled         BOOLEAN       -- default true; false skips scheduled runs but allows manual sync
  sync_interval   TEXT          -- 'hourly'|'daily'|'manual'|<cron-expr>; default 'manual'
  last_synced_at  TIMESTAMP
  last_sync_status TEXT         -- 'ok'|'error'|'never'
  last_error      TEXT
  oauth_account_id INTEGER FK   -- nullable; only for private spotify lists
  metadata_json   JSON          -- art_url, owner, total_tracks_remote, etc.
  created_at, updated_at

track_entry
  id              INTEGER PK
  source_list_id  INTEGER FK
  position        INTEGER       -- order within list (Spotify) or chunk-index (DJ set)
  artist          TEXT
  title           TEXT
  album           TEXT
  duration_sec    INTEGER
  isrc            TEXT          -- canonical key when present
  spotify_track_id TEXT
  yt_timestamp_sec INTEGER      -- for DJ-set: when track appears in mix
  recognition_confidence REAL   -- nullable; only for DJ-set tracks
  download_status TEXT          -- 'pending'|'queued'|'downloading'|'done'|'failed'|'skipped'
  download_id     INTEGER FK    -- nullable; latest download attempt
  first_seen_at, last_seen_at
  removed_at      TIMESTAMP     -- soft-delete when track leaves remote list
  UNIQUE(source_list_id, isrc) WHERE isrc IS NOT NULL
  INDEX(source_list_id, position)

download
  id              INTEGER PK
  track_entry_id  INTEGER FK
  job_id          INTEGER FK
  attempt         INTEGER
  status          TEXT          -- 'success'|'failed'|'partial'
  file_path       TEXT          -- absolute path on disk if success
  file_size_bytes INTEGER
  sldl_match_path TEXT          -- entry as it appears in sldl index, used for reconciliation
  error           TEXT
  started_at, finished_at

job
  id              INTEGER PK
  type            TEXT          -- 'sync_list'|'recognize_djset'|'download_track'|'library_scan'
  payload_json    JSON
  state           TEXT          -- 'pending'|'running'|'success'|'failed'|'cancelled'
  priority        INTEGER       -- lower = sooner
  source_list_id  INTEGER FK
  attempts        INTEGER
  max_attempts    INTEGER
  scheduled_for   TIMESTAMP     -- earliest run time (for retries / scheduling)
  started_at, finished_at
  log_path        TEXT          -- file with full log lines
  progress_json   JSON          -- {current, total, message}
  pid             INTEGER       -- subprocess pid for cancellation
  INDEX(state, scheduled_for, priority)

oauth_account
  id              INTEGER PK
  provider        TEXT          -- 'spotify'
  account_label   TEXT
  access_token_enc BLOB         -- encrypted at rest with key derived from API token
  refresh_token_enc BLOB
  expires_at      TIMESTAMP
  scopes          TEXT
  remote_user_id  TEXT
  remote_display  TEXT

library_file
  id              INTEGER PK
  path            TEXT UNIQUE
  size_bytes      INTEGER
  mtime           TIMESTAMP
  artist, title, album, duration_sec
  acoustid_fp     TEXT          -- nullable, future
  source_list_id  INTEGER FK    -- nullable; set if matched to a list folder
  matched_track_id INTEGER FK   -- nullable; matched track_entry

setting
  key             TEXT PK
  value_json      JSON
  -- holds: api_token_hash, music_root, default_sldl_args, ui_prefs, server_port
```

APScheduler manages its own `apscheduler_jobs` table in the same SQLite database.

### Key choices

- `track_entry` is the join between "what should exist" (resolved from a source) and "what's downloaded." Its `download_status` field is a denormalized cache of the latest matching `download` row.
- DJ-set tracks share the `track_entry` table; they're distinguished by `source_list.source_type` and the presence of `yt_timestamp_sec` and `recognition_confidence`.
- `download_path` is per-list; renaming the list folder updates the path and the worker resolves it at run-time, so download history is preserved.
- OAuth tokens are encrypted with a key derived from the API token. Loss of the API token implies re-authentication, which is acceptable for a local-only deploy.
- `removed_at` enables soft deletion for diff detection — a track that left a remote playlist isn't purged, so download history stays intact.

## 5. API Surface

All endpoints under `/api/v1/`. Auth: `Authorization: Bearer <api-token>` header. CORS off (same-origin SPA). Origin/Host check middleware rejects non-localhost requests to defend against DNS rebinding.

```
# Source lists
GET    /api/v1/lists                          ?source_type=&enabled=
POST   /api/v1/lists                          {name, source_url, source_type?, download_path?, sync_interval?, oauth_account_id?}
GET    /api/v1/lists/{id}
PATCH  /api/v1/lists/{id}                     partial update
DELETE /api/v1/lists/{id}                     ?delete_files=false
POST   /api/v1/lists/{id}/sync                trigger sync now → returns job_id
POST   /api/v1/lists/{id}/recognize           DJ-set only; trigger recognition → job_id

# Tracks within a list
GET    /api/v1/lists/{id}/tracks              ?status=&q=&limit=&offset=
POST   /api/v1/lists/{id}/tracks/{tid}/download   manual re-download → job_id
POST   /api/v1/lists/{id}/tracks/{tid}/skip       mark as skipped

# Jobs
GET    /api/v1/jobs                           ?state=&type=&list_id=&limit=
GET    /api/v1/jobs/{id}
GET    /api/v1/jobs/{id}/log                  paginated text log
POST   /api/v1/jobs/{id}/cancel
POST   /api/v1/jobs/{id}/retry

# Spotify OAuth
GET    /api/v1/oauth/spotify/start            -> {auth_url, state}
GET    /api/v1/oauth/spotify/callback         consumes ?code&state, redirects to /app
GET    /api/v1/oauth/accounts
DELETE /api/v1/oauth/accounts/{id}
GET    /api/v1/oauth/spotify/playlists        proxy to list user's Spotify playlists for picker

# Library
GET    /api/v1/library                        ?q=&list_id=&limit=&offset=
POST   /api/v1/library/scan                   trigger scan → job_id
GET    /api/v1/library/stats                  totals for dashboard

# Settings
GET    /api/v1/settings                       redacts secrets
PATCH  /api/v1/settings
GET    /api/v1/settings/sldl                  raw sldl.conf view
PATCH  /api/v1/settings/sldl

# Schedule
GET    /api/v1/schedule                       active scheduled jobs from APScheduler
POST   /api/v1/schedule/pause-all
POST   /api/v1/schedule/resume-all

# Health/info
GET    /api/v1/health
GET    /api/v1/info                           version, paths, tools status

# SSE
GET    /api/v1/events                         ?topics=jobs,lists,library
```

### SSE event payloads

```
event: job.update
data: {"id": 42, "state": "running", "progress": {"current": 12, "total": 60, "message": "Downloading track 12/60"}}

event: list.updated
data: {"id": 7, "tracks_total": 128, "tracks_done": 95, "last_synced_at": "..."}
# tracks_total = COUNT(track_entry) excluding removed_at
# tracks_done  = COUNT(track_entry WHERE download_status='done')

event: library.changed
data: {"added": 3, "removed": 0}

event: log.append
data: {"job_id": 42, "lines": ["...","..."]}
```

The frontend uses one `EventSource` connection and dispatches by event name to TanStack Query cache invalidations and log buffers.

### Conventions

- **OpenAPI:** auto-generated by FastAPI. Frontend runs `npm run generate-api` against `/openapi.json` (via `openapi-typescript`) for a typed client.
- **Pagination:** offset/limit with `X-Total-Count` header.
- **Errors:** RFC 7807 problem+json — `{"type": "...", "title": "...", "status": 400, "detail": "...", "code": "list.not_found"}`.

## 6. Workflows

### 6.1 Add Spotify playlist (paste-URL, no OAuth)

```
User pastes URL → POST /api/v1/lists {source_url, name?}
  ↓
SourceListService.create
  - Detect source_type from URL pattern
  - Parse external_id (playlist id)
  - Fetch playlist metadata via Spotify public Web API (client_credentials token at app level)
  - Create source_list row (download_path templated)
  - Create initial track_entry rows from playlist tracks
  - Enqueue job(type=sync_list, list_id, mode='download_only')
  ↓
Worker picks up sync_list job → SyncService.run_for_list
  - Build sldl args from settings.sldl_defaults + list.download_path
  - Spawn sldl subprocess with the playlist URL, stream stdout
  - Parse lines → emit SSE job.update + log.append events
  - On exit: read sldl index → reconcile → update track_entry rows
  - Mark job success/failed, update list.last_synced_at
```

### 6.2 Spotify OAuth (private playlists / Liked Songs)

```
User clicks "Connect Spotify" in Settings
  ↓
GET /api/v1/oauth/spotify/start
  - Generate state, store in setting (5-min TTL)
  - Build Spotify auth URL with redirect_uri=http://127.0.0.1:<port>/api/v1/oauth/spotify/callback
  - Return {auth_url} → frontend window.location = auth_url
  ↓
Spotify redirects browser back to /api/v1/oauth/spotify/callback?code&state
  - Validate state
  - Exchange code → access_token + refresh_token
  - Encrypt with key derived from API token, store in oauth_account row
  - Redirect to /app/settings?spotify_connected=1
  ↓
GET /api/v1/oauth/spotify/playlists → picker UI
Create source_list with oauth_account_id set
SyncService threads refresh token to sldl via --spotify-refresh
```

Notes:

- The server's bound port is set in settings; the Spotify app's redirect URI must match exactly. Document this dance in the README.
- SyncService refreshes the access token if it's within 10 minutes of expiry, persists the new token, and falls back to letting sldl refresh via `--spotify-refresh` for the actual download run.

### 6.3 Add DJ-set from YouTube

```
User pastes YouTube URL → POST /api/v1/lists {source_type='youtube_djset'}
  ↓
SourceListService.create
  - yt-dlp --dump-single-json fetches title, duration, thumbnail
  - source_list row + metadata_json populated
  - NO track_entry rows yet (need recognition first)
  - Enqueue job(type=recognize_djset, list_id)
  ↓
Worker → RecognitionService.run_for_list
  - Call existing shazam-tool: `toolcrate shazam-tool download <url>`
    (downloads audio, segments, recognizes via shazamio, outputs txt)
  - For each recognized track:
    - Create track_entry row (yt_timestamp_sec, recognition_confidence, artist, title)
    - Dedup against existing track_entry within list (skip if same ISRC or matching artist+title)
  - Emit SSE list.updated with tracks_total
  - Auto-enqueue sync_list job (mode='download_only') → 6.1's download path
```

Notes:

- Recognition is slow (a 2-hour DJ set takes minutes of API calls). Show progress via shazam-tool's per-segment output.
- Re-recognition: a "Re-analyze" button re-runs the job and merges new tracks. Existing matched tracks are preserved.
- If shazam-tool's text format becomes a parsing pain, enhance shazam-tool to emit JSON in P4 rather than parsing fragile output forever.

### 6.4 Scheduled sync (recurring)

```
On startup, SyncService loads all source_list rows with sync_interval != 'manual'
  ↓
For each, register an APScheduler job:
  - trigger = CronTrigger(parse(sync_interval))
  - action = enqueue_job(type='sync_list', list_id=X)
APScheduler stores jobs in apscheduler_jobs table → survives restart.
  ↓
On list update (PATCH sync_interval): unregister + re-register.
On list delete: unregister.
```

The Schedule UI shows the next-run time per list (queried from APScheduler).

### 6.5 Job queue worker

```
Single asyncio worker task launched at FastAPI lifespan startup.
Loop:
  1. SELECT job WHERE state='pending' AND scheduled_for<=now
       ORDER BY priority, scheduled_for LIMIT 1
       (SQLite: short transaction with BEGIN IMMEDIATE)
  2. If none: sleep(1s), continue
  3. Mark state='running', started_at=now, emit SSE
  4. Dispatch by type:
       sync_list       → SyncService.run_for_list
       recognize_djset → RecognitionService.run_for_list
       download_track  → DownloadService.run_single_track
       library_scan    → LibraryService.scan
  5. On exception: state='failed', record error, retry if attempts<max_attempts
     (exponential backoff: scheduled_for = now + 2^attempts minutes)
  6. On success: state='success', emit SSE, finalize
```

Concurrency in v1 is serial — one sldl run at a time — to avoid Soulseek session conflicts. Per-job-type pools could be added later.

Cancellation: `POST /jobs/{id}/cancel` sets a flag; the running job's subprocess gets SIGTERM via the stored pid.

### 6.6 Download orchestration: hybrid playlist-level sldl

Critical design choice — sldl already handles Spotify and YouTube playlists end-to-end. We don't reimplement that.

**Metadata layer (us):**

- Resolve playlist → `track_entry` rows via Spotify Web API (so the UI shows tracks, status, art, ISRC).
- Maintain per-track download status, retry counts, manual skip/retry actions.

**Download layer (sldl):**

- One sldl invocation per sync run, given the playlist URL or generated track list.
- sldl handles parallel search/download, file naming, m3u generation, skip-existing, missed-tracks retry.

**Reconciliation:**

- After (or while) sldl runs, parse its index file (or `--print index` output) to map sldl outcomes back to our `track_entry` rows by ISRC, then by `artist + title` fuzzy match.
- Update `download_status` and create `download` rows with `sldl_match_path`.

**Live progress:**

- Tail sldl stdout, parse "Searching" / "Downloading" / "Succeeded" / "Failed" lines, fan out as SSE `job.update` and `log.append` events.

**Manual single-track retry:**

- `POST /lists/{id}/tracks/{tid}/download` enqueues a `download_track` job that runs sldl with string input (`sldl "Artist - Title"`). Different code path from playlist sync.

**DJ sets:**

- Recognition is ours (yt-dlp + shazam-tool). Output is a list of tracks → one sldl call with `--input-type list` (or generated CSV). Same reconciliation logic.

This avoids reimplementing sldl's matching heuristics, keeps process spawn count low, and still gives the UI per-track status.

### 6.6.1 Sync for manual lists

Manual lists have no remote source to refresh. A sync_list job for a manual list re-evaluates all track_entry rows with `download_status` in (`pending`, `failed`) and runs them through DownloadService:

- If 2+ tracks pending, build a list-input file and run a single sldl invocation with `--input-type list`.
- If 1 track, fall back to the single-track sldl path.

`last_synced_at` updates on completion. The same SSE/log/reconcile flow as 6.6 applies.

### 6.7 Library scan

```
Periodic (configurable, default daily) + manual trigger.
LibraryService.scan walks music_root recursively:
  - For each audio file: read tags (mutagen), compute file hash for dedup
  - Upsert library_file row by path
  - Match to track_entry: prefer ISRC tag → fallback artist+title fuzzy
  - If matched: track_entry.download_status='done', link library_file
Emits SSE library.changed with diff.
```

### 6.8 Migration from existing flat files

`toolcrate migrate` is a one-shot CLI command:

- Read `~/.config/toolcrate/wishlist.txt` → `source_list(source_type='manual', name='Wishlist')`, one `track_entry` per line.
- Read `dj-sets.txt` → one `source_list` per URL with `source_type='youtube_djset'`. Recognition is **not** auto-triggered; user runs it from the UI.
- Read `download-queue.txt` → manual list `Imported queue`, tracks pending.
- Read `sldl.conf` → populate `setting.sldl_defaults`.
- Existing cron entries are kept; users can delete them once they verify the APScheduler-driven sync works.

Idempotent: re-running skips already-imported lines (matched by URL/text).

## 7. Frontend

### 7.1 Stack

- **Build:** Vite + React 18 + TypeScript
- **Routing:** React Router v6
- **State/data:** TanStack Query for server state, Zustand for transient UI state. SSE invalidates queries.
- **API client:** generated from OpenAPI via `openapi-typescript` + thin `fetch` wrapper. Re-generated when backend changes.
- **UI kit:** shadcn/ui (Radix + Tailwind). Dark mode default.
- **Forms:** react-hook-form + zod.
- **Lives at:** `src/toolcrate/web/frontend/`. Vite output → `src/toolcrate/web/static/`. FastAPI serves it at `/app/*`.

### 7.2 Pages

```
/app
├── /                        Dashboard - stats cards + activity feed
├── /sources/spotify         Spotify lists (master/detail)
├── /sources/djsets          DJ sets (master/detail)
├── /sources/manual          Manual lists
├── /lists/:id               Detail view (drill-in target)
│   ├── tab: tracks          paginated table with status filters
│   ├── tab: history         past sync jobs + logs
│   └── tab: settings        rename, path, sync interval, enabled, oauth account
├── /library                 Tile grid + search
├── /jobs                    All jobs, filters, cancel/retry
├── /schedule                Calendar of upcoming + recent runs
└── /settings                api token, music root, sldl config, OAuth accounts, tools status
```

The sidebar layout is fixed; the right detail panel toggles via `?selected=<id>` for deep-linking.

### 7.3 Key components

- `SourceListSidebar` — grouped by source_type
- `ListMasterTable` — virtualized rows, status pill, sync action, art thumb
- `ListDetailPanel` — big art, sync stats, action buttons, live progress bar via SSE
- `TrackTable` — track_entry rows, status pill, retry/skip per row
- `JobLogPane` — SSE-tailed log, follow-toggle
- `LibraryGrid` — masonry tiles, hover for actions
- `OAuthConnectButton` — opens auth_url in popup, polls for completion
- `Toast` — global error/success surface from RFC 7807 errors

## 8. Phasing Roadmap

### Phase 1 — Backend foundations (no UI yet)

- Add deps: FastAPI, SQLAlchemy 2.x, Alembic, APScheduler, mutagen.
- Bump pydantic to v2; sweep code for v1 → v2 changes.
- New packages: `src/toolcrate/web/`, `src/toolcrate/core/`, `src/toolcrate/db/`.
- Implement: SourceListService, SyncService.run_for_list (sldl subprocess + index parse), DownloadService, JobQueue worker, EventBus, API token auth + Origin guard middleware.
- Endpoints: lists CRUD, jobs read, `/events` SSE, `/health`, `/info`.
- New CLI entrypoint: `toolcrate serve`.
- New CLI command: `toolcrate migrate` for flat-file → DB import.
- Tests: services unit-tested with mocked subprocesses; FastAPI TestClient + SQLite tmpdir for integration.
- **Ship state:** CLI users keep working via service-backed shims. No UI yet. Existing cron flows continue.

### Phase 2 — Web UI v1: paste-URL Spotify + queue end-to-end

- Frontend scaffold (Vite/React/shadcn/Tailwind).
- Pages: Dashboard (skeleton), Spotify lists (master/detail), List detail (tracks tab), Jobs.
- SSE wiring + live progress.
- Add-list flow: paste URL, name autofill, sync triggers immediately.
- **Ship state:** Working web app for the most-used flow.

### Phase 3 — Spotify OAuth + private playlists

- OAuth start/callback endpoints, token encryption.
- Browse-my-playlists picker UI.
- Per-list `oauth_account_id`. SyncService threads refresh token to sldl.
- Tests: OAuth flow with mocked Spotify auth server (respx).

### Phase 4 — DJ-set analyzer integration

- RecognitionService wrapping shazam-tool. Job type `recognize_djset`.
- DJ sets list page + add-from-YouTube flow.
- Re-analyze button. Recognition progress SSE.
- If text-format parsing is fragile, contribute a JSON output mode to shazam-tool.

### Phase 5 — Library + polish

- LibraryService scan, `library_file` table, `library_scan` job.
- Library tile grid + search.
- Dashboard stats fully populated.
- Settings UI: sldl config editor, music root, tools install.
- Performance pass, error surfaces, packaging, README updates.

## 9. Testing Strategy

- **Backend unit:** pytest for services. Subprocesses mocked. Spotify HTTP via respx.
- **Backend integration:** FastAPI TestClient + SQLite in tmpdir, real APScheduler, mocked sldl binary (shell stub that emits canned output and writes a fake index file).
- **Backend e2e (opt-in, slow):** real sldl + Docker, real Spotify public playlist, downloads disabled (`--print` mode). Marked `@pytest.mark.integration`.
- **Frontend:** Vitest for components, MSW for API mocking, Playwright for one happy-path e2e (paste URL → see tracks → sync → see progress).
- **CI:** existing GitHub Actions. New job for frontend (lint, type-check, vitest).

## 10. Backward Compatibility

- All existing CLI commands preserved; rewritten internally to call core services.
- Old text files: read once at migration, then ignored. Optionally regenerated as derived export from DB for users who want them.
- Old cron entries: untouched. Users can delete them once they trust APScheduler.
- `toolcrate sldl ...` direct passthrough preserved as a one-shot.

## 11. Security Considerations

- **API token:** generated on first launch, stored at `~/.config/toolcrate/api-token` with `0600` perms. Hash stored in DB; raw token never logged.
- **DNS rebinding:** Origin/Host check middleware rejects requests whose Host isn't `127.0.0.1` or `localhost` and Origin (when present) isn't a localhost variant.
- **OAuth tokens:** encrypted at rest using a key derived from the API token (HKDF). Re-issuing the API token requires re-authenticating Spotify.
- **Subprocess injection:** all sldl/yt-dlp/shazam-tool args built via list-form (`subprocess.run([...])`); never shell-quoted strings. URLs validated against allow-list of hosts before passing.
- **Logs:** redact OAuth tokens and API token from log files and SSE streams.

## 12. Open Risks & Mitigations

- **shazam-tool text output format:** if not JSON-able, parsing is fragile. Mitigation: pin tool version; in P4, add a JSON output mode upstream.
- **sldl line format drift:** mitigation: pin sldl version in tools-install; add a smoke test that asserts known marker lines appear on a canned input.
- **OAuth port stability:** API server must run on a stable port for the Spotify redirect URI. Mitigation: explicit `server_port` setting (default 48721); document the Spotify app redirect URI.
- **SQLite + APScheduler concurrency:** WAL mode + short transactions; serialize via the single worker. Documented for users with high-volume schedules.
- **Long-running recognition jobs blocking the worker:** acceptable in v1 (serial). Reconsider per-type concurrency in P5.

## 13. Out of Scope

- Multi-user, role-based access
- Cloud hosting, public TLS, or non-localhost binding
- Mobile / native iOS apps (Swift macOS client preserved as future option)
- AcoustID / chromaprint / non-Shazam recognizers (future plugin point on RecognitionService)
- Editing playlists back to Spotify
- In-browser audio playback
