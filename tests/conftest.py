import uuid

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
def client():
    """TestClient with full lifespan (creates tables)."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers(client):
    """Register a fresh user per test and return auth headers."""
    email = f"test_{uuid.uuid4().hex[:8]}@test.com"
    password = "testpass123"
    client.post("/auth/register", json={"email": email, "password": password})
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, f"Login failed: {r.json()}"
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def campaign(client, auth_headers):
    """Create a campaign and return it."""
    r = client.post("/campaigns", json={"name": "Test Campaign"}, headers=auth_headers)
    return r.json()


@pytest.fixture
def product(client, auth_headers, campaign):
    """Create a product under the test campaign."""
    r = client.post(
        f"/campaigns/{campaign['id']}/products",
        json={"name": "Test Shoe", "description": "A fast running shoe"},
        headers=auth_headers,
    )
    return r.json()
