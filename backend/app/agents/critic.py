from app.config import settings
from app.models.ticket_state import TicketState
from app.services.llm import complete_json


def _apply_deterministic_guardrails(state: TicketState, llm_requires_human: bool) -> None:
    flags = list(state.guardrail_flags)
    requires = bool(llm_requires_human)

    if state.proposed_action == "reset_2fa":
        flags.append("action_reset_2fa")
        requires = True

    if state.proposed_action == "provision_access" and not state.critic_approved:
        flags.append("provision_access_unapproved")
        requires = True

    if "low_rag_confidence" in flags or state.rag_confidence < settings.rag_confidence_floor:
        if "low_rag_confidence" not in flags:
            flags.append("low_rag_confidence")
        requires = True

    if state.resolver_confidence < settings.confidence_floor:
        flags.append("resolver_confidence_below_floor")
        requires = True

    top = state.rag_hits[0] if state.rag_hits else None
    if top is None or top.confidence_tag != "auto_resolve":
        flags.append("kb_not_auto_resolve")
        requires = True

    # de-dupe while preserving order
    seen: set[str] = set()
    unique = []
    for f in flags:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    state.guardrail_flags = unique
    state.requires_human = requires


def run(state: TicketState) -> TicketState:
    citations = ", ".join(f"{h.title} ({h.confidence_tag}, {h.score:.2f})" for h in state.rag_hits)
    fallback = {
        "approved": state.resolver_confidence >= settings.confidence_floor,
        "reason": "Heuristic critic: check confidence and action type.",
        "requires_human": state.resolver_confidence < settings.confidence_floor,
    }
    result = complete_json(
        (
            "Review this draft. Return JSON with approved (bool), reason (string), "
            "requires_human (bool).\n"
            f"draft={state.draft_resolution}\n"
            f"resolver_confidence={state.resolver_confidence}\n"
            f"proposed_action={state.proposed_action}\n"
            f"rag_citations={citations}"
        ),
        flagship=True,
        fallback=fallback,
    )
    state.critic_approved = bool(result.get("approved"))
    state.critic_reason = str(result.get("reason") or fallback["reason"])
    state.critic_requires_human = bool(result.get("requires_human"))
    _apply_deterministic_guardrails(state, bool(state.critic_requires_human))
    state.add_step(
        "Critic",
        "Guardrails "
        + ("fired → human review" if state.requires_human else "clear"),
        f"{state.critic_reason}; flags={state.guardrail_flags}",
    )
    return state
