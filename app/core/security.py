from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import get_settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(user_id: int, expires_delta: timedelta | None = None) -> tuple[str, int]:
    settings = get_settings()
    lifetime = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    issued_at = datetime.now(UTC)
    expires_at = issued_at + lifetime
    token = jwt.encode(
        {
            "sub": str(user_id),
            "type": "access",
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "jti": str(uuid4()),
            "exp": expires_at,
            "iat": issued_at,
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return token, int(lifetime.total_seconds())


def decode_access_token(token: str) -> int:
    settings = get_settings()
    payload = jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        options={"require": ["sub", "type", "iss", "aud", "jti", "exp", "iat"]},
    )
    if payload.get("type") != "access":
        raise InvalidTokenError("Invalid token type")
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.isdigit():
        raise InvalidTokenError("Invalid token subject")
    return int(subject)
