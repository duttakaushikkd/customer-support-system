# Test cases

Use **Live Chat** as `customer` / `customer123`, then **Admin Dashboard** as `admin` / `admin123`. On Hobby, chat may time out; retry or use Pro.

## Auth

| ID | Steps | Expected |
|---|---|---|
| A1 | Open `/login` | Form loads (not function crash) |
| A2 | Sign in `admin` / `admin123` | Redirect to `/admin` |
| A3 | Sign in `customer` / `customer123` | Redirect to `/chat` |
| A4 | Wrong password | Error, stay on login |
| A5 | Register new username + valid email + matching passwords | Session created, role customer |
| A6 | Register duplicate username or email | 400, message shown |
| A7 | Register without email | Browser required-field; API would 422/400 |
| A8 | Sign in with email instead of username | 401 |

## Auto-resolve (paste in chat)

| ID | Message | Expect roughly |
|---|---|---|
| C1 | I forgot my password and can't sign in. Can you send a password reset? | auto_resolved, reset_password / reply |
| C2 | My account is locked after too many failed login attempts. Please unlock it. | auto_resolved, unlock_account |
| C3 | I can't connect to the corporate VPN from home. What settings should I use? | auto_resolved, reply_kb |
| C4 | How do I set up Outlook with IMAP and SMTP for my work email? | auto_resolved, reply_kb |
| C5 | Please resend my latest billing invoice to my account email. | auto_resolved, send_invoice |
| C6 | Where is my order? I need the shipping and delivery status. | auto_resolved, reply_kb |
| C7 | SSO login keeps looping on the identity provider page. How do I fix it? | auto_resolved, reply_kb |
| C8 | How do I install approved software from the company catalog? | auto_resolved, reply_kb |

## Human queue

| ID | Message | Expect |
|---|---|---|
| H1 | I lost my authenticator app. Please reset my two-factor authentication. | pending_human_approval, flag `action_reset_2fa` |
| H2 | I need to update the phone number used for MFA. | human, reset_2fa |
| H3 | Please provision Salesforce admin access for my username. | human, provision_access |
| H4 | My laptop screen is cracked. I need a replacement laptop. | human |
| H5 | I clicked a phishing link that asked me to re-enter my password. | human, escalate_security |
| H6 | I was charged twice last month. I want a full refund. | human, refund |
| H7 | The office espresso machine is leaking. What is the policy? | human (low RAG / not auto_resolve) |
| H8 | I think I was phished and also I forgot my password and need 2FA reset and a refund. | human |

## Admin

| ID | Steps | Expected |
|---|---|---|
| D1 | After H1, open admin as admin | Ticket in pending queue |
| D2 | Approve a pending ticket | Status resolved / action executed |
| D3 | Reject a pending ticket | Status escalated |
| D4 | Customer opens portal | Own tickets only; no mailto link |
| D5 | Customer opens `/admin` | Redirected to chat |

## Health / deploy

| ID | Steps | Expected |
|---|---|---|
| P1 | `GET /health` | `{ "ok": true }` |
| P2 | `GET /api/email-poll` | Not found / not a cron job |
| P3 | Cold start after index change | Login still 200 (indexes compatible) |
