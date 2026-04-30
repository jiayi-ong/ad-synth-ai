"""Module tests for the authentication flow."""
import uuid

import pytest


@pytest.mark.module
class TestAuthFlow:
    def _unique_email(self) -> str:
        return f"test_{uuid.uuid4().hex[:8]}@module-test.com"

    def test_register_and_login_full_flow(self, client):
        email = self._unique_email()
        password = "SecurePass123!"

        r = client.post("/auth/register", json={"email": email, "password": password})
        assert r.status_code == 201
        assert r.json()["email"] == email

        r = client.post("/auth/login", data={"username": email, "password": password})
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_duplicate_email_registration_rejected(self, client):
        email = self._unique_email()
        password = "pass123"
        client.post("/auth/register", json={"email": email, "password": password})
        r = client.post("/auth/register", json={"email": email, "password": password})
        assert r.status_code in (400, 409)

    def test_wrong_password_returns_401(self, client):
        email = self._unique_email()
        client.post("/auth/register", json={"email": email, "password": "correctpass"})
        r = client.post("/auth/login", data={"username": email, "password": "wrongpass"})
        assert r.status_code == 401

    def test_unregistered_email_returns_401(self, client):
        r = client.post(
            "/auth/login",
            data={"username": "nobody@example.com", "password": "any"},
        )
        assert r.status_code == 401

    def test_invalid_token_rejected_on_protected_route(self, client):
        r = client.get(
            "/campaigns",
            headers={"Authorization": "Bearer not-a-real-token"},
        )
        assert r.status_code == 401

    def test_missing_auth_header_returns_401(self, client):
        r = client.get("/campaigns")
        assert r.status_code == 401

    def test_token_grants_access_to_protected_routes(self, client, auth_headers):
        r = client.get("/campaigns", headers=auth_headers)
        assert r.status_code == 200
