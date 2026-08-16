from app.config import settings
from app.models.ticket_state import RagHit, TicketState
from app.services.kb import search_kb


def run(state: TicketState) -> TicketState:
    query = f"{state.category or ''} {state.subject or ''} {state.message}"
    raw_hits = search_kb(query, limit=3)
    hits: list[RagHit] = []
    for h in raw_hits:
        hits.append(
            RagHit(
                article_id=str(h.get("article_id", "")),
                title=str(h.get("title", "Untitled")),
                snippet=str(h.get("snippet", "")),
                score=float(h.get("score") or 0.0),
                confidence_tag=str(h.get("confidence_tag", "human_review")),
                proposed_action=h.get("proposed_action"),
                category=h.get("category"),
            )
        )
    state.rag_hits = hits
    state.rag_confidence = hits[0].score if hits else 0.0
    if state.rag_confidence < settings.rag_confidence_floor:
        if "low_rag_confidence" not in state.guardrail_flags:
            state.guardrail_flags.append("low_rag_confidence")
    titles = ", ".join(h.title for h in hits) or "none"
    state.add_step(
        "RAG",
        f"Retrieved {len(hits)} KB articles (top score {state.rag_confidence:.2f})",
        titles,
    )
    return state
