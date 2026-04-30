"""Unit tests for auth endpoints."""
import uuid


def test_register_and_login(client):
    email = f"unit_{uuid.uuid4().hex[:8]}@test.com"
    r = client.post("/auth/register", json={"email": email, "password": "pw123"})
    assert r.status_code == 201
    assert r.json()["email"] == email

    r = client.post("/auth/login", data={"username": email, "password": "pw123"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_duplicate_register(client):
    client.post("/auth/register", json={"email": "dup@test.com", "password": "pw"})
    r = client.post("/auth/register", json={"email": "dup@test.com", "password": "pw"})
    assert r.status_code == 400


def test_wrong_password(client):
    client.post("/auth/register", json={"email": "wp@test.com", "password": "correct"})
    r = client.post("/auth/login", data={"username": "wp@test.com", "password": "wrong"})
    assert r.status_code == 401


def test_protected_route_requires_token(client):
    r = client.get("/campaigns")
    assert r.status_code == 401
