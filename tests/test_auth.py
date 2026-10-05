from datetime import timedelta

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from jwt import decode
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token
from app.models.user import User
from app.repositories.users import UserRepository
from app.schemas.user import UserCreate
from app.services.auth import AuthService


def test_registration_and_profile(client: TestClient, user_payload: dict[str, str]) -> None:
    response = client.post("/auth/register", json=user_payload)
    assert response.status_code == 201
    assert response.json()["email"] == user_payload["email"]
    assert "password" not in response.json()

    login = client.post("/auth/login", json={"email": user_payload["email"], "password": user_payload["password"]})
    assert login.status_code == 200
    token = login.json()["access_token"]
    profile = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json()["full_name"] == user_payload["full_name"]


def test_duplicate_registration_returns_conflict(client: TestClient, user_payload: dict[str, str]) -> None:
    assert client.post("/auth/register", json=user_payload).status_code == 201
    duplicate = client.post("/auth/register", json=user_payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["message"] == "An account with this email already exists"


def test_email_is_case_insensitive_for_registration_and_login(client: TestClient, user_payload: dict[str, str]) -> None:
    mixed_case = {**user_payload, "email": "Owner@Example.COM"}
    registered = client.post("/auth/register", json=mixed_case)
    assert registered.status_code == 201
    assert registered.json()["email"] == "owner@example.com"

    duplicate = client.post("/auth/register", json=user_payload)
    assert duplicate.status_code == 409
    login = client.post("/auth/login", json={"email": "OWNER@example.com", "password": user_payload["password"]})
    assert login.status_code == 200


def test_database_unique_constraint_handles_registration_race(
    db_session: Session, user_payload: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    service = AuthService(db_session)
    payload = UserCreate(**user_payload)
    service.register(payload)
    monkeypatch.setattr(service.users, "get_by_email", lambda _: None)

    with pytest.raises(HTTPException) as exc_info:
        service.register(UserCreate(**{**user_payload, "email": "OWNER@example.com"}))
    assert exc_info.value.status_code == 409

    assert db_session.scalar(select(User).where(User.email == "owner@example.com")) is not None


def test_valid_and_invalid_login(client: TestClient, user_payload: dict[str, str]) -> None:
    client.post("/auth/register", json=user_payload)
    valid = client.post("/auth/login", json={"email": user_payload["email"], "password": user_payload["password"]})
    assert valid.status_code == 200
    assert valid.json()["token_type"] == "bearer"
    invalid = client.post("/auth/login", json={"email": user_payload["email"], "password": "wrong-password"})
    assert invalid.status_code == 401


def test_protected_endpoint_rejects_missing_or_invalid_token(client: TestClient) -> None:
    assert client.get("/users/me").status_code == 401
    assert client.get("/users/me", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_expired_access_token_is_rejected(client: TestClient) -> None:
    token, _ = create_access_token(1, expires_delta=timedelta(seconds=-1))
    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_access_token_contains_required_public_claims() -> None:
    settings = get_settings()
    token, _ = create_access_token(123)
    claims = decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )
    assert claims["sub"] == "123"
    assert claims["type"] == "access"
    assert {"exp", "iat", "jti", "iss", "aud"} <= claims.keys()


def test_inactive_user_cannot_authenticate(
    client: TestClient, user_payload: dict[str, str], db_session: Session
) -> None:
    client.post("/auth/register", json=user_payload)
    login = client.post("/auth/login", json={"email": user_payload["email"], "password": user_payload["password"]})
    token = login.json()["access_token"]
    user = UserRepository(db_session).get_by_email(user_payload["email"])
    assert user is not None
    user.is_active = False
    db_session.commit()

    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    second_login = client.post(
        "/auth/login", json={"email": user_payload["email"], "password": user_payload["password"]}
    )
    assert response.status_code == 401
    assert second_login.status_code == 401


def test_blank_password_and_whitespace_name_are_rejected(client: TestClient) -> None:
    blank_password = client.post(
        "/auth/register", json={"email": "blank@example.com", "full_name": "Valid Name", "password": "        "}
    )
    blank_name = client.post(
        "/auth/register", json={"email": "name@example.com", "full_name": "   ", "password": "valid-password"}
    )
    assert blank_password.status_code == 422
    assert blank_name.status_code == 422


def test_invalid_registration_payload_has_structured_error(client: TestClient) -> None:
    response = client.post("/auth/register", json={"email": "not-email", "full_name": "A", "password": "short"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
