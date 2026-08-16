# Architecture specification

## Purpose

A multi-agent customer-support system that turns a chat or portal message into a ticket, retrieves knowledge-base context, drafts a resolution, applies deterministic guardrails, then either executes a simulated action or parks the ticket for an admin.

## Non-goals

- Inbound email (IMAP / webhook intake)
- Outbound email (SMTP replies)
- Azure services (OpenAI Azure, AI Search, Cosmos, Entra, Logic Apps, App Insights)
- Mock / hash LLM fallback — a real OpenAI-compatible API is required
- Password-reset or MFA flows that actually send mail (KB text may describe them; the product only simulates actions)

## Channels

| Channel | Status | Entry |
|---|---|---|
| `chat` | Active | Live Chat → `POST /api/chat` with `channel=chat` |
| `portal` | Active | Same API with `channel=portal` |
| `email` | Legacy only | Field remains on `TicketState` for old documents; no intake path |

Email **addresses** are stored on user records at registration. They are not a support channel.

## Context diagram

```
Browser (Vite React SPA)
        │  same origin on Vercel
        ▼
FastAPI (api/index.py → backend/app/main.py)
        │
        ├── Auth (JWT)
        ├── Orchestrator + agents
        ├── OpenAI Chat Completions + Embeddings
        └── MongoDB Atlas
              tickets | users | kb_articles | auditLog | counters
```

## Azure mapping (diagram → implementation)

| Diagram | Implementation |
|---|---|
| Azure OpenAI | `OPENAI_BASE_URL` + `OPENAI_API_KEY` |
| Azure AI Search | Atlas `kb_articles.embedding` + cosine search in app code |
| Cosmos DB | Atlas collections listed above |
| Entra / MSAL | Local username/password JWT |
| Logic App + Outlook | Removed |
| Application Insights | JSON stdout logs on the Vercel function |

## Runtime topology

- **Production:** one Python serverless function (`api/index.py`) serves the API and the built SPA (`backend/static`).
- **Local:** FastAPI on `:8000`, Vite on `:5173` with path proxies.
- **Bootstrap (cold start):** ensure indexes → seed demo users → seed KB if empty.

Path note: Vercel may collapse requests to `/api`. Middleware restores `x-forwarded-uri` / `x-invoke-path` when needed.

## Trust boundaries

- Secrets live in Vercel env / local `.env` (gitignored).
- Atlas must allow `0.0.0.0/0` because Vercel IPs are not static.
- Actions (unlock, reset password, refund, etc.) are **simulated** and audited; they do not call identity or billing systems.
