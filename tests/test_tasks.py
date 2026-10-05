import pytest
from fastapi.testclient import TestClient


def create_task(client: TestClient, headers: dict[str, str], **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": "Prepare release notes",
        "description": "Summarize the API changes",
        "priority": "high",
        "due_date": "2026-10-20",
    }
    payload.update(overrides)
    response = client.post("/tasks", json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_create_and_retrieve_task(client: TestClient, auth_headers: dict[str, str]) -> None:
    task = create_task(client, auth_headers)
    assert task["status"] == "todo"
    response = client.get(f"/tasks/{task['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["title"] == task["title"]


def test_update_status_and_delete_task(client: TestClient, auth_headers: dict[str, str]) -> None:
    task = create_task(client, auth_headers)
    updated = client.patch(f"/tasks/{task['id']}", json={"status": "completed"}, headers=auth_headers)
    assert updated.status_code == 200
    assert updated.json()["status"] == "completed"
    assert client.delete(f"/tasks/{task['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/tasks/{task['id']}", headers=auth_headers).status_code == 404


def test_filter_search_and_sort_tasks(client: TestClient, auth_headers: dict[str, str]) -> None:
    create_task(client, auth_headers, title="Write documentation", priority="high", status="in_progress")
    create_task(client, auth_headers, title="Review telemetry", priority="low", status="todo")
    create_task(client, auth_headers, title="Documentation follow-up", priority="high", status="todo")

    filtered = client.get(
        "/tasks?priority=high&status=todo&search=documentation&sort_by=title&sort_order=asc", headers=auth_headers
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["title"] == "Documentation follow-up"


def test_pagination(client: TestClient, auth_headers: dict[str, str]) -> None:
    for index in range(5):
        create_task(client, auth_headers, title=f"Task {index}")
    first = client.get("/tasks?page=1&page_size=2&sort_by=title&sort_order=asc", headers=auth_headers).json()
    second = client.get("/tasks?page=2&page_size=2&sort_by=title&sort_order=asc", headers=auth_headers).json()
    assert first["total"] == 5
    assert first["pages"] == 3
    assert len(first["items"]) == 2
    assert first["items"][0]["id"] != second["items"][0]["id"]


def test_sort_ties_are_deterministic(client: TestClient, auth_headers: dict[str, str]) -> None:
    created_ids = [create_task(client, auth_headers, title="Same title")["id"] for _ in range(3)]
    ascending = client.get("/tasks?sort_by=title&sort_order=asc", headers=auth_headers).json()["items"]
    descending = client.get("/tasks?sort_by=title&sort_order=desc", headers=auth_headers).json()["items"]
    assert [item["id"] for item in ascending] == created_ids
    assert [item["id"] for item in descending] == list(reversed(created_ids))


def test_search_treats_wildcards_as_literal_text(client: TestClient, auth_headers: dict[str, str]) -> None:
    create_task(client, auth_headers, title="Reach 100% coverage")
    create_task(client, auth_headers, title="Ordinary task")
    percent = client.get("/tasks?search=%25", headers=auth_headers)
    underscore = client.get("/tasks?search=_", headers=auth_headers)
    whitespace = client.get("/tasks?search=%20%20", headers=auth_headers)
    assert percent.status_code == 200
    assert [item["title"] for item in percent.json()["items"]] == ["Reach 100% coverage"]
    assert underscore.json()["total"] == 0
    assert whitespace.status_code == 422


def test_user_cannot_access_another_users_task(client: TestClient, auth_headers: dict[str, str]) -> None:
    task = create_task(client, auth_headers)
    second = {"email": "second@example.com", "full_name": "Second User", "password": "another-secure-password"}
    client.post("/auth/register", json=second)
    login = client.post("/auth/login", json={"email": second["email"], "password": second["password"]})
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get(f"/tasks/{task['id']}", headers=other_headers).status_code == 404
    assert (
        client.patch(f"/tasks/{task['id']}", json={"title": "Unauthorized"}, headers=other_headers).status_code == 404
    )
    assert client.delete(f"/tasks/{task['id']}", headers=other_headers).status_code == 404
    assert client.get("/tasks", headers=other_headers).json()["total"] == 0


def test_missing_task_and_invalid_payload(client: TestClient, auth_headers: dict[str, str]) -> None:
    assert client.get("/tasks/9999", headers=auth_headers).status_code == 404
    invalid = client.post("/tasks", json={"title": "", "status": "blocked", "priority": "urgent"}, headers=auth_headers)
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"
    assert client.patch("/tasks/9999", json={}, headers=auth_headers).status_code == 422


def test_blank_or_null_required_task_fields_are_rejected(client: TestClient, auth_headers: dict[str, str]) -> None:
    blank = client.post("/tasks", json={"title": "   "}, headers=auth_headers)
    task = create_task(client, auth_headers)
    null_title = client.patch(f"/tasks/{task['id']}", json={"title": None}, headers=auth_headers)
    null_status = client.patch(f"/tasks/{task['id']}", json={"status": None}, headers=auth_headers)
    assert blank.status_code == 422
    assert null_title.status_code == 422
    assert null_status.status_code == 422


def test_postgres_returns_timezone_aware_timestamps(
    client: TestClient, auth_headers: dict[str, str], database_backend: str
) -> None:
    if database_backend != "postgresql":
        pytest.skip("Timezone round-trip behavior is PostgreSQL-specific")
    task = create_task(client, auth_headers)
    assert task["created_at"].endswith("+00:00")
    assert task["updated_at"].endswith("+00:00")


def test_task_routes_require_authentication(client: TestClient) -> None:
    assert client.get("/tasks").status_code == 401
    assert client.post("/tasks", json={"title": "No access"}).status_code == 401
