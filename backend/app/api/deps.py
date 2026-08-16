from typing import Annotated

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.services.auth import verify_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> dict:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        return verify_token(creds.credentials)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_admin(user: Annotated[dict, Depends(get_current_user)]) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


def verify_email_webhook_secret(
    x_webhook_secret: Annotated[str | None, Header(alias="X-Webhook-Secret")] = None,
) -> None:
    if not x_webhook_secret or x_webhook_secret != settings.email_intake_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
