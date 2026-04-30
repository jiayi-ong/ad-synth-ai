"""Module tests for brand profile CRUD and campaign linkage."""
import pytest


@pytest.mark.module
class TestBrandProfileCRUD:
    def test_create_brand(self, client, auth_headers):
        r = client.post(
            "/brands",
            json={
                "name": "Test Brand",
                "company": "ACME Corp",
                "mission": "Make the world better",
                "values": "Quality, Innovation",
                "tone_keywords": "energetic, bold",
            },
            headers=auth_headers,
        )
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Test Brand"
        assert data["company"] == "ACME Corp"
        assert "id" in data

    def test_list_brands(self, client, auth_headers):
        client.post("/brands", json={"name": "Brand X"}, headers=auth_headers)
        client.post("/brands", json={"name": "Brand Y"}, headers=auth_headers)
        r = client.get("/brands", headers=auth_headers)
        assert r.status_code == 200
        names = [b["name"] for b in r.json()]
        assert "Brand X" in names
        assert "Brand Y" in names

    def test_get_brand_by_id(self, client, auth_headers):
        r = client.post("/brands", json={"name": "Specific Brand"}, headers=auth_headers)
        brand_id = r.json()["id"]
        r2 = client.get(f"/brands/{brand_id}", headers=auth_headers)
        assert r2.status_code == 200
        assert r2.json()["id"] == brand_id

    def test_update_brand(self, client, auth_headers):
        r = client.post("/brands", json={"name": "Old Brand"}, headers=auth_headers)
        brand_id = r.json()["id"]
        r2 = client.patch(
            f"/brands/{brand_id}",
            json={"name": "New Brand", "mission": "Updated mission"},
            headers=auth_headers,
        )
        assert r2.status_code == 200
        assert r2.json()["name"] == "New Brand"
        assert r2.json()["mission"] == "Updated mission"

    def test_delete_brand(self, client, auth_headers):
        r = client.post("/brands", json={"name": "ToDelete"}, headers=auth_headers)
        brand_id = r.json()["id"]
        r2 = client.delete(f"/brands/{brand_id}", headers=auth_headers)
        assert r2.status_code == 204
        r3 = client.get(f"/brands/{brand_id}", headers=auth_headers)
        assert r3.status_code == 404

    def test_brand_not_accessible_by_other_user(self, client, auth_headers):
        import uuid
        r = client.post("/brands", json={"name": "Private Brand"}, headers=auth_headers)
        brand_id = r.json()["id"]

        email = f"other_{uuid.uuid4().hex[:6]}@test.com"
        client.post("/auth/register", json={"email": email, "password": "pass"})
        login_r = client.post("/auth/login", data={"username": email, "password": "pass"})
        other_headers = {"Authorization": f"Bearer {login_r.json()['access_token']}"}

        r2 = client.get(f"/brands/{brand_id}", headers=other_headers)
        assert r2.status_code in (403, 404)


@pytest.mark.module
class TestBrandProducts:
    def test_create_brand_product(self, client, auth_headers):
        r = client.post("/brands", json={"name": "Tech Brand"}, headers=auth_headers)
        brand_id = r.json()["id"]
        r2 = client.post(
            f"/brands/{brand_id}/products",
            json={"name": "Flagship Product", "description": "The best product"},
            headers=auth_headers,
        )
        assert r2.status_code == 201
        assert r2.json()["name"] == "Flagship Product"
        assert r2.json()["brand_profile_id"] == brand_id

    def test_list_brand_products(self, client, auth_headers):
        r = client.post("/brands", json={"name": "Multi-Product Brand"}, headers=auth_headers)
        brand_id = r.json()["id"]
        for i in range(3):
            client.post(f"/brands/{brand_id}/products", json={"name": f"Product {i}"}, headers=auth_headers)
        r2 = client.get(f"/brands/{brand_id}/products", headers=auth_headers)
        assert r2.status_code == 200
        assert len(r2.json()) >= 3


@pytest.mark.module
class TestCampaignBrandLinkage:
    def test_campaign_linked_to_brand(self, client, auth_headers):
        r = client.post(
            "/brands",
            json={"name": "Linked Brand", "mission": "To inspire", "tone_keywords": "bold"},
            headers=auth_headers,
        )
        brand_id = r.json()["id"]

        r2 = client.post(
            "/campaigns",
            json={"name": "Brand Campaign", "brand_profile_id": brand_id},
            headers=auth_headers,
        )
        assert r2.status_code == 201
        assert r2.json()["brand_profile_id"] == brand_id
