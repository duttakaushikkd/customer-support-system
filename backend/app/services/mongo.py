from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, DESCENDING, MongoClient, ReturnDocument

from app.config import settings

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        kwargs: dict[str, Any] = {"serverSelectionTimeoutMS": 15000}
        if settings.mongo_uri.startswith("mongodb+srv://"):
            kwargs["tls"] = True
        _client = MongoClient(settings.mongo_uri, **kwargs)
    return _client


def db():
    return get_client()[settings.mongo_db]


def tickets():
    return db()["tickets"]


def audit_log():
    return db()["auditLog"]


def users():
    return db()["users"]


def counters():
    return db()["counters"]


def kb_articles():
    return db()["kb_articles"]


def ensure_indexes() -> None:
    tickets().create_index("ticket_id", unique=True)
    tickets().create_index("ticket_number", unique=True)
    tickets().create_index([("updated_at", DESCENDING)])
    tickets().create_index("customer_id")
    tickets().create_index("status")
    users().create_index("email", unique=True)
    audit_log().create_index([("ticket_id", ASCENDING), ("at", DESCENDING)])
    kb_articles().create_index("article_id", unique=True)


def next_ticket_number() -> str:
    doc = counters().find_one_and_update(
        {"_id": "ticket"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    seq = int(doc["seq"])
    return f"INC{1000 + seq}"


def save_ticket(state_dict: dict[str, Any]) -> None:
    state_dict["updated_at"] = datetime.now(timezone.utc)
    tickets().replace_one({"ticket_id": state_dict["ticket_id"]}, state_dict, upsert=True)


def get_ticket(ticket_id: str) -> dict[str, Any] | None:
    return tickets().find_one({"ticket_id": ticket_id}, {"_id": 0})


def list_tickets(limit: int = 200, customer_id: str | None = None) -> list[dict[str, Any]]:
    query: dict[str, Any] = {}
    if customer_id:
        query["customer_id"] = customer_id
    cursor = tickets().find(query, {"_id": 0}).sort("updated_at", DESCENDING).limit(limit)
    return list(cursor)


def write_audit(ticket_id: str, event: str, detail: dict[str, Any] | None = None) -> None:
    audit_log().insert_one(
        {
            "ticket_id": ticket_id,
            "event": event,
            "detail": detail or {},
            "at": datetime.now(timezone.utc),
        }
    )
