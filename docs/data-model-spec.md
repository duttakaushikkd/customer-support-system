# Data model specification

Database name: `MONGO_DB` (default `customer_support`).

## Collection: `users`

| Field | Type | Notes |
|---|---|---|
| `_id` | ObjectId | |
| `username` | string | Unique, lowercase |
| `email` | string \| null | Unique when present, lowercase |
| `password_hash` | string | `salt$digest` |
| `role` | string | `admin` \| `customer` |
| `display_name` | string | |

## Collection: `tickets`

Full `TicketState` dump (see below). Query projections omit `_id`.

## Collection: `kb_articles`

| Field | Type |
|---|---|
| `article_id` | string, unique |
| `title` | string |
| `category` | string |
| `confidence_tag` | `auto_resolve` \| `human_review` |
| `proposed_action` | string |
| `body` | string |
| `embedding` | number[] | OpenAI embedding vector |

## Collection: `auditLog`

| Field | Type |
|---|---|
| `ticket_id` | string |
| `event` | string |
| `detail` | object |
| `at` | datetime UTC |

## Collection: `counters`

`{ _id: "ticket", seq: number }` — `find_one_and_update` increment. Ticket numbers: `INC{1000 + seq}`.

## TicketState

Defined in `backend/app/models/ticket_state.py`.

| Field | Type | Notes |
|---|---|---|
| `ticket_id` | UUID string | |
| `ticket_number` | string | |
| `channel` | `chat` \| `email` \| `portal` | New tickets: chat or portal |
| `customer_id` | string | Username |
| `customer_email` | string \| null | From JWT at chat time |
| `subject` | string \| null | |
| `message` | string | |
| `category` | string \| null | |
| `ticket_type` | string \| null | |
| `rag_hits` | RagHit[] | Up to 3 |
| `rag_confidence` | float | Top hit score |
| `resolver_confidence` | float | 0–1 |
| `proposed_action` | string \| null | |
| `draft_resolution` | string \| null | |
| `resolution` | string \| null | Customer-visible |
| `reply_subject` | string \| null | Unused for SMTP (no mail) |
| `critic_approved` | bool \| null | |
| `critic_reason` | string \| null | |
| `critic_requires_human` | bool \| null | LLM opinion before code |
| `guardrail_flags` | string[] | |
| `requires_human` | bool | |
| `status` | see statuses | |
| `reasoning_steps` | {agent, summary, detail, at}[] | |
| `loop_turn` | int | |
| `max_turns` | int | |
| `loop_metadata` | object | |
| `human_decision` | string \| null | `approved` \| `rejected` |
| `created_at` / `updated_at` | datetime | |

### Statuses

`new` → `in_progress` (intake) → `pending_human_approval` | `auto_resolved` → after human: `resolved` or `escalated`.

## Indexes

Created idempotently in `ensure_indexes`. If an existing index has the same key but different options (e.g. unique vs unique+sparse), it is dropped and recreated.

| Collection | Key | Options |
|---|---|---|
| tickets | `ticket_id` | unique |
| tickets | `ticket_number` | unique |
| tickets | `updated_at` | descending |
| tickets | `customer_id` | |
| tickets | `status` | |
| users | `email` | unique, sparse |
| users | `username` | unique, sparse |
| auditLog | `ticket_id` + `at` desc | |
| kb_articles | `article_id` | unique |

Sparse unique on email allows missing emails on old documents while enforcing uniqueness when set.
