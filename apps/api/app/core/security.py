from hashlib import sha256
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import get_settings

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return password_hasher.verify(encoded, password)
    except (InvalidHashError, VerifyMismatchError):
        return False


def create_access_token(user_id: UUID) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=20),
        "type": "access",
    }
    return jwt.encode(payload, get_settings().jwt_secret.get_secret_value(), algorithm="HS256")


def decode_access_token(token: str) -> UUID | None:
    try:
        payload = jwt.decode(
            token,
            get_settings().jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            options={"require": ["sub", "exp", "type"]},
        )
        if payload.get("type") != "access":
            return None
        return UUID(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, KeyError):
        return None


def access_token_ttl(token: str) -> int:
    payload = jwt.decode(
        token,
        get_settings().jwt_secret.get_secret_value(),
        algorithms=["HS256"],
        options={"require": ["exp", "type"]},
    )
    if payload.get("type") != "access":
        return 0
    return max(1, int(payload["exp"] - datetime.now(UTC).timestamp()))


def token_fingerprint(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()