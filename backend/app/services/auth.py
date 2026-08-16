import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import settings
from app.services import mongo

DEMO_USERS = [
    {
        "email": "admin@example.com",
        "password": "admin123",
        "role": "admin",
        "display_name": "Alex Admin",
    },
    {
        "email": "customer@example.com",
        "password": "customer123",
        "role": "customer",
        "display_name": "Casey Customer",
    },
]


def _hash_password(password: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), settings.jwt_secret.encode(), 120000).hex()


def seed_users() -> None:
    for user in DEMO_USERS:
        if mongo.users().find_one({"email": user["email"]}):
            continue
        mongo.users().insert_one(
            {
                "email": user["email"],
                "password_hash": _hash_password(user["password"]),
                "role": user["role"],
                "display_name": user["display_name"],
            }
        )


def authenticate(email: str, password: str) -> dict | None:
    user = mongo.users().find_one({"email": email.lower()})
    if not user:
        return None
    if not hmac.compare_digest(user["password_hash"], _hash_password(password)):
        return None
    return user


def create_token(user: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user.get("email")),
        "role": user.get("role"),
        "name": user.get("display_name"),
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise ValueError("invalid token") from exc
