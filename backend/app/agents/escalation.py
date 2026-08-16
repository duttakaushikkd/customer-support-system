from app.models.ticket_state import TicketState
from app.services import mongo


def run(state: TicketState) -> TicketState:
    state.status = "escalated"
    state.resolution = (
        f"Ticket {state.ticket_number} was escalated to a specialist. "
        "A human agent will contact you with next steps."
    )
    mongo.write_audit(
        state.ticket_id,
        "escalated",
        {"reason": state.critic_reason, "flags": state.guardrail_flags},
    )
    state.add_step("Escalation", "Ticket escalated after human rejection")
    return state
