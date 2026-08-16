from app.models.ticket_state import TicketState
from app.services.llm import complete_json

CATEGORIES = [
    "account",
    "security",
    "access",
    "network",
    "email",
    "billing",
    "shipping",
    "hardware",
    "software",
    "general",
]


def run(state: TicketState) -> TicketState:
    text = (state.message + " " + (state.subject or "")).lower()
    guessed = "general"
    if any(w in text for w in ("2fa", "mfa", "authenticator", "two-factor")):
        guessed = "security"
    elif any(w in text for w in ("password", "locked", "unlock", "login")):
        guessed = "account"
    elif any(w in text for w in ("access", "permission", "provision", "role")):
        guessed = "access"
    elif "vpn" in text:
        guessed = "network"
    elif "invoice" in text or "bill" in text or "refund" in text:
        guessed = "billing"
    elif "phish" in text:
        guessed = "security"
    elif "laptop" in text:
        guessed = "hardware"
    elif "ship" in text or "delivery" in text:
        guessed = "shipping"

    result = complete_json(
        (
            "Classify this ticket. Return JSON with category (one of "
            f"{CATEGORIES}) and ticket_type (how-to, incident, request, security).\n"
            f"message={state.message}"
        ),
        fallback={"category": guessed, "ticket_type": "incident"},
    )
    category = result.get("category") if result.get("category") in CATEGORIES else guessed
    state.category = category
    state.ticket_type = result.get("ticket_type") or "incident"
    state.add_step("Triage", f"Classified as {state.category}/{state.ticket_type}")
    return state
