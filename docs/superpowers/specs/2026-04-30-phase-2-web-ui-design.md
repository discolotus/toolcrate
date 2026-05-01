# Phase 2 — Web UI v1 Design Spec

- **Date:** 2026-04-30
- **Author:** Brainstorm session (Claude + user)
- **Status:** Draft, ready for review
- **Scope:** Build the React/TypeScript SPA on top of the Phase 1 FastAPI backend (merged in PR #20). Strictly limited to spec §8 Phase 2: paste-URL Spotify playlists, end-to-end queue visibility, dashboard skeleton. No DJ-set, library, OAuth, settings UI, or manual-list page.
- **Parent spec:** [docs/superpowers/specs/2026-04-27-frontend-music-manager-design.md](2026-04-27-frontend-music-manager-design.md) — read sections 7 and 8 first; this document refines Phase 2 only.

## 1. Goals

- Ship a working web app for the most-used flow: paste a public Spotify playlist URL, watch it sync, see per-track download status update live.
- Auto-onboard auth: zero-friction first visit, no token paste step.
- Frontend builds during `pip install` so packaged distributions (wheels, `pipx install toolcrate`) ship with the SPA ready to serve.
- Existing Phase 1 backend code stays unchanged except: one new auth path (cookie), one new preview endpoint, one new static route.

## 2. Non-Goals (Phase 2)

- DJ sets, manual lists, library scan UI.
- Spotify OAuth flow + private playlists (Phase 3).
- Settings UI (sldl config editor, music root, tools install).
- Schedule calendar UI.
- Playwright e2e test (Phase 5 polish).
- Theme toggle / light mode (dark default only).

## 3. Decisions Captured From Brainstorm

| Topic | Decision |
|---|---|
| Phase 2 page set | Strict spec §8: `/`, `/sources/spotify`, `/lists/:id`, `/jobs`. No others. |
| Auth in browser | HttpOnly cookie set server-side on first hit to `/app`. No login screen. |
| Build/ship | Hatch custom build hook runs `npm ci && npm run build` during wheel build. Built `static/` not committed. `package-lock.json` committed. |
| Frontend location | `src/toolcrate/web/frontend/` (npm package), output to `src/toolcrate/web/static/`. |
| Dev workflow | `npm run dev` at `:5173` proxies `/api/*` to backend at `:48721`. Backend allows CORS for `localhost:5173` only when `TOOLCRATE_ENV=dev`. |
| API typing | `openapi-typescript` regenerates `src/api/types.ts` from `/api/openapi.json`. Committed. |
| Server state | TanStack Query. SSE invalidates queries; no manual cache writes. |
| Live log tail | One global `EventSource('/api/v1/events')`. Components filter by job id. |
| E2E tests | Deferred to Phase 5. Vitest + MSW only. |

## 4. Architecture

### 4.1 Directory layout

```
src/toolcrate/web/
  __init__.py
  app.py                  # existing — adds /app router + cookie auth path
  middleware.py           # existing — extended for cookie auth
  routers/
    __init__.py
    auth.py               # NEW — /app/* SPA serving + cookie set
    lists.py              # existing — adds POST /lists/preview
    ...                   # existing routers unchanged
  static/                 # gitignored, hatch hook output
    index.html
    assets/
  frontend/               # NEW — Vite/React/TS source
    package.json
    package-lock.json     # committed
    vite.config.ts
    tsconfig.json
    index.html
    src/
      main.tsx
      App.tsx
      api/
        client.ts         # fetch wrapper, RFC 7807 parser
        types.ts          # generated from OpenAPI (committed)
        sse.ts            # EventSource wrapper, query invalidator
      pages/
        Dashboard.tsx
        SpotifyLists.tsx
        ListDetail.tsx
        Jobs.tsx
      components/
        Sidebar.tsx
        ListMasterTable.tsx
        TrackTable.tsx
        AddListDialog.tsx
        StatusPill.tsx
        JobLogPane.tsx
        Toast.tsx
      hooks/
        useLists.ts
        useJobs.ts
        useTracks.ts
        useSseInvalidation.ts
      lib/
        format.ts
        cn.ts
      styles/
        globals.css       # Tailwind base
```

### 4.2 Stack

- Vite + React 18 + TypeScript (strict mode).
- React Router v6 (data routers — `createBrowserRouter`).
- TanStack Query v5 for server state. Zustand only if a transient global emerges (e.g. sidebar collapsed); start without.
- shadcn/ui via CLI (`npx shadcn@latest add button dialog input table tabs sonner badge card`). Components copied into `src/components/ui/`.
- Tailwind CSS 3.x with class-variance-authority + tailwind-merge (shadcn pattern).
- react-hook-form + zod for the Add-List form.
- `@tanstack/react-virtual` for the Track table (lists can run thousands of tracks).

### 4.3 Auth flow (cookie-based)

```
First visit to http://127.0.0.1:48721/app/
  ↓
Backend GET /app/{path:path}:
  1. If request has no `tc_session` cookie:
     - Read ~/.config/toolcrate/api-token (file mode 0600)
     - Compute hash, compare to setting.api_token_hash
     - Set-Cookie: tc_session=<token>; HttpOnly; SameSite=Strict; Path=/
  2. Serve src/toolcrate/web/static/index.html (verbatim)
  ↓
SPA boots, makes /api/v1/* calls with credentials: 'include'
  ↓
Auth middleware (existing, extended):
  - if Authorization: Bearer <token> → use that
  - else if Cookie tc_session=<token> → use that
  - else → 401 + RFC 7807
```

Notes:

- If `~/.config/toolcrate/api-token` is missing or the hash does not match, `/app` returns a plain HTML page instructing the user to run `toolcrate serve` to bootstrap (no SPA load).
- SSE (`EventSource`) sends cookies automatically because it is same-origin.
- Logout endpoint deferred to a later phase. Removing `~/.config/toolcrate/api-token` and rotating the hash is the manual reset path.

### 4.4 SSE → query invalidation

Single `EventSource` lives in a top-level `<SseProvider>`. On each event:

| Event type | Action |
|---|---|
| `list.created` / `list.updated` / `list.deleted` | invalidate `['lists']` and `['lists', id]` |
| `job.created` / `job.update` / `job.finished` | invalidate `['jobs']`; if event payload has `source_list_id`, also invalidate `['lists', id]` and `['lists', id, 'tracks']` |
| `track.updated` | invalidate `['lists', id, 'tracks']` |
| `log.append` | append to in-memory log buffer keyed by `job_id` (Zustand or React context — not React Query) |

Reconnect strategy: exponential backoff capped at 30s. UI shows a small "live" / "reconnecting" pip in the header.

### 4.5 New backend endpoint

`POST /api/v1/lists/preview`

```python
# request
{ "source_url": "https://open.spotify.com/playlist/..." }

# 200 response
{
  "source_type": "spotify_playlist",
  "external_id": "...",
  "name": "Daft Punk Essentials",
  "owner": "spotify",
  "total_tracks": 42,
  "art_url": "https://..."
}

# 400 if URL not recognized; 404 if Spotify says playlist missing
```

Implementation: thin wrapper around `SpotifyClient.fetch_playlist` (already exists). No DB write. Used by the Add-List dialog to autofill name + show metadata before commit.

### 4.6 Add-list flow

```
User clicks "Add Spotify list" on /sources/spotify
  ↓
Dialog opens with URL input (autofocus)
  ↓
On URL paste/blur (debounced 300ms):
  - validate URL via zod (must match open.spotify.com/playlist/<id>)
  - POST /lists/preview → fill `name` field with returned name, show art + track count
  ↓
User edits name (optional), picks sync_interval (default 'manual'), submits:
  - POST /lists  → server creates row + enqueues sync_list job
  - dialog closes, list appears in master table (via SSE invalidation)
  - URL changes to /lists/:newId so the user sees track table fill in
```

### 4.7 Pages

#### Dashboard (`/`)

Skeleton card grid:
- `Lists` card: count of `source_list` rows, link to `/sources/spotify`
- `Active jobs` card: count of `job.state in (pending, running)`, link to `/jobs`
- `Recent activity` card: last 10 finished jobs (type, list name, duration, status)

No charts, no library stats. P5 fills in.

#### Spotify lists (`/sources/spotify`)

Master/detail layout:
- **Left:** virtualized table of `source_list` rows where `source_type='spotify_playlist'`. Columns: art thumb, name, track count, last sync, status pill. Click → navigates to `/lists/:id`.
- **Right:** by default, shows a "select a list" empty state. When `:id` is set, embeds `<ListDetailPanel>`.
- Toolbar: `Add Spotify list` button → opens dialog (4.6).

#### List detail (`/lists/:id`)

Tabs:
- **Tracks (default):** `<TrackTable>` — virtualized rows. Columns: position, artist, title, duration, status pill, retry button. Filter chips for status.
- **History:** table of past `job` rows for this list (latest first). Click row → expands inline log via SSE replay (uses `job.log_path` HTTP fetch + tail subsequent SSE events).
- **Settings:** read-only summary + minimal edit form (name, download_path, sync_interval, enabled toggle). No Spotify-specific fields. PATCH `/lists/:id`.

Header: name, art, track count, last-sync timestamp, primary action `Sync now` (POST `/lists/:id/sync`).

#### Jobs (`/jobs`)

Single virtualized table.
- Columns: id, type, source list, state pill, progress (`current/total` from `progress_json`), started/finished.
- Filters: state (pending/running/success/failed), type. URL-synced (`?state=running&type=sync_list`).
- Row actions: `Cancel` (running), `Retry` (failed → enqueues new job with same payload). Both call existing endpoints.
- Click row → side drawer with live log pane.

### 4.8 Build hook details

`pyproject.toml`:

```toml
[tool.hatch.build.hooks.custom]
path = "scripts/build_frontend.py"
dependencies = []

[tool.hatch.build.targets.wheel]
include = [
  "src/toolcrate/**/*.py",
  "src/toolcrate/web/static/**",
]
artifacts = ["src/toolcrate/web/static/**"]

[tool.hatch.build.targets.sdist]
include = [
  "src/toolcrate",
  "scripts/build_frontend.py",
  "alembic.ini",
  # ...existing entries
]
```

`scripts/build_frontend.py` (Hatch `BuildHookInterface`):

- `initialize(version, build_data)`:
  - If `os.environ.get("TOOLCRATE_SKIP_FRONTEND_BUILD") == "1"` → return.
  - If `shutil.which("npm") is None` → log warning, write a stub `index.html` to `src/toolcrate/web/static/` that says "Frontend not built. Install Node 20+ and reinstall, or run `make frontend`." → return.
  - Run `npm ci` then `npm run build` from `src/toolcrate/web/frontend/`. Surface stderr on failure (raises).
- Adds `src/toolcrate/web/static/**` to `build_data["artifacts"]`.

`Makefile` target `frontend`:

```make
frontend:
	cd src/toolcrate/web/frontend && npm ci && npm run build
```

`.gitignore` adds `src/toolcrate/web/static/`.

Editable installs (`pip install -e .`): hatch hook runs once, devs use `npm run dev` thereafter for hot reload — Vite dev server proxies API calls to `:48721`.

### 4.9 Backend serving (`/app`)

New router `src/toolcrate/web/routers/auth.py` registers:

- `GET /app` and `GET /app/{path:path}` → cookie-set + `FileResponse(static/index.html)` for any path (SPA owns routing).
- `GET /app/assets/{filename}` → `FileResponse` from `static/assets/`.
- `GET /` → `RedirectResponse` to `/app/`.

Mount via `app.include_router` in existing `app.py`. The static asset path stays under `/app/assets/` so cookie protection cannot be bypassed by a request that never crosses `/app`.

### 4.10 CORS for dev

Middleware reads `os.environ.get("TOOLCRATE_ENV")`. When `dev`, `CORSMiddleware` allows origin `http://localhost:5173` and `credentials=True`. Otherwise no CORS middleware. Production single-origin needs none.

### 4.11 Tests

**Backend (pytest):**

- `test_auth_cookie.py` — `/app` sets cookie; `/api/v1/lists` accepts cookie auth; rejects bogus cookie.
- `test_lists_preview.py` — mocked `SpotifyClient.fetch_playlist`; happy path + 400 (bad URL) + 404 (Spotify miss) + RFC 7807 error shape.
- `test_app_static.py` — `/app/` returns 200 with HTML; `/app/anything` returns same HTML (SPA fallback).

**Frontend (Vitest + Testing Library + MSW):**

- `client.test.ts` — `fetch` wrapper parses RFC 7807, throws `ApiError` with code/title/detail.
- `sse.test.ts` — given mocked SSE events, asserts the right `queryClient.invalidateQueries` calls.
- `AddListDialog.test.tsx` — paste URL → preview shown → submit → POST sent.
- `TrackTable.test.tsx` — renders rows, status pill colors, retry button calls POST.
- `Jobs.test.tsx` — filter chips update URL query; cancel button only on `running`.

**CI:**

- New GitHub Actions matrix job `frontend`: Node 20, run `npm ci`, `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build`. Artifacts upload `static/` (so the install hook test that follows can use the prebuilt output if desired).
- Existing pytest job runs unchanged plus the three new test files.

## 5. Data flow recap

```
Browser (React)        FastAPI (existing + new auth.py)        Phase 1 services
─────────────────       ─────────────────────────────────       ──────────────────
/app/  ──────────────►  GET /app/* (sets cookie)
                        FileResponse(index.html)
SPA boots
fetch /api/v1/lists  ──► auth middleware (cookie)  ──────────►  ListService
                        JSON response
TanStack Query caches
EventSource('/events') ► /api/v1/events (SSE)      ◄───────────  EventBus
SSE event arrives  ────► onmessage → invalidateQueries
TanStack refetches /api/v1/lists, components re-render
```

## 6. Risks & Mitigations

- **Hatch hook + sdist installs without Node** — mitigation: hook detects missing `npm`, writes stub HTML, install proceeds. Server still works (CLI users unaffected).
- **`openapi-typescript` drift** — mitigation: `npm run gen:api` is idempotent; CI runs it and fails on diff (`git diff --exit-code src/api/types.ts`). Forces devs to regenerate when changing FastAPI schemas.
- **Cookie auth bypass** — mitigation: cookie scoped to `/`, `HttpOnly`, `SameSite=Strict`. Origin/Host middleware (already in P1) blocks DNS rebinding. No CORS in prod.
- **Vite dev proxy CORS in dev** — mitigation: `TOOLCRATE_ENV=dev` env-flag-gated allow. Default closed.
- **Track table perf with 10k+ rows** — mitigation: `react-virtual`, paginated server endpoint already returns 500/page (Phase 1 default).

## 7. Open Questions

None. All decisions resolved during brainstorm.

## 8. Out of Scope (deferred to later phases)

- Spotify OAuth start/callback + private playlists picker → Phase 3.
- DJ-set page, recognition progress UI, Re-analyze button → Phase 4.
- Library tile grid + search, scan trigger → Phase 5.
- Settings UI (sldl config editor, music root, tools install, OAuth account list) → Phase 5.
- Schedule calendar view → Phase 5.
- Playwright e2e happy path → Phase 5.
- Light theme toggle → Phase 5.
- Logout endpoint + UI → Phase 3 alongside OAuth.
