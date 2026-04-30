"""Unit tests for campaign CRUD."""


def test_create_and_list_campaign(client, auth_headers):
    r = client.post("/campaigns", json={"name": "My Campaign", "mission": "Sell stuff"}, headers=auth_headers)
    assert r.status_code == 201
    cid = r.json()["id"]

    r = client.get("/campaigns", headers=auth_headers)
    ids = [c["id"] for c in r.json()]
    assert cid in ids


def test_update_campaign(client, auth_headers, campaign):
    r = client.patch(f"/campaigns/{campaign['id']}", json={"name": "Updated"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["name"] == "Updated"


def test_delete_campaign(client, auth_headers):
    r = client.post("/campaigns", json={"name": "To Delete"}, headers=auth_headers)
    cid = r.json()["id"]
    r = client.delete(f"/campaigns/{cid}", headers=auth_headers)
    assert r.status_code == 204


def test_other_user_cannot_access_campaign(client, auth_headers):
    r = client.post("/campaigns", json={"name": "Private"}, headers=auth_headers)
    cid = r.json()["id"]

    # Second user
    client.post("/auth/register", json={"email": "other@test.com", "password": "pass"})
    r2 = client.post("/auth/login", data={"username": "other@test.com", "password": "pass"})
    other_headers = {"Authorization": f"Bearer {r2.json()['access_token']}"}

    r = client.get(f"/campaigns/{cid}", headers=other_headers)
    assert r.status_code == 403
