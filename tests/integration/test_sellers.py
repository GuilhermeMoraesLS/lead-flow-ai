from uuid import uuid4

import httpx


def test_gestor_registers_seller_without_granting_access(client, identity):
    _, gestor_headers = identity()
    _, seller_headers = identity()
    gestor_headers["Idempotency-Key"] = str(uuid4())
    org = client.post(
        "/v1/organizations", headers=gestor_headers, json={"name": "Alfa"}
    ).json()
    path = f"/v1/orgs/{org['id']}/sellers"

    created = client.post(
        path, headers=gestor_headers,
        json={"name": "Bia", "email": "bia@example.test", "phone": "+5511999990000", "available": True},
    )
    assert created.status_code == 201
    assert created.json()["name"] == "Bia"
    assert created.json()["available"] is True
    assert created.json()["email"] == "bia@example.test"
    assert created.json()["phone"] == "+5511999990000"
    assert created.json()["access"] == "registered"
    assert client.get(path, headers=gestor_headers).json() == [created.json()]
    assert client.get(path, headers=seller_headers).status_code == 404


def test_enabled_seller_must_change_generated_password_before_access(client, identity):
    _, gestor_headers = identity()
    gestor_headers["Idempotency-Key"] = str(uuid4())
    org = client.post("/v1/organizations", headers=gestor_headers, json={"name": "Alfa"}).json()
    seller = client.post(f"/v1/orgs/{org['id']}/sellers", headers=gestor_headers, json={
        "name": "Bia", "email": f"bia-{uuid4().hex}@example.test",
        "phone": "+5511999990000", "available": True,
    }).json()

    enabled = client.post(f"/v1/orgs/{org['id']}/sellers/{seller['id']}/enable", headers=gestor_headers)
    assert enabled.status_code == 200
    temporary_password = enabled.json()["temporary_password"]
    assert len(temporary_password) >= 20
    assert client.post(f"/v1/orgs/{org['id']}/sellers/{seller['id']}/enable", headers=gestor_headers).status_code == 409
    listed = client.get(f"/v1/orgs/{org['id']}/sellers", headers=gestor_headers).json()[0]
    assert listed["access"] == "password_change_required"
    assert "temporary_password" not in listed
    assert client.get(f"/v1/orgs/{org['id']}", headers=gestor_headers).json()["role"] == "gestor"

    login = httpx.post("http://127.0.0.1:54321/token?grant_type=password", json={
        "email": seller["email"], "password": temporary_password,
    })
    assert login.status_code == 200
    seller_headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    access = client.get(f"/v1/orgs/{org['id']}/sellers/me/eligibility", headers=seller_headers)
    assert access.status_code == 403
    assert access.json()["error"]["code"] == "PASSWORD_CHANGE_REQUIRED"

    wrong = client.post(f"/v1/orgs/{org['id']}/sellers/me/password", headers=seller_headers,
                        json={"current_password": "SenhaErrada-2026!",
                              "new_password": "NovaSenhaSintetica-2026!"})
    assert wrong.status_code == 400
    assert client.get(f"/v1/orgs/{org['id']}/sellers/me/eligibility",
                      headers=seller_headers).status_code == 403
    same = client.post(f"/v1/orgs/{org['id']}/sellers/me/password", headers=seller_headers,
                       json={"current_password": temporary_password,
                             "new_password": temporary_password})
    assert same.status_code == 422

    changed = client.post(f"/v1/orgs/{org['id']}/sellers/me/password", headers=seller_headers,
                          json={"current_password": temporary_password,
                                "new_password": "NovaSenhaSintetica-2026!"})
    assert changed.status_code == 200
    assert client.get(f"/v1/orgs/{org['id']}/sellers/me/eligibility",
                      headers=seller_headers).json() == {
        "eligible": True, "active": True, "available": True,
    }
    assert httpx.post("http://127.0.0.1:54321/token?grant_type=password", json={
        "email": seller["email"], "password": temporary_password,
    }).status_code != 200
    assert httpx.post("http://127.0.0.1:54321/token?grant_type=password", json={
        "email": seller["email"], "password": "NovaSenhaSintetica-2026!",
    }).status_code == 200

    assert client.get(f"/v1/orgs/{org['id']}/agent-config", headers=seller_headers).status_code == 404
    _, other_gestor_headers = identity()
    other_gestor_headers["Idempotency-Key"] = str(uuid4())
    client.post("/v1/organizations", headers=other_gestor_headers, json={"name": "Beta"})
    availability_path = f"/v1/orgs/{org['id']}/sellers/{seller['id']}/availability"
    assert client.put(availability_path, headers=other_gestor_headers,
                      json={"active": False, "available": False}).status_code == 404
    assert client.put(availability_path, headers=gestor_headers,
                      json={"active": True, "available": False}).status_code == 200
    assert client.get(f"/v1/orgs/{org['id']}/sellers/me/eligibility",
                      headers=seller_headers).json()["eligible"] is False
    assert client.put(availability_path, headers=gestor_headers,
                      json={"active": False, "available": True}).status_code == 200
    assert client.get(f"/v1/orgs/{org['id']}/sellers/me/eligibility",
                      headers=seller_headers).json()["eligible"] is False
    assert client.put(availability_path, headers=gestor_headers,
                      json={"active": True, "available": True}).status_code == 200
    revoked = client.post(f"/v1/orgs/{org['id']}/sellers/{seller['id']}/revoke",
                          headers=gestor_headers)
    assert revoked.status_code == 200
    assert client.get(f"/v1/orgs/{org['id']}/sellers/me/eligibility",
                      headers=seller_headers).status_code == 404
    assert client.get(f"/v1/orgs/{org['id']}/sellers", headers=gestor_headers).json()[0]["access"] == "revoked"
