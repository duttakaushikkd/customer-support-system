import email
import imaplib
import json
import os
import time
import html
from email.header import decode_header
from email.message import Message

import html2text
import httpx

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
WEBHOOK_SECRET = os.environ.get("EMAIL_INTAKE_WEBHOOK_SECRET", "dev-webhook-secret")
IMAP_HOST = os.environ.get("IMAP_HOST", "localhost")
IMAP_PORT = int(os.environ.get("IMAP_PORT", "1143"))
IMAP_USER = os.environ.get("IMAP_USER", "support@example.com")
IMAP_PASSWORD = os.environ.get("IMAP_PASSWORD", "anything")
MAILPIT_API = os.environ.get("MAILPIT_API", f"http://{IMAP_HOST}:8025")
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "8"))

seen_imap: set[bytes] = set()
seen_mailpit: set[str] = set()
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


def post_intake(from_email: str, subject: str, body: str) -> None:
    url = f"{BACKEND_URL.rstrip('/')}/api/email-intake"
    resp = httpx.post(
        url,
        json={"from_email": from_email, "subject": subject, "body": body},
        headers={"X-Webhook-Secret": WEBHOOK_SECRET},
        timeout=120.0,
    )
    resp.raise_for_status()
    data = resp.json()
    print(json.dumps({"event": "email_intake", "ticket": data.get("ticket_number"), "status": data.get("status")}))


def poll_imap() -> bool:
    try:
        mailbox = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
        mailbox.login(IMAP_USER, IMAP_PASSWORD)
        mailbox.select("INBOX")
        _, data = mailbox.search(None, "UNSEEN")
        ids = data[0].split() if data[0] else []
        for msg_id in ids:
            if msg_id in seen_imap:
                continue
            _, fetched = mailbox.fetch(msg_id, "(RFC822)")
            raw = fetched[0][1]
            msg = email.message_from_bytes(raw)
            from_email = email.utils.parseaddr(_decode(msg.get("From")))[1]
            if not from_email:
                continue
            # skip our own automated replies
            if from_email.lower() == os.environ.get("SMTP_FROM", "support@example.com").lower():
                seen_imap.add(msg_id)
                continue
            subject = _decode(msg.get("Subject"))
            body = _body_from_message(msg).strip()
            post_intake(from_email, subject, body)
            seen_imap.add(msg_id)
        mailbox.logout()
        return True
    except Exception as exc:
        print(json.dumps({"event": "imap_error", "error": str(exc)}))
        return False


def poll_mailpit() -> None:
    try:
        resp = httpx.get(f"{MAILPIT_API}/api/v1/messages", timeout=10.0)
        resp.raise_for_status()
        messages = resp.json().get("messages", [])
        for item in reversed(messages):
            mid = item.get("ID")
            if not mid or mid in seen_mailpit:
                continue
            from_addr = (item.get("From") or {}).get("Address") or ""
            if from_addr.lower() == os.environ.get("SMTP_FROM", "support@example.com").lower():
                seen_mailpit.add(mid)
                continue
            detail = httpx.get(f"{MAILPIT_API}/api/v1/message/{mid}", timeout=10.0).json()
            html_body = detail.get("HTML") or ""
            text_body = detail.get("Text") or ""
            body = text_body.strip() or h2t.handle(html.unescape(html_body))
            subject = item.get("Subject") or ""
            if from_addr and body:
                post_intake(from_addr, subject, body)
            seen_mailpit.add(mid)
    except Exception as exc:
        print(json.dumps({"event": "mailpit_error", "error": str(exc)}))


def main() -> None:
    print(json.dumps({"event": "email_worker_start", "backend": BACKEND_URL, "imap": f"{IMAP_HOST}:{IMAP_PORT}"}))
    while True:
        ok = poll_imap()
        if not ok:
            poll_mailpit()
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
