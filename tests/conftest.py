import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.task import Task
from app.models.user import User

TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]
database_url = make_url(TEST_DATABASE_URL)
IS_POSTGRES = database_url.get_backend_name() == "postgresql"
if IS_POSTGRES and not (database_url.database or "").endswith("_test"):
    raise RuntimeError("PostgreSQL tests require a database name ending in '_test'")

engine_options: dict[str, object] = {}
if database_url.get_backend_name() == "sqlite":
    engine_options = {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}
engine = create_engine(TEST_DATABASE_URL, **engine_options)
TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture(autouse=True)
def database() -> Generator[None, None, None]:
    if not IS_POSTGRES:
        Base.metadata.create_all(engine)
    with TestingSession() as session:
        session.execute(delete(Task))
        session.execute(delete(User))
        session.commit()
    try:
        yield
    finally:
        with TestingSession() as session:
            session.execute(delete(Task))
            session.execute(delete(User))
            session.commit()
        if not IS_POSTGRES:
            Base.metadata.drop_all(engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    with TestingSession() as session:
        yield session


@pytest.fixture
def database_backend() -> str:
    return database_url.get_backend_name()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    def override_db() -> Generator[Session, None, None]:
        with TestingSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def user_payload() -> dict[str, str]:
    return {"email": "owner@example.com", "full_name": "Task Owner", "password": "correct-horse-battery"}


@pytest.fixture
def auth_headers(client: TestClient, user_payload: dict[str, str]) -> dict[str, str]:
    client.post("/auth/register", json=user_payload)
    response = client.post("/auth/login", json={"email": user_payload["email"], "password": user_payload["password"]})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
