# API specification

Base URL: empty on Vercel (same origin). Local Vite proxies `/auth`, `/api`, `/tickets`, `/health` to `http://localhost:8000`.

Unless noted, JSON request bodies and JSON responses. Authenticated routes require:

```
Authorization: Bearer <jwt>
```

## Public

### `POST /auth/register`

Create a customer account and return a session.

Request:

```json
{
  "username": "jane",
  "email": "jane@example.com",
  "password": "secret1",
  "display_name": "Jane"
}
```

- `username`: 3–32 chars, `[A-Za-z0-9_.-]`, stored lowercase
- `email`: valid email, stored lowercase, unique
- `password`: min 6 characters
- `display_name`: optional

Success: `200` — see [Auth response](#auth-response).

Errors: `400` with `detail` (validation, username taken, email taken).

### `POST /auth/login`

Request:

```json
{
  "username": "jane",
  "password": "secret1"
}
```

Login is **username only** (not email).

Success: `200` — auth response.  
Errors: `401` Invalid credentials.

### `GET /health` and `GET /api/health`

```json
{ "ok": true }
```

## Authenticated

### `POST /api/chat`

Request:

```json
{
  "message": "I forgot my password",
  "user_id": "jane",
  "channel": "chat"
}
```

- `user_id` optional; defaults to JWT username
- `channel`: `chat` or `portal` (anything else treated as `chat`)
- `customer_email` on the ticket is taken from the JWT `email` claim

Response: [Ticket pipeline response](#ticket-pipeline-response).

Runs the full orchestrator (may exceed Hobby 10s).

### `GET /tickets?limit=200`

- Customer: tickets where `customer_id` = JWT `sub`
- Admin: all tickets (capped by `limit`)

Array of ticket documents (Mongo shape, `_id` omitted).

### `GET /tickets/stats` (admin)

```json
{
  "unique_users": 0,
  "total_tickets": 0,
  "resolved": 0,
  "escalated": 0,
  "not_resolved": 0,
  "pending_human_approval": 0,
  "resolution_rate_pct": 0,
  "by_channel": {}
}
```

`resolved` counts `auto_resolved` + `resolved`. Non-admin → `403`.

### `POST /tickets/{ticket_id}/decision` (admin)

```json
{ "decision": "approved" }
```

`decision` is `approved` or `rejected`. Missing ticket → `404`. Response: ticket pipeline response.

## Auth response

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "role": "customer",
  "username": "jane",
  "email": "jane@example.com",
  "name": "Jane"
}
```

## Ticket pipeline response

Returned by chat and human decision:

| Field | Type |
|---|---|
| `ticket_id` | UUID string |
| `ticket_number` | e.g. `INC1001` |
| `status` | see data-model spec |
| `channel` | `chat` \| `portal` \| `email` |
| `ticket_type` | string |
| `category` | string |
| `resolution` | string |
| `reply_subject` | string |
| `requires_human` | bool |
| `holding` | true iff status is `pending_human_approval` |
| `resolver_confidence` | 0–1 |
| `reasoning_steps` | agent trace |
| `loop_metadata` | object |
| `guardrail_flags` | string[] |
| `proposed_action` | string |
| `rag_hits` | retrieved articles |

## Errors

| Status | When |
|---|---|
| 400 | Register validation |
| 401 | Missing/invalid JWT or bad login |
| 403 | Admin route, non-admin |
| 404 | Ticket not found; SPA miss |
| 500 | Function crash (e.g. LLM/Mongo); Vercel `FUNCTION_INVOCATION_FAILED` |

## Removed endpoints

Do not implement or call:

- `POST /api/email-intake`
- `GET|POST /api/email-poll`
