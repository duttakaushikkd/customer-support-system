import hashlib
import hmac
import os
import re
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.services import mongo

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,32}$")

DEMO_USERS = [
    {
        "username": "admin",
        "email": "admin@example.com",
        "password": "admin123",
        "role": "admin",
        "display_name": "Alex Admin",
    },
    {
        "username": "customer",
        "email": "customer@example.com",
        "password": "customer123",
        "role": "customer",
        "display_name": "Casey Customer",
    },
]


def normalize_username(username: str) -> str:
    return username.strip().lower()


def _hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000).hex()
    return f"{salt}${digest}"


def _verify_password(password: str, stored: str) -> bool:
    if "$" in stored:
        salt, _digest = stored.split("$", 1)
        return hmac.compare_digest(stored, _hash_password(password, salt))
    legacy = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), settings.jwt_secret.encode(), 120000
    ).hex()
    return hmac.compare_digest(stored, legacy)


def seed_users() -> None:
    for user in DEMO_USERS:
        existing = mongo.users().find_one(
            {"$or": [{"email": user["email"]}, {"username": user["username"]}]}
        )
        if existing:
            mongo.users().update_one(
                {"_id": existing["_id"]},
                {"$set": {"username": user["username"], "role": user["role"]}},
            )
            continue
        mongo.users().insert_one(
            {
                "username": user["username"],
                "email": user["email"],
                "password_hash": _hash_password(user["password"]),
                "role": user["role"],
                "display_name": user["display_name"],
            }
        )


def normalize_email(email: str) -> str:
    return email.strip().lower()


def register_user(username: str, password: str, email: str, display_name: str | None = None) -> dict:
    username = normalize_username(username)
    email = normalize_email(email)
    if not USERNAME_RE.match(username):
        raise ValueError("Username must be 3–32 letters, numbers, dots, underscores, or hyphens")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters")
    if not email or "@" not in email:
        raise ValueError("A valid email address is required")
    if mongo.users().find_one({"username": username}):
        raise ValueError("Username already taken")
    if mongo.users().find_one({"email": email}):
        raise ValueError("Email already registered")
    doc = {
        "username": username,
        "email": email,
        "password_hash": _hash_password(password),
        "role": "customer",
        "display_name": (display_name or username).strip() or username,
    }
    try:
        mongo.users().insert_one(doc)
    except DuplicateKeyError as exc:
        raise ValueError("Username or email already taken") from exc
    return doc


def authenticate(identifier: str, password: str) -> dict | None:
    ident = identifier.strip().lower()
    user = mongo.users().find_one({"username": ident})
    if not user:
        return None
    if not _verify_password(password, user["password_hash"]):
        return None
    return user


def create_token(user: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    username = user.get("username") or user.get("email")
    payload = {
        "sub": str(username),
        "username": username,
        "email": user.get("email"),
        "role": user.get("role"),
        "name": user.get("display_name") or username,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def auth_response(user: dict) -> dict:
    token = create_token(user)
    username = user.get("username") or user.get("email")
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
        "username": username,
        "email": user.get("email"),
        "name": user.get("display_name") or username,
    }


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise ValueError("invalid token") from exc
