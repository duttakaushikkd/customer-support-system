from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.api.deps import get_current_user, require_admin
from app.models.ticket_state import TicketState
from app.orchestrator import resume_after_human, run_pipeline
from app.services import mongo

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    display_name: str | None = None


class ChatRequest(BaseModel):
    message: str
    user_id: str | None = None
    channel: str = "chat"


class DecisionRequest(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")


def _build_ticket_response(state: TicketState) -> dict[str, Any]:
    holding = state.status == "pending_human_approval"
    return {
        "ticket_id": state.ticket_id,
        "ticket_number": state.ticket_number,
        "status": state.status,
        "channel": state.channel,
        "ticket_type": state.ticket_type,
        "category": state.category,
        "resolution": state.resolution,
        "reply_subject": state.reply_subject or f"Re: {state.subject or state.ticket_number}",
        "requires_human": state.requires_human,
        "holding": holding,
        "resolver_confidence": state.resolver_confidence,
        "reasoning_steps": [s.model_dump(mode="json") for s in state.reasoning_steps],
        "loop_metadata": state.loop_metadata,
        "guardrail_flags": state.guardrail_flags,
        "proposed_action": state.proposed_action,
        "rag_hits": [h.model_dump(mode="json") for h in state.rag_hits],
    }


@router.post("/auth/register")
def register(payload: RegisterRequest) -> dict:
    from app.services.auth import auth_response, register_user

    try:
        user = register_user(payload.username, payload.password, str(payload.email), payload.display_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return auth_response(user)


@router.post("/auth/login")
def login(payload: LoginRequest) -> dict:
    from app.services.auth import auth_response, authenticate

    user = authenticate(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return auth_response(user)


@router.post("/api/chat")
def chat(payload: ChatRequest, user: Annotated[dict, Depends(get_current_user)]) -> dict:
    customer_id = payload.user_id or user.get("username") or user["sub"]
    state = TicketState(
        channel="chat" if payload.channel in {"chat", "portal"} else "chat",
        customer_id=customer_id,
        customer_email=user.get("email"),
        message=payload.message,
        subject=payload.message[:80],
    )
    if payload.channel == "portal":
        state.channel = "portal"
    state = run_pipeline(state)
    return _build_ticket_response(state)


@router.get("/tickets")
def get_tickets(
    user: Annotated[dict, Depends(get_current_user)],
    limit: int = 200,
) -> list[dict]:
    if user.get("role") == "admin":
        return mongo.list_tickets(limit=limit)
    return mongo.list_tickets(limit=limit, customer_id=user["sub"])


@router.get("/tickets/stats")
def get_stats(_admin: Annotated[dict, Depends(require_admin)]) -> dict:
    docs = mongo.list_tickets(limit=5000)
    unique_users = {d.get("customer_id") for d in docs}
    resolved = [d for d in docs if d.get("status") in {"auto_resolved", "resolved"}]
    escalated = [d for d in docs if d.get("status") == "escalated"]
    not_resolved = [d for d in docs if d.get("status") not in {"auto_resolved", "resolved", "escalated"}]
    by_channel: dict[str, int] = {}
    for d in docs:
        ch = d.get("channel") or "unknown"
        by_channel[ch] = by_channel.get(ch, 0) + 1
    total = len(docs) or 1
    return {
        "unique_users": len(unique_users),
        "total_tickets": len(docs),
        "resolved": len(resolved),
        "escalated": len(escalated),
        "not_resolved": len(not_resolved),
        "pending_human_approval": sum(1 for d in docs if d.get("status") == "pending_human_approval"),
        "resolution_rate_pct": round(100.0 * len(resolved) / total, 1),
        "by_channel": by_channel,
    }


@router.post("/tickets/{ticket_id}/decision")
def post_decision(
    ticket_id: str,
    payload: DecisionRequest,
    _admin: Annotated[dict, Depends(require_admin)],
) -> dict:
    doc = mongo.get_ticket(ticket_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    state = TicketState.model_validate(doc)
    state = resume_after_human(state, payload.decision)
    return _build_ticket_response(state)


@router.get("/health")
@router.get("/api/health")
def health() -> dict:
    return {"ok": True}
