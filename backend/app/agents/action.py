from app.models.ticket_state import TicketState
from app.services import mongo


ACTION_LABELS = {
    "reset_password": "Issued a password-reset email (simulated).",
    "unlock_account": "Unlocked the customer account (simulated).",
    "reset_2fa": "Queued 2FA reset after human approval (simulated).",
    "provision_access": "Provisioned requested access (simulated).",
    "send_invoice": "Resent the latest invoice (simulated).",
    "refund": "Submitted refund request (simulated).",
    "escalate_security": "Opened a security ops case (simulated).",
    "reply_kb": "Sent knowledge-base guidance.",
}


def run(state: TicketState) -> TicketState:
    action = state.proposed_action or "reply_kb"
    label = ACTION_LABELS.get(action, f"Executed {action} (simulated).")
    state.resolution = state.draft_resolution or state.resolution or label
    if state.status == "pending_human_approval":
        state.status = "resolved"
    elif state.status != "auto_resolved":
        state.status = "auto_resolved"
    state.reply_subject = state.reply_subject or f"Re: {state.subject or state.ticket_number}"
    mongo.write_audit(
        state.ticket_id,
        "action_executed",
        {"action": action, "label": label, "channel": state.channel},
    )
    state.add_step("Action", label, action)
    return state
