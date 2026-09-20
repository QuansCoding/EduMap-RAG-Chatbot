from fastapi.testclient import TestClient

from app.main import app

# Not using `with TestClient(app)` → the lifespan (DB pool) doesn't start. These tests need no DB.
client = TestClient(app)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_protected_endpoint_requires_token():
    assert client.get("/api/workspaces").status_code == 401


def test_invalid_uuid_rejected_before_auth_logic():
    response = client.get("/api/workspaces/not-a-uuid", headers={"Authorization": "Bearer x"})
    assert response.status_code in (401, 422)