# Customer Support Agent

Multi-agent customer support system based on `docs/architecture-diagram.drawio`, built **without Azure**. Production stack is **Vercel (Python FastAPI + Vite SPA)**, **MongoDB Atlas**, and an **OpenAI-compatible LLM**.

**Specs (commit these):** see [`docs/README.md`](docs/README.md) for architecture, API, auth, data model, agents, KB, frontend, deployment, and test cases.

Customers use **Live Chat** and the **Customer Portal**. Admins use the **Admin Dashboard** to approve or reject tickets that fail guardrails. There is **no inbound/outbound email channel**. Email is collected at registration and stored on the user record only.

## Design

```
Customer (Vite SPA)
  Live Chat ────────┐
  Portal   ─────────┼──► FastAPI gateway (api/index.py → backend/app)
                    │         │
Admin Dashboard ────┘         ▼
                    Orchestrator
                      Intake → Triage → RAG → Resolver ⇄ Critic (up to 3 turns)
                                              │
                         Manager ── auto ──► Action (simulated)
                                 └── human ─► Admin queue
                                              approve → Action
                                              reject  → Escalation
```

| Original diagram | This repo |
|---|---|
| Azure OpenAI | OpenAI API (`OPENAI_BASE_URL`, `OPENAI_API_KEY`) |
| Azure AI Search | Atlas `kb_articles` (embeddings + cosine similarity) |
| Cosmos DB | Atlas `tickets`, `auditLog`, `users`, `counters` |
| Entra / MSAL | Local JWT (`username` + password) |
| Logic App + Outlook | Removed |
| Application Insights | Structured JSON logs on the function |

### Auth

- **Register:** `POST /auth/register` with `username`, `email`, `password`, optional `display_name`. Role is always `customer`. Email is stored (unique, case-insensitive); it is **not** used to send mail.
- **Login:** `POST /auth/login` with `username` and `password` only.
- Passwords are **PBKDF2-HMAC-SHA256** with a **per-user salt** (`salt$digest`). Do not hash with `JWT_SECRET` (rotating the secret would invalidate every password).
- JWT `sub` is the username. Tickets are keyed by username.
- Seeded demo users (created on first bootstrap if missing):

  | Username | Password | Role |
  |---|---|---|
  | `admin` | `admin123` | admin |
  | `customer` | `customer123` | customer |

### LLM

There is **no mock LLM**. `OPENAI_API_KEY` is required.

Shared system prompt (all JSON completions):

> You are a customer-support agent. Reply with a single JSON object only.

The **user** message is different per agent (intake, triage, resolver, critic, manager). RAG uses embeddings only. Action and Escalation are code, not LLM.

| Setting | Typical production value | Used for |
|---|---|---|
| `MODEL_MINI` | `gpt-4o-mini` | Intake, triage, manager |
| `MODEL_FLAGSHIP` | `gpt-4o` | Resolver, critic |
| `MODEL_EMBEDDING` | `text-embedding-3-small` | KB vectors |

### Knowledge base

Markdown articles in `backend/kb/articles/` are seeded into Atlas when the collection is empty. Each article has `confidence_tag` (`auto_resolve` or `human_review`) and `proposed_action`.

Topics: password reset, account unlock, 2FA / MFA phone, app access, VPN, email **client** how-to, invoices, shipping, SSO, laptop replacement, software install, phishing, refunds.

### Guardrails (code, not only the critic model)

The critic LLM can suggest approval. Code still forces **human review** when any of these fire:

- `proposed_action == reset_2fa`
- `provision_access` without critic approval
- RAG score &lt; `RAG_CONFIDENCE_FLOOR` (default 0.45)
- resolver confidence &lt; `CONFIDENCE_FLOOR` (default 0.5)
- top KB hit `confidence_tag != auto_resolve`
- resolver/critic loop exceeds `MAX_TURNS` (default 3)

Admin **Approve** runs Action (simulated). **Reject** runs Escalation.

### Indexes

On startup the app ensures indexes, including unique sparse indexes on `users.username` and `users.email`. If Atlas already has the same key with different options (for example unique but not sparse), the app drops and recreates the index so bootstrap does not crash the serverless function.

## UI

| Route | Who | Purpose |
|---|---|---|
| `/login` | Public | Sign in / register |
| `/chat` | Signed-in | Live Chat → `POST /api/chat` |
| `/portal` | Signed-in | Customer’s tickets |
| `/admin` | Admin | Queue, stats, approve / reject |

## API (same origin on Vercel)

| Method | Path | Notes |
|---|---|---|
| `POST` | `/auth/register` | Store username + email + password |
| `POST` | `/auth/login` | Username + password → JWT |
| `POST` | `/api/chat` | Bearer token; runs the pipeline |
| `GET` | `/tickets` | Customer: own tickets; admin: all |
| `GET` | `/tickets/stats` | Admin only |
| `POST` | `/tickets/{id}/decision` | Admin `approved` \| `rejected` |
| `GET` | `/health` | `{ "ok": true }` |

Removed: `/api/email-intake`, `/api/email-poll`, SMTP/IMAP, Vercel cron, Mailpit worker.

## Repo layout

```
api/index.py          Vercel Python entry (loads FastAPI app)
backend/app/         Gateway, orchestrator, agents, auth, Mongo, KB seed
backend/kb/articles/ Markdown knowledge base
frontend/             Vite + React SPA
vercel.json           Build frontend → backend/static; FastAPI function
```

Vercel build copies `frontend/dist` into `backend/static`. FastAPI serves the SPA and restores paths if the platform collapses them to `/api`.

## Deploy on Vercel

1. Atlas → **Network Access** → allow `0.0.0.0/0` (serverless IPs are not static).
2. Keep `MONGO_URI` and `OPENAI_API_KEY` in Vercel env vars only (never git).
3. Root directory = repo root. Set the variables below, then deploy.

Hobby functions cap at **10s**. `maxDuration` is **60s** in `vercel.json`, which needs **Pro** for the full 8-agent LLM path. On Hobby, chat may time out even when login works.

```bash
npx vercel --prod
```

## Environment variables

Required:

| Name | Example |
|---|---|
| `OPENAI_API_KEY` | `sk-...` |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` |
| `MODEL_MINI` | `gpt-4o-mini` |
| `MODEL_FLAGSHIP` | `gpt-4o` |
| `MODEL_EMBEDDING` | `text-embedding-3-small` |
| `MONGO_URI` | Atlas `mongodb+srv://...` |
| `MONGO_DB` | `customer_support` |
| `JWT_SECRET` | long random string |

Optional:

| Name | Default |
|---|---|
| `JWT_EXPIRE_MINUTES` | `480` |
| `MAX_TURNS` | `3` |
| `CONFIDENCE_FLOOR` | `0.5` |
| `RAG_CONFIDENCE_FLOOR` | `0.45` |
| `CORS_ORIGINS` | `*` |
| `VITE_API_URL` | empty (same origin) |

See `.env.example`. Local `.env` is gitignored and is **not** uploaded to Vercel automatically.

## Local run

```bash
cp .env.example .env
# set OPENAI_API_KEY, MONGO_URI, JWT_SECRET

cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

cd ../frontend && npm install && npm run dev
```

Vite proxies `/auth`, `/api`, `/tickets`, and `/health` to `http://localhost:8000`.

```bash
docker compose up --build
```

starts API + UI only (no mail services).

## Sample chat tests

**Likely auto-resolve:** forgotten password, locked account, VPN, Outlook IMAP setup, resend invoice, shipping status, SSO loop, install approved software.

**Likely human queue:** 2FA reset, MFA phone change, provision Salesforce admin, laptop replacement, phishing, refund, off-topic / mixed requests.
