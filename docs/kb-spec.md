# Knowledge base specification

## Source files

Markdown under `backend/kb/articles/`. Front matter (before `\n---\n`):

```
id: kb-001
title: Reset a forgotten password
category: account
confidence_tag: auto_resolve
proposed_action: reset_password
---
Body text…
```

## Seed

`seed_kb_if_needed` runs at bootstrap. If `kb_articles` already has at least as many documents as files on disk, seed is skipped. Otherwise articles are embedded with `MODEL_EMBEDDING` and upserted.

## Retrieval

`search_kb(query, limit=3)`:

1. Embed the query (category + subject + message).
2. Load articles with embeddings.
3. Cosine similarity vs stored vectors.
4. Return top `limit` with snippet (first ~400 chars of body).

RAG sets `rag_confidence` to the top score. Below `RAG_CONFIDENCE_FLOOR` → flag `low_rag_confidence`.

## Catalog

| ID | Title | Category | Tag | Action |
|---|---|---|---|---|
| kb-001 | Reset a forgotten password | account | auto_resolve | reset_password |
| kb-002 | Unlock a locked account | account | auto_resolve | unlock_account |
| kb-003 | Reset two-factor authentication | security | human_review | reset_2fa |
| kb-004 | Provision application access | access | human_review | provision_access |
| kb-005 | Connect to the corporate VPN | network | auto_resolve | reply_kb |
| kb-006 | Configure the email desktop client | email | auto_resolve | reply_kb |
| kb-007 | Billing invoice copy | billing | auto_resolve | send_invoice |
| kb-008 | Shipping and delivery status | shipping | auto_resolve | reply_kb |
| kb-009 | Single sign-on troubleshooting | access | auto_resolve | reply_kb |
| kb-010 | Request a laptop replacement | hardware | human_review | provision_access |
| kb-011 | Install approved software | software | auto_resolve | reply_kb |
| kb-012 | Report a phishing message | security | human_review | escalate_security |
| kb-013 | Request a refund | billing | human_review | refund |
| kb-014 | Update MFA phone number | security | human_review | reset_2fa |

`kb-006` is **how to configure a mail client**, not a product email channel.

## Policy

`confidence_tag != auto_resolve` on the top hit always forces human review (`kb_not_auto_resolve`), even if the critic LLM approves.
