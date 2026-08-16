import json
import time
from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, DESCENDING, MongoClient, ReturnDocument
from pymongo.errors import OperationFailure

from app.config import settings

_DEBUG_LOG = "/Users/kaushikdutta/Documents/GitHub/customer-support-system/.cursor/debug-164638.log"


def _agent_log(hypothesis_id: str, location: str, message: str, data: dict[str, Any]) -> None:
    # #region agent log
    payload = {
        "sessionId": "164638",
        "runId": "post-fix",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    line = json.dumps(payload)
    try:
        with open(_DEBUG_LOG, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass
    print(line, flush=True)
    # #endregion

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


def _ensure_index(collection, keys, **kwargs) -> str:
    name = collection.create_index(keys, **kwargs)
    return name


def _index_options_match(info: dict[str, Any], unique: bool, sparse: bool) -> bool:
    return bool(info.get("unique")) == unique and bool(info.get("sparse")) == sparse


def ensure_indexes() -> None:
    specs: list[tuple[Any, Any, dict[str, Any]]] = [
        (tickets(), "ticket_id", {"unique": True}),
        (tickets(), "ticket_number", {"unique": True}),
        (tickets(), [("updated_at", DESCENDING)], {}),
        (tickets(), "customer_id", {}),
        (tickets(), "status", {}),
        (users(), "email", {"unique": True, "sparse": True}),
        (users(), "username", {"unique": True, "sparse": True}),
        (audit_log(), [("ticket_id", ASCENDING), ("at", DESCENDING)], {}),
        (kb_articles(), "article_id", {"unique": True}),
    ]
    for collection, keys, options in specs:
        unique = bool(options.get("unique"))
        sparse = bool(options.get("sparse"))
        existing = collection.index_information()
        key_tuple = ((keys, 1),) if isinstance(keys, str) else tuple(keys)
        matched_name = None
        for name, info in existing.items():
            if name == "_id_":
                continue
            if tuple(info.get("key") or ()) == key_tuple:
                matched_name = name
                same = _index_options_match(info, unique, sparse)
                # #region agent log
                _agent_log(
                    "A",
                    "mongo.py:ensure_indexes",
                    "found existing index for key",
                    {
                        "collection": collection.name,
                        "index": name,
                        "unique": bool(info.get("unique")),
                        "sparse": bool(info.get("sparse")),
                        "wanted_unique": unique,
                        "wanted_sparse": sparse,
                        "options_match": same,
                    },
                )
                # #endregion
                if same:
                    break
                collection.drop_index(name)
                matched_name = None
                # #region agent log
                _agent_log(
                    "A",
                    "mongo.py:ensure_indexes",
                    "dropped incompatible index",
                    {"collection": collection.name, "index": name},
                )
                # #endregion
                break
        if matched_name:
            continue
        try:
            created = _ensure_index(collection, keys, **options)
            # #region agent log
            _agent_log(
                "B",
                "mongo.py:ensure_indexes",
                "created index",
                {"collection": collection.name, "index": created, "options": options},
            )
            # #endregion
        except OperationFailure as exc:
            # #region agent log
            _agent_log(
                "C",
                "mongo.py:ensure_indexes",
                "create_index failed",
                {
                    "collection": collection.name,
                    "code": getattr(exc, "code", None),
                    "error": str(exc)[:300],
                },
            )
            # #endregion
            raise


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
