# Customer Support Agent

Multi-agent customer support system from `docs/architecture-diagram.drawio`, implemented without Azure. Production target is **Vercel + MongoDB Atlas**.

## Architecture

Customers reach the same FastAPI gateway through **Live Chat** or the **Customer Portal**. The orchestrator runs Intake → Triage → RAG → Resolver → Critic → Manager. High-confidence tickets go to the Action agent; low confidence or a fired guardrail goes to the Admin Dashboard human queue.

| Diagram | This repo |
|---|---|
| Azure OpenAI | OpenAI-compatible API (`OPENAI_BASE_URL`) |
| Azure AI Search | MongoDB Atlas `kb_articles` (embeddings + cosine search) |
| Cosmos DB | MongoDB Atlas (`tickets`, `auditLog`) |
| Entra / MSAL | Local JWT login |
| Application Insights | Structured JSON logs |

## Deploy on Vercel

1. In [MongoDB Atlas](https://cloud.mongodb.com) → **Network Access**, add `0.0.0.0/0` (Vercel serverless IPs are not static).
2. **Rotate the database password** if it was ever pasted into chat or committed, then use the new URI only as an environment variable.
3. Import this GitHub repo in [Vercel](https://vercel.com/new) (root directory = repo root).
4. Set environment variables (see the table below). `OPENAI_API_KEY` is required.

5. Deploy. Open the Vercel URL and sign in:

- username `customer` / `customer123`
- username `admin` / `admin123`

Hobby plan functions time out at 10s; the full LLM pipeline often needs **Pro** (`maxDuration` is set to 60s).

## Environment variables

Required:

| Name | Example |
|---|---|
| `OPENAI_API_KEY` | `sk-...` from [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` |
| `MODEL_MINI` | `gpt-4o-mini` |
| `MODEL_FLAGSHIP` | `gpt-4o` |
| `MODEL_EMBEDDING` | `text-embedding-3-small` |
| `MONGO_URI` | Atlas `mongodb+srv://...` URI |
| `MONGO_DB` | `customer_support` |
| `JWT_SECRET` | long random string |

Recommended:

| Name | Example |
|---|---|
| `JWT_EXPIRE_MINUTES` | `480` |
| `MAX_TURNS` | `3` |
| `CONFIDENCE_FLOOR` | `0.5` |
| `RAG_CONFIDENCE_FLOOR` | `0.45` |
| `CORS_ORIGINS` | `*` |
| `VITE_API_URL` | empty on Vercel |

Vercel treats this repo as a FastAPI app, so the Vite build is copied into `backend/static` and the API serves the SPA (same origin as `/health`, `/auth/login`, `/api/chat`, `/tickets`).

CLI (from the repo root, after `npx vercel login`):

```bash
npx vercel --prod
```

You will be prompted for the env vars above if they are not already set on the project.

## Local run (Atlas)

```bash
cp .env.example .env
# set MONGO_URI to your Atlas connection string

cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

cd ../frontend && npm install && npm run dev
```

## Guardrails (deterministic)

The critic model may suggest approval, but code still forces human review when any of these fire:

- `proposed_action == reset_2fa`
- `provision_access` without LLM approval
- RAG score &lt; 0.45 (`low_rag_confidence`)
- resolver confidence &lt; 50%
- top KB article `confidence_tag != auto_resolve`
