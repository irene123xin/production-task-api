from fastapi.testclient import TestClient


def test_health_and_readiness(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "healthy"}
    readiness = client.get("/health/ready")
    assert readiness.status_code == 200
    assert readiness.json()["database"] == "available"
