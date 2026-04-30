"""Module tests for campaign, product, and persona CRUD with auth isolation."""
import uuid

import pytest


def _register_and_login(client) -> dict:
    email = f"user_{uuid.uuid4().hex[:8]}@test.com"
    password = "pass123"
    client.post("/auth/register", json={"email": email, "password": password})
    r = client.post("/auth/login", data={"username": email, "password": password})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.module
class TestCampaignCRUD:
    def test_create_campaign(self, client, auth_headers):
        r = client.post("/campaigns", json={"name": "My Campaign"}, headers=auth_headers)
        assert r.status_code == 201
        assert r.json()["name"] == "My Campaign"
        assert "id" in r.json()

    def test_list_campaigns(self, client, auth_headers):
        client.post("/campaigns", json={"name": "Camp A"}, headers=auth_headers)
        client.post("/campaigns", json={"name": "Camp B"}, headers=auth_headers)
        r = client.get("/campaigns", headers=auth_headers)
        assert r.status_code == 200
        names = [c["name"] for c in r.json()]
        assert "Camp A" in names
        assert "Camp B" in names

    def test_get_campaign_by_id(self, client, auth_headers):
        r = client.post("/campaigns", json={"name": "Specific"}, headers=auth_headers)
        campaign_id = r.json()["id"]
        r2 = client.get(f"/campaigns/{campaign_id}", headers=auth_headers)
        assert r2.status_code == 200
        assert r2.json()["id"] == campaign_id

    def test_update_campaign(self, client, auth_headers):
        r = client.post("/campaigns", json={"name": "Original"}, headers=auth_headers)
        campaign_id = r.json()["id"]
        r2 = client.patch(
            f"/campaigns/{campaign_id}",
            json={"name": "Updated", "campaign_notes": "some notes"},
            headers=auth_headers,
        )
        assert r2.status_code == 200
        assert r2.json()["name"] == "Updated"
        assert r2.json()["campaign_notes"] == "some notes"

    def test_delete_campaign(self, client, auth_headers):
        r = client.post("/campaigns", json={"name": "ToDelete"}, headers=auth_headers)
        campaign_id = r.json()["id"]
        r2 = client.delete(f"/campaigns/{campaign_id}", headers=auth_headers)
        assert r2.status_code == 204
        r3 = client.get(f"/campaigns/{campaign_id}", headers=auth_headers)
        assert r3.status_code == 404

    def test_cross_user_campaign_isolation(self, client, auth_headers):
        r = client.post("/campaigns", json={"name": "Private"}, headers=auth_headers)
        campaign_id = r.json()["id"]

        other_headers = _register_and_login(client)
        r2 = client.get(f"/campaigns/{campaign_id}", headers=other_headers)
        assert r2.status_code in (403, 404)


@pytest.mark.module
class TestProductCRUD:
    def test_create_product_under_campaign(self, client, auth_headers, campaign):
        r = client.post(
            f"/campaigns/{campaign['id']}/products",
            json={"name": "Widget", "description": "A fine widget"},
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert r.json()["name"] == "Widget"

    def test_list_products(self, client, auth_headers, campaign):
        for i in range(3):
            client.post(
                f"/campaigns/{campaign['id']}/products",
                json={"name": f"Product {i}"},
                headers=auth_headers,
            )
        r = client.get(f"/campaigns/{campaign['id']}/products", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()) >= 3

    def test_update_product(self, client, auth_headers, campaign):
        r = client.post(
            f"/campaigns/{campaign['id']}/products",
            json={"name": "Old Name"},
            headers=auth_headers,
        )
        product_id = r.json()["id"]
        r2 = client.patch(
            f"/campaigns/{campaign['id']}/products/{product_id}",
            json={"name": "New Name", "description": "Updated desc"},
            headers=auth_headers,
        )
        assert r2.status_code == 200
        assert r2.json()["name"] == "New Name"


@pytest.mark.module
class TestPersonaCRUD:
    def test_create_persona(self, client, auth_headers, campaign):
        r = client.post(
            f"/campaigns/{campaign['id']}/personas",
            json={"name": "Alex the Athlete", "traits": {"style": "competitive", "focus": "data-driven"}},
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert r.json()["name"] == "Alex the Athlete"

    def test_list_personas(self, client, auth_headers, campaign):
        client.post(
            f"/campaigns/{campaign['id']}/personas",
            json={"name": "Persona A"},
            headers=auth_headers,
        )
        r = client.get(f"/campaigns/{campaign['id']}/personas", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1
