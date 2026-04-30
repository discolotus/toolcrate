# toolcrate frontend

Lives at `src/toolcrate/web/frontend/`. Vite + React 18 + TypeScript + Tailwind +
shadcn/ui (Radix). State: TanStack Query v5 + custom SSE invalidator.

## Layout

    src/toolcrate/web/frontend/
      package.json
      src/
        api/      # fetch client, query keys, generated openapi types, SSE
        components/ # Sidebar, Layout, AddListDialog, ListMasterTable,
                  # TrackTable, JobLogPane, StatusPill, LiveBadge, ui/
        hooks/    # query/mutation hooks per resource + useSseInvalidation
        pages/    # Dashboard, SpotifyLists, ListDetail, Jobs
        lib/      # cn, format
        styles/globals.css
      __tests__/  # vitest specs
      scripts/gen-api.ts

## Common commands

| Command | What |
|---|---|
| `make frontend` | one-shot production build to `src/toolcrate/web/static/` |
| `make frontend-dev` | Vite dev server at `:5173` (set `TOOLCRATE_ENV=dev` for backend CORS) |
| `make frontend-test` | lint + typecheck + vitest + build |
| `npm run gen:api` | regenerate `src/api/types.ts` from a running backend's `/api/openapi.json` |

## Auth

The SPA uses cookie auth; no token is ever exposed to JS. The cookie is set by the
backend's `/app` route on first hit. SSE works because `EventSource` is same-origin.
The same `api_token_auth` dep accepts either `Authorization: Bearer <token>` or
`Cookie: tc_session=<token>` (header takes precedence).

## SSE event handling

`useSseInvalidation` opens one `EventSource` to `/api/v1/events`, dispatches each
event through `dispatchSseEvent` (which invalidates the right TanStack Query keys),
and feeds `log.append` events to per-job listeners registered via `subscribeJobLog`.
