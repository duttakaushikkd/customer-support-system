# Agent pipeline specification

## Orchestrator

Module: `backend/app/orchestrator.py`.

1. Assign `ticket_number` (`INC` + sequence from `counters`).
2. Persist ticket.
3. Run **Intake → Triage → RAG** once each (persist after each).
4. Loop **Resolver → Critic** while `loop_turn <= MAX_TURNS` (default 3):
   - Stop if `requires_human`.
   - Stop if `critic_approved`.
   - Else increment turn and retry Resolver.
5. If max turns exceeded without approval or human flag → set `requires_human`, flag `max_turns_exceeded`.
6. **Manager** sets route `auto` or `human`.
7. If not human → **Action**. If human → hold; no Action until admin decides.

### Human resume

`POST /tickets/{ticket_id}/decision`

- `approved` → Action (status `resolved` if it was pending).
- `rejected` → Escalation (status `escalated`).

## Agents

| Agent | LLM? | Responsibility |
|---|---|---|
| Intake | Mini | Normalize `cleaned_message`, `subject`, `customer_intent` |
| Triage | Mini | `category` + `ticket_type` |
| RAG | No | Embed query, cosine search KB, top 3 hits |
| Resolver | Flagship | `draft_resolution`, `proposed_action`, `resolver_confidence` |
| Critic | Flagship | `approved`, `reason`, `requires_human` then **code guardrails** |
| Manager | Mini | `route` auto\|human (human forced if `requires_human`) |
| Action | No | Apply simulated action label; set `auto_resolved` / `resolved` |
| Escalation | No | Status `escalated`, customer-facing escalation text |

Triage categories: `account`, `security`, `access`, `network`, `email`, `billing`, `shipping`, `hardware`, `software`, `general`.

Ticket types: `how-to`, `incident`, `request`, `security`.

Heuristic hints in triage (before/with LLM): 2FA/MFA → security; password/lock → account; VPN → network; invoice/refund → billing; etc.

## LLM contract

All completions go through `complete_json` (`backend/app/services/llm.py`).

**System prompt (every call):**

```
You are a customer-support agent. Reply with a single JSON object only.
```

- `temperature`: 0.2
- `response_format`: `json_object`
- Non-JSON or non-object → runtime error (no mock fallback)
- `OPENAI_API_KEY` required

Resolver and Critic use the flagship model; Intake, Triage, Manager use mini.

## Deterministic guardrails

Applied in Critic after the LLM JSON (`_apply_deterministic_guardrails`). Any match sets `requires_human = true`.

| Condition | Flag |
|---|---|
| `proposed_action == reset_2fa` | `action_reset_2fa` |
| `provision_access` and critic did not approve | `provision_access_unapproved` |
| RAG score &lt; `RAG_CONFIDENCE_FLOOR` (0.45) | `low_rag_confidence` |
| Resolver confidence &lt; `CONFIDENCE_FLOOR` (0.5) | `resolver_confidence_below_floor` |
| No top hit or `confidence_tag != auto_resolve` | `kb_not_auto_resolve` |
| Loop exhausted | `max_turns_exceeded` |

Manager cannot override `requires_human`.

## Simulated actions

| `proposed_action` | Label (Action agent) |
|---|---|
| `reset_password` | Issued a password-reset email (simulated). |
| `unlock_account` | Unlocked the customer account (simulated). |
| `reset_2fa` | Queued 2FA reset after human approval (simulated). |
| `provision_access` | Provisioned requested access (simulated). |
| `send_invoice` | Resent the latest invoice (simulated). |
| `refund` | Submitted refund request (simulated). |
| `escalate_security` | Opened a security ops case (simulated). |
| `reply_kb` | Sent knowledge-base guidance. |

Unknown actions still execute as `Executed {action} (simulated).`

## Persistence and audit

Every pipeline step persists the full ticket document. Audit events include `action_executed`, `pipeline_complete`, `human_decision`, `escalated`.
