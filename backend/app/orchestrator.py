from app.agents import action, critic, escalation, intake, manager, rag, resolver, triage
from app.config import settings
from app.models.ticket_state import TicketState
from app.services import mongo


def persist(state: TicketState) -> None:
    mongo.save_ticket(state.model_dump())


def run_pipeline(state: TicketState) -> TicketState:
    if not state.ticket_number:
        state.ticket_number = mongo.next_ticket_number()
    state.max_turns = settings.max_turns
    persist(state)

    for fn in (intake.run, triage.run, rag.run):
        state = fn(state)
        persist(state)

    while state.loop_turn <= state.max_turns:
        state = resolver.run(state)
        persist(state)
        state = critic.run(state)
        persist(state)
        if state.requires_human:
            break
        if state.critic_approved:
            break
        state.loop_turn += 1
        state.add_step(
            "Orchestrator",
            f"Retry resolver (turn {state.loop_turn}/{state.max_turns})",
        )
        persist(state)

    if state.loop_turn > state.max_turns and not state.requires_human and not state.critic_approved:
        state.requires_human = True
        state.guardrail_flags.append("max_turns_exceeded")
        persist(state)

    state.loop_metadata.update(
        {
            "loop_turn": state.loop_turn,
            "max_turns": state.max_turns,
            "guardrail_flags": state.guardrail_flags,
            "requires_human": state.requires_human,
            "resolver_confidence": state.resolver_confidence,
        }
    )
    state = manager.run(state)
    persist(state)

    if not state.requires_human:
        state = action.run(state)
        persist(state)

    mongo.write_audit(state.ticket_id, "pipeline_complete", {"status": state.status})
    return state


def resume_after_human(state: TicketState, decision: str) -> TicketState:
    state.human_decision = decision
    if decision == "approved":
        state.add_step("Human", "Approved in Admin Dashboard")
        persist(state)
        state = action.run(state)
    else:
        state.add_step("Human", "Rejected and escalated")
        persist(state)
        state = escalation.run(state)
    persist(state)
    mongo.write_audit(state.ticket_id, "human_decision", {"decision": decision})
    return state
