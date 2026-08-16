# Deployment specification

## Vercel

| Setting | Value |
|---|---|
| Root | Repository root |
| Entry | `api/index.py` (adds `backend` to `sys.path`, exports FastAPI `app`) |
| Install | `npm --prefix frontend install && pip install -r requirements.txt` |
| Build | Frontend production build → `backend/static` |
| Function | `api/index.py`, `includeFiles: backend/**`, `maxDuration: 60` |
| Cron | None |

Hobby plan still enforces ~**10s** wall time. Full pipeline (several LLM calls) typically needs **Pro**.

Atlas **Network Access** must include `0.0.0.0/0`.

Env vars are **not** taken from committed `.env`. Set them in the Vercel project (Production / Preview / Development).

## Required environment

| Name | Purpose |
|---|---|
| `OPENAI_API_KEY` | LLM + embeddings |
| `OPENAI_BASE_URL` | Default `https://api.openai.com/v1` |
| `MODEL_MINI` | Intake, triage, manager |
| `MODEL_FLAGSHIP` | Resolver, critic |
| `MODEL_EMBEDDING` | KB vectors |
| `MONGO_URI` | Atlas connection string |
| `MONGO_DB` | Database name |
| `JWT_SECRET` | HS256 signing |

## Optional environment

| Name | Default |
|---|---|
| `JWT_EXPIRE_MINUTES` | 480 |
| `MAX_TURNS` | 3 |
| `CONFIDENCE_FLOOR` | 0.5 |
| `RAG_CONFIDENCE_FLOOR` | 0.45 |
| `CORS_ORIGINS` | `*` |
| `VITE_API_URL` | empty |

Removed (do not set for this product): `SMTP_*`, `IMAP_*`, `SUPPORT_MAILTO`, `EMAIL_INTAKE_WEBHOOK_SECRET`, `CRON_SECRET`, `MOCK_LLM`.

Template: `.env.example`.

## Local

```bash
cp .env.example .env
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
cd ../frontend && npm install && npm run dev
```

`docker compose up --build` runs backend + frontend only.

## Bootstrap failure mode

If Mongo index create fails (name clash, network), FastAPI lifespan fails and Vercel returns **FUNCTION_INVOCATION_FAILED** for every path including `/login`. Index ensure must be idempotent (drop incompatible same-key indexes, then create).
