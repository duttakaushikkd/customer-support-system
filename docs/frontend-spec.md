# Frontend specification

Stack: Vite 6, React, React Router, TypeScript. Package: `frontend/`.

## Routes

| Path | Auth | Page |
|---|---|---|
| `/login` | Public | Sign in / register |
| `/chat` | Any signed-in | Live Chat |
| `/portal` | Any signed-in | Ticket list for current user |
| `/admin` | `role === admin` | Queue, stats, approve/reject |
| `*` | — | Redirect to `/chat` (then to login if needed) |

Unauthenticated protected routes redirect to `/login`. Non-admin hitting `/admin` redirects to `/chat`.

## Session

`frontend/src/auth.ts` — `localStorage` keys `css_token` and `css_user`. API helper attaches Bearer token when `auth=true`.

## Login / register UI

- Toggle Sign in | Register
- Sign in: username, password
- Register: username, **email** (required), optional display name, password, confirm password
- Copy: sign in with username and password; demo admin `admin` / `admin123`

## Live Chat

Posts to `/api/chat` with session username and `channel=chat`. Shows resolution, ticket number, reasoning steps when present.

## Portal

Lists the caller’s tickets (number, channel, subject, status, relative time). No mailto / support-inbox CTA.

## Admin

Loads `/tickets` and `/tickets/stats`. Human queue: pending approval. Actions call `/tickets/{id}/decision`.

## API client

`frontend/src/api.ts`:

- `VITE_API_URL` default `""` (same origin)
- Parses FastAPI `{ detail: string }` errors into `Error.message`

## Build for Vercel

`vercel.json` `buildCommand` runs `npm --prefix frontend run build` and copies `frontend/dist` → `backend/static`. FastAPI catch-all serves `index.html` for SPA routes.
