from app.models.ticket_state import TicketState
from app.services.llm import complete_json


def run(state: TicketState) -> TicketState:
    fallback = {
        "cleaned_message": state.message.strip(),
        "subject": state.subject or (state.message[:72] + ("…" if len(state.message) > 72 else "")),
        "customer_intent": "support_request",
    }
    result = complete_json(
        (
            "Normalize this support request. Return JSON with keys "
            "cleaned_message, subject, customer_intent.\n\n"
            f"channel={state.channel}\nsubject={state.subject}\nmessage={state.message}"
        ),
        fallback=fallback,
    )
    state.message = result.get("cleaned_message") or fallback["cleaned_message"]
    state.subject = result.get("subject") or fallback["subject"]
    state.add_step(
        "Intake",
        "Normalized inbound request",
        result.get("customer_intent"),
    )
    state.status = "in_progress"
    return state
