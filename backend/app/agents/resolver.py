from app.models.ticket_state import TicketState
from app.services.llm import complete_json


def _heuristic(state: TicketState) -> dict:
    top = state.rag_hits[0] if state.rag_hits else None
    action = (top.proposed_action if top else None) or "reply_kb"
    citations = "\n".join(f"- {h.title}: {h.snippet}" for h in state.rag_hits) or "No KB hits."
    resolution = (
        f"Thanks for contacting support. Ticket {state.ticket_number} is in progress.\n\n"
        f"Based on our knowledge base ({top.title if top else 'general guidance'}):\n"
        f"{top.snippet if top else state.message}\n\n"
        "If this does not resolve the issue, a specialist will follow up."
    )
    confidence = 0.82 if top and top.confidence_tag == "auto_resolve" else 0.42
    if top:
        confidence = min(0.95, max(0.2, top.score if top.score > 1 else confidence))
        # cosine scores are 0-1; use a blend
        confidence = 0.35 + 0.6 * min(1.0, max(0.0, top.score))
        if top.confidence_tag != "auto_resolve":
            confidence = min(confidence, 0.48)
    return {
        "draft_resolution": resolution,
        "proposed_action": action,
        "resolver_confidence": round(confidence, 2),
        "citations_used": citations,
    }


def run(state: TicketState) -> TicketState:
    fallback = _heuristic(state)
    citations = fallback["citations_used"]
    result = complete_json(
        (
            "Draft a customer-ready resolution. Return JSON with "
            "draft_resolution, proposed_action, resolver_confidence (0-1).\n"
            f"message={state.message}\ncategory={state.category}\n"
            f"kb:\n{citations}"
        ),
        flagship=True,
        fallback=fallback,
    )
    state.draft_resolution = result.get("draft_resolution") or fallback["draft_resolution"]
    state.proposed_action = result.get("proposed_action") or fallback["proposed_action"]
    try:
        state.resolver_confidence = float(result.get("resolver_confidence", fallback["resolver_confidence"]))
    except (TypeError, ValueError):
        state.resolver_confidence = fallback["resolver_confidence"]
    state.resolver_confidence = max(0.0, min(1.0, state.resolver_confidence))
    state.add_step(
        "Resolver",
        f"Drafted {state.proposed_action} at {int(state.resolver_confidence * 100)}% confidence",
        state.draft_resolution[:240] if state.draft_resolution else None,
    )
    return state
