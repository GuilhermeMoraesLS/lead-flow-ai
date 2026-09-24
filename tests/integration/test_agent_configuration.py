import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt


def test_gestor_saves_and_reopens_agent_configuration(client, identity):
    _, headers = identity()
    headers["Idempotency-Key"] = str(uuid4())
    org = client.post("/v1/organizations", headers=headers, json={"name": "Alfa"}).json()
    path = f"/v1/orgs/{org['id']}/agent-config"

    initial = client.get(path, headers=headers)
    assert initial.status_code == 200
    assert initial.json()["version"] == 1

    saved = client.put(
        path,
        headers=headers,
        json={
            "version": 1,
            "name": "Lia",
            "identity": "Assistente comercial da Alfa",
            "instructions": "Apresente os produtos e peça autorização para contato.",
        },
    )
    assert saved.status_code == 200
    assert saved.json()["version"] == 2
    assert saved.json()["active"] is False
    assert client.get(path, headers=headers).json() == saved.json()


def test_stale_configuration_update_is_recoverable(client, identity):
    _, headers = identity()
    headers["Idempotency-Key"] = str(uuid4())
    org = client.post("/v1/organizations", headers=headers, json={"name": "Alfa"}).json()
    path = f"/v1/orgs/{org['id']}/agent-config"
    first = {"version": 1, "name": "Lia", "identity": "Alfa", "instructions": "Primeira versão"}
    assert client.put(path, headers=headers, json=first).status_code == 200

    stale = client.put(path, headers=headers, json={**first, "instructions": "Versão antiga"})
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "VERSION_CONFLICT"
    current = client.get(path, headers=headers).json()
    assert current["instructions"] == "Primeira versão"
    assert current["version"] == 2


def test_expired_session_cannot_change_configuration(client, identity):
    _, headers = identity()
    headers["Idempotency-Key"] = str(uuid4())
    org = client.post("/v1/organizations", headers=headers, json={"name": "Alfa"}).json()
    path = f"/v1/orgs/{org['id']}/agent-config"
    expired = jwt.encode(
        {"sub": str(uuid4()), "aud": "authenticated", "exp": datetime.now(UTC) - timedelta(minutes=1),
         "iat": datetime.now(UTC) - timedelta(minutes=2), "iss": os.environ["JWT_ISSUER"]},
        os.environ["LOCAL_JWT_SECRET"], algorithm="HS256",
    )
    response = client.put(path, headers={"Authorization": "Bearer " + expired},
                          json={"version": 1, "name": "Lia", "identity": "Alfa", "instructions": "Não salvar"})
    assert response.status_code == 401
    assert client.get(path, headers=headers).json()["instructions"] == ""


def test_incomplete_activation_lists_pending_checks_and_preserves_progress(client, identity):
    _, headers = identity()
    headers["Idempotency-Key"] = str(uuid4())
    org = client.post("/v1/organizations", headers=headers, json={"name": "Alfa"}).json()
    config_path = f"/v1/orgs/{org['id']}/agent-config"
    saved = client.put(config_path, headers=headers, json={
        "version": 1, "name": "Lia", "identity": "Assistente da Alfa",
        "instructions": "Atenda em português e esclareça dúvidas.",
    })
    assert saved.status_code == 200

    attempt = client.post(f"/v1/orgs/{org['id']}/agent/activate", headers=headers)
    assert attempt.status_code == 409
    body = attempt.json()
    assert body["error"]["code"] == "AGENT_NOT_READY"
    assert body["blockers"] == [
        {"code": "commercial_source", "label": "Fonte comercial utilizável", "status": "pending"},
        {"code": "channel", "label": "Canal operacional", "status": "pending"},
        {"code": "qualification", "label": "Critérios de qualificação", "status": "pending"},
        {"code": "contingency_owner", "label": "Responsável de contingência", "status": "pending"},
        {"code": "v02", "label": "Checklist definitivo V02", "status": "pending"},
    ]
    assert client.get(config_path, headers=headers).json()["instructions"] == "Atenda em português e esclareça dúvidas."
    assert client.get(f"/v1/orgs/{org['id']}", headers=headers).json()["agent"]["active"] is False


def test_other_organization_cannot_read_or_change_configuration(client, identity):
    _, alpha_headers = identity()
    _, beta_headers = identity()
    alpha_headers["Idempotency-Key"] = str(uuid4())
    org = client.post("/v1/organizations", headers=alpha_headers, json={"name": "Alfa"}).json()
    path = f"/v1/orgs/{org['id']}/agent-config"

    assert client.get(path, headers=beta_headers).status_code == 404
    rejected = client.put(path, headers=beta_headers, json={
        "version": 1, "name": "Beta", "identity": "Outra", "instructions": "Invadir",
    })
    assert rejected.status_code == 404
    assert client.get(path, headers=alpha_headers).json()["name"] == ""
