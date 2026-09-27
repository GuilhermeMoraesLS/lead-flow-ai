import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import jwt


def test_gestor_creates_and_retrieves_own_inactive_operation(client, identity):
    _, headers = identity()
    headers["Idempotency-Key"] = str(uuid4())
    created = client.post("/v1/organizations", headers=headers, json={"name": "Alfa sintética"})
    assert created.status_code == 201
    operation = created.json()
    assert operation["name"] == "Alfa sintética"
    assert operation["role"] == "gestor"
    assert operation["automation_enabled"] is False
    assert operation["agent"]["active"] is False
    assert client.get("/v1/orgs/" + operation["id"], headers=headers).json() == operation


def test_repeating_same_command_does_not_duplicate(client, identity):
    _, headers = identity()
    headers["Idempotency-Key"] = str(uuid4())
    payload = {"name": "Alfa idempotente"}
    first = client.post("/v1/organizations", headers=headers, json=payload)
    second = client.post("/v1/organizations", headers=headers, json=payload)
    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json() == first.json()


def test_reusing_key_with_different_request_is_rejected(client, identity):
    _, headers = identity()
    headers["Idempotency-Key"] = str(uuid4())
    assert (
        client.post("/v1/organizations", headers=headers, json={"name": "Alfa"}).status_code == 201
    )
    conflict = client.post("/v1/organizations", headers=headers, json={"name": "Beta"})
    assert conflict.status_code == 409


def test_organization_isolation_and_expired_session(client, identity):
    _, alpha_headers = identity()
    _, beta_headers = identity()
    alpha_headers["Idempotency-Key"] = str(uuid4())
    created = client.post(
        "/v1/organizations", headers=alpha_headers, json={"name": "Alfa isolada"}
    ).json()
    assert client.get("/v1/orgs/" + created["id"], headers=beta_headers).status_code == 404
    expired = jwt.encode(
        {
            "sub": str(uuid4()),
            "aud": "authenticated",
            "exp": datetime.now(UTC) - timedelta(minutes=1),
            "iat": datetime.now(UTC) - timedelta(minutes=2),
            "iss": os.environ["JWT_ISSUER"],
        },
        os.environ["LOCAL_JWT_SECRET"],
        algorithm="HS256",
    )
    response = client.post(
        "/v1/organizations",
        headers={"Authorization": "Bearer " + expired, "Idempotency-Key": str(uuid4())},
        json={"name": "Não deve salvar"},
    )
    assert response.status_code == 401


def test_member_discovers_own_organizations_without_identifier(client, identity):
    _, gestor_headers = identity()
    _, stranger_headers = identity()
    created = []
    for name in ("Alfa descoberta", "Beta descoberta"):
        headers = {**gestor_headers, "Idempotency-Key": str(uuid4())}
        created.append(client.post("/v1/organizations", headers=headers, json={"name": name}).json())
    listed = client.get("/v1/me/organizations", headers=gestor_headers)
    assert listed.status_code == 200
    assert sorted(listed.json(), key=lambda item: item["name"]) == [
        {"id": org["id"], "name": org["name"], "role": "gestor"} for org in created]
    assert client.get("/v1/me/organizations", headers=stranger_headers).json() == []
    assert client.get("/v1/me/organizations").status_code == 401

    org = created[0]
    seller = client.post(f"/v1/orgs/{org['id']}/sellers", headers=gestor_headers, json={
        "name": "Bia", "email": f"bia-{uuid4().hex}@example.test",
        "phone": "+5511999990000", "available": True}).json()
    password = client.post(f"/v1/orgs/{org['id']}/sellers/{seller['id']}/enable",
                           headers=gestor_headers).json()["temporary_password"]
    login = httpx.post("http://127.0.0.1:54321/token?grant_type=password",
                       json={"email": seller["email"], "password": password})
    seller_headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert client.get("/v1/me/organizations", headers=seller_headers).json() == [
        {"id": org["id"], "name": org["name"], "role": "vendedor"}]
    client.post(f"/v1/orgs/{org['id']}/sellers/{seller['id']}/revoke", headers=gestor_headers)
    assert client.get("/v1/me/organizations", headers=seller_headers).json() == []


def test_rejected_creation_does_not_consume_idempotency_key(client, identity):
    _, headers = identity()
    headers["Idempotency-Key"] = str(uuid4())
    rejected = client.post("/v1/organizations", headers=headers, json={"name": ""})
    assert rejected.status_code == 422
    created = client.post("/v1/organizations", headers=headers, json={"name": "Retomada"})
    assert created.status_code == 201
