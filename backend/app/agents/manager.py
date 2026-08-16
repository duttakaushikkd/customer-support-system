from app.models.ticket_state import TicketState
from app.services.llm import complete_json


def run(state: TicketState) -> TicketState:
    decision = "human" if state.requires_human else "auto"
    result = complete_json(
        (
            "Route this ticket. Return JSON with route (auto|human) and summary.\n"
            f"requires_human={state.requires_human}\nflags={state.guardrail_flags}\n"
            f"confidence={state.resolver_confidence}"
        ),
        fallback={"route": decision, "summary": f"Manager route: {decision}"},
    )
    route = result.get("route") or decision
    if state.requires_human:
        route = "human"
        state.status = "pending_human_approval"
        state.resolution = (
            "Thanks — we have your request. A specialist will review it shortly. "
            f"Your ticket number is {state.ticket_number}."
        )
    else:
        route = "auto"
        state.status = "auto_resolved"
        state.resolution = state.draft_resolution
    state.loop_metadata["manager_route"] = route
    state.loop_metadata["manager_summary"] = result.get("summary") or f"Routed {route}"
    state.add_step("Manager", f"Routed to {route}", state.loop_metadata["manager_summary"])
    return state
