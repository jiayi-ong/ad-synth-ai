"""System tests — light smoke tests of all API endpoints with a real server.

These tests use mock image provider and do NOT call Gemini — they verify
routing, auth enforcement, and response shapes across the full API surface.
"""
import pytest


@pytest.mark.system
class TestHealthAndAuth:
    def test_health_returns_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_all_protected_routes_reject_unauthenticated(self, client):
        protected = [
            ("GET", "/campaigns"),
            ("GET", "/brands"),
            ("POST", "/campaigns"),
            ("POST", "/brands"),
        ]
        for method, path in protected:
            r = client.request(method, path)
            assert r.status_code == 401, f"Expected 401 on {method} {path}, got {r.status_code}"


@pytest.mark.system
class TestCampaignEndpoints:
    def test_create_list_get_update_delete(self, client, auth_headers):
        r = client.post("/campaigns", json={"name": "Smoke Campaign"}, headers=auth_headers)
        assert r.status_code == 201
        campaign_id = r.json()["id"]

        r = client.get("/campaigns", headers=auth_headers)
        assert r.status_code == 200

        r = client.get(f"/campaigns/{campaign_id}", headers=auth_headers)
        assert r.status_code == 200

        r = client.patch(f"/campaigns/{campaign_id}", json={"name": "Updated"}, headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["name"] == "Updated"

        r = client.delete(f"/campaigns/{campaign_id}", headers=auth_headers)
        assert r.status_code == 204


@pytest.mark.system
class TestBrandEndpoints:
    def test_create_list_get_update_delete(self, client, auth_headers):
        r = client.post(
            "/brands",
            json={"name": "Smoke Brand", "company": "Smoke Co"},
            headers=auth_headers,
        )
        assert r.status_code == 201
        brand_id = r.json()["id"]

        r = client.get("/brands", headers=auth_headers)
        assert r.status_code == 200

        r = client.get(f"/brands/{brand_id}", headers=auth_headers)
        assert r.status_code == 200

        r = client.patch(f"/brands/{brand_id}", json={"mission": "Inspire"}, headers=auth_headers)
        assert r.status_code == 200

        r = client.delete(f"/brands/{brand_id}", headers=auth_headers)
        assert r.status_code == 204


@pytest.mark.system
class TestProductAndPersonaEndpoints:
    def test_products_crud(self, client, auth_headers, campaign):
        r = client.post(
            f"/campaigns/{campaign['id']}/products",
            json={"name": "Smoke Product", "description": "desc"},
            headers=auth_headers,
        )
        assert r.status_code == 201
        product_id = r.json()["id"]

        r = client.get(f"/campaigns/{campaign['id']}/products", headers=auth_headers)
        assert r.status_code == 200

        r = client.patch(
            f"/campaigns/{campaign['id']}/products/{product_id}",
            json={"name": "Renamed"},
            headers=auth_headers,
        )
        assert r.status_code == 200

        r = client.delete(f"/campaigns/{campaign['id']}/products/{product_id}", headers=auth_headers)
        assert r.status_code == 204

    def test_personas_crud(self, client, auth_headers, campaign):
        r = client.post(
            f"/campaigns/{campaign['id']}/personas",
            json={"name": "Smoke Persona", "traits": {"style": "curious"}},
            headers=auth_headers,
        )
        assert r.status_code == 201
        persona_id = r.json()["id"]

        r = client.get(f"/campaigns/{campaign['id']}/personas", headers=auth_headers)
        assert r.status_code == 200

        r = client.delete(f"/campaigns/{campaign['id']}/personas/{persona_id}", headers=auth_headers)
        assert r.status_code == 204


@pytest.mark.system
class TestResearchEndpoint:
    def test_research_endpoint_requires_auth(self, client):
        r = client.post(
            "/research",
            json={"product_description": "running shoe", "research_type": "trends"},
        )
        assert r.status_code == 401
