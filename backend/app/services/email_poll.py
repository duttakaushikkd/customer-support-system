"""One-shot IMAP poll used by Vercel Cron. The always-on worker still uses email-worker/."""

from __future__ import annotations

import email
import imaplib
from email.header import decode_header
from email.message import Message

import html2text

from app.config import settings
from app.models.ticket_state import TicketState
from app.orchestrator import run_pipeline
from app.services.smtp import send_reply

h2t = html2text.HTML2Text()
h2t.ignore_links = False


def _decode(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    out = []
    for text, enc in parts:
        if isinstance(text, bytes):
            out.append(text.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out)


def _body_from_message(msg: Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                payload = part.get_payload(decode=True) or b""
                return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
            if ctype == "text/html":
                payload = part.get_payload(decode=True) or b""
                html_body = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                return h2t.handle(html_body)
    payload = msg.get_payload(decode=True) or b""
    text = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
    if "<html" in text.lower():
        return h2t.handle(text)
    return text


def _ingest(from_email: str, subject: str, body: str) -> str:
    state = TicketState(
        channel="email",
        customer_id=from_email,
        customer_email=from_email,
        subject=subject,
        message=body,
        reply_subject=f"Re: {subject}" if subject else None,
    )
    state = run_pipeline(state)
    if from_email and state.resolution:
        try:
            send_reply(from_email, state.reply_subject or f"Re: {subject}", state.resolution)
        except Exception:
            pass
    return state.ticket_number


def poll_once() -> dict:
    import os

    host = os.environ.get("IMAP_HOST", "")
    if not host:
        return {"ok": True, "skipped": True, "reason": "IMAP_HOST not set"}
    port = int(os.environ.get("IMAP_PORT", "993"))
    user = os.environ.get("IMAP_USER", "")
    password = os.environ.get("IMAP_PASSWORD", "")
    processed: list[str] = []
    mailbox = imaplib.IMAP4_SSL(host, port) if port == 993 else imaplib.IMAP4(host, port)
    mailbox.login(user, password)
    mailbox.select("INBOX")
    _, data = mailbox.search(None, "UNSEEN")
    ids = data[0].split() if data[0] else []
    for msg_id in ids:
        _, fetched = mailbox.fetch(msg_id, "(RFC822)")
        raw = fetched[0][1]
        msg = email.message_from_bytes(raw)
        from_email = email.utils.parseaddr(_decode(msg.get("From")))[1]
        if not from_email or from_email.lower() == settings.smtp_from.lower():
            continue
        ticket = _ingest(from_email, _decode(msg.get("Subject")), _body_from_message(msg).strip())
        processed.append(ticket)
    mailbox.logout()
    return {"ok": True, "tickets": processed}
