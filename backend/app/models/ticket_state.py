from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


Channel = Literal["chat", "email", "portal"]
TicketStatus = Literal[
    "new",
    "in_progress",
    "pending_human_approval",
    "auto_resolved",
    "resolved",
    "escalated",
]


class ReasoningStep(BaseModel):
    agent: str
    summary: str
    detail: str | None = None
    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RagHit(BaseModel):
    article_id: str
    title: str
    snippet: str
    score: float
    confidence_tag: str
    proposed_action: str | None = None
    category: str | None = None


class TicketState(BaseModel):
    ticket_id: str = Field(default_factory=lambda: str(uuid4()))
    ticket_number: str = ""
    channel: Channel = "chat"
    customer_id: str
    customer_email: str | None = None
    subject: str | None = None
    message: str
    category: str | None = None
    ticket_type: str | None = None
    rag_hits: list[RagHit] = Field(default_factory=list)
    rag_confidence: float = 0.0
    resolver_confidence: float = 0.0
    proposed_action: str | None = None
    draft_resolution: str | None = None
    resolution: str | None = None
    reply_subject: str | None = None
    critic_approved: bool | None = None
    critic_reason: str | None = None
    critic_requires_human: bool | None = None
    guardrail_flags: list[str] = Field(default_factory=list)
    requires_human: bool = False
    status: TicketStatus = "new"
    reasoning_steps: list[ReasoningStep] = Field(default_factory=list)
    loop_turn: int = 1
    max_turns: int = 3
    loop_metadata: dict[str, Any] = Field(default_factory=dict)
    human_decision: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def add_step(self, agent: str, summary: str, detail: str | None = None) -> None:
        self.reasoning_steps.append(
            ReasoningStep(agent=agent, summary=summary, detail=detail)
        )
        self.updated_at = datetime.now(timezone.utc)
