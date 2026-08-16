# Specifications

Canonical specs for the Customer Support Agent. The source of truth for behavior is this folder plus the running code.

| Spec | Contents |
|---|---|
| [architecture-spec.md](./architecture-spec.md) | System context, channels, Azure replacements, what was removed |
| [agent-pipeline-spec.md](./agent-pipeline-spec.md) | Orchestrator, agents, LLM prompts, guardrails, actions |
| [api-spec.md](./api-spec.md) | HTTP API, request/response shapes, errors |
| [auth-spec.md](./auth-spec.md) | Register, login, JWT, password hashing, roles |
| [data-model-spec.md](./data-model-spec.md) | Atlas collections, ticket state, indexes |
| [kb-spec.md](./kb-spec.md) | Knowledge-base articles, tags, RAG |
| [frontend-spec.md](./frontend-spec.md) | SPA routes, session, pages |
| [deployment-spec.md](./deployment-spec.md) | Vercel, env vars, local run |
| [test-cases.md](./test-cases.md) | Manual chat and admin test cases |

Original architecture drawing: [architecture-diagram.drawio](./architecture-diagram.drawio).
