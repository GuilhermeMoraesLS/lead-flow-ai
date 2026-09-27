"""Managed bot binding and durable five-second inbound buffer."""

from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import httpx
import psycopg
import pytest
from cryptography.fernet import Fernet

from scripts.local import admin_connection


def test_telegram_secret_versions_support_rotation(monkeypatch):
    from leadflow.telegram import decrypt_secret, encrypt_secret

    old_key = Fernet.generate_key().decode()
    new_key = Fernet.generate_key().decode()
    monkeypatch.setenv("TELEGRAM_FERNET_KEY", old_key)
    monkeypatch.delenv("TELEGRAM_FERNET_KEYS", raising=False)
    legacy = Fernet(old_key.encode()).encrypt(b"legacy").decode()
    old = encrypt_secret("current")
    assert old.startswith("v1:")

    monkeypatch.setenv("TELEGRAM_FERNET_KEYS", f"1:{old_key},2:{new_key}")
    monkeypatch.setenv("TELEGRAM_FERNET_ACTIVE_VERSION", "2")
    assert decrypt_secret(legacy) == "legacy"
    assert decrypt_secret(old) == "current"
    rotated = encrypt_secret(decrypt_secret(old))
    assert rotated.startswith("v2:")
    monkeypatch.setenv("TELEGRAM_FERNET_KEYS", f"2:{new_key}")
    assert decrypt_secret(rotated) == "current"


def test_local_telegram_rotation_reencrypts_all_secret_columns(monkeypatch, tmp_path):
    import sys

    from scripts import local

    old_key = Fernet.generate_key().decode()
    config = tmp_path / "local.env"
    config.write_text("LOCAL_APP_PASSWORD=synthetic\n"
                      f"LOCAL_TELEGRAM_FERNET_KEY={old_key}\n", encoding="utf-8")
    monkeypatch.setattr(local, "ENV_FILE", config)
    monkeypatch.setattr(local, "OPENAI_ENV_FILE", tmp_path / "missing-openai.env")
    monkeypatch.setattr(local, "TELEGRAM_ENV_FILE", tmp_path / "missing-telegram.env")
    old = Fernet(old_key.encode())
    row = (uuid4(), *("v1:" + old.encrypt(secret.encode()).decode()
                      for secret in ("request", "token", "webhook")))
    updated = []

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, query, parameters=None):
            if query.startswith("SELECT"):
                return self
            updated.append(parameters)
            return self

        def fetchall(self):
            return [row]

    monkeypatch.setattr(local, "admin_connection", FakeConnection)
    monkeypatch.setattr(sys, "argv", ["local.py", "telegram-rotate-key"])
    local.main()

    from leadflow.telegram import decrypt_secret

    assert len(updated) == 1
    assert updated[0][3] == row[0]
    assert all(ciphertext.startswith("v2:") for ciphertext in updated[0][:3])
    assert tuple(decrypt_secret(ciphertext) for ciphertext in updated[0][:3]) == (
        "request", "token", "webhook")


def organization(client, identity):
    _, headers = identity()
    headers["Idempotency-Key"] = str(uuid4())
    response = client.post("/v1/organizations", headers=headers,
                           json={"name": "Telegram synthetic"})
    assert response.status_code == 201
    return response.json()["id"], headers


def test_managed_bot_onboarding_and_buffer(client, identity, monkeypatch):
    monkeypatch.setenv("TELEGRAM_MANAGER_USERNAME", "LeadFlowAI_gestor_bot")
    monkeypatch.setenv("TELEGRAM_MANAGER_TOKEN", "synthetic-manager-token")
    monkeypatch.setenv("TELEGRAM_MANAGER_WEBHOOK_SECRET", "synthetic-manager-secret")
    monkeypatch.setenv("TELEGRAM_PUBLIC_URL", "https://example.test")
    org, headers = organization(client, identity)
    owner_id = uuid4().int % 900000000000 + 100000000000
    bot_id = uuid4().int % 900000000000 + 100000000000
    base = f"/v1/orgs/{org}/telegram"
    assert client.get(base, headers=headers).json()["status"] == "not_started"
    first = client.post(base, headers=headers)
    again = client.post(base, headers=headers)
    assert first.status_code == again.status_code == 202
    assert first.json()["link"] == again.json()["link"]
    assert first.json()["connected"] is False
    assert client.get(base, headers=headers).json()["link"] == first.json()["link"]
    nonce = parse_qs(urlparse(first.json()["link"]).query)["start"][0]

    calls = []

    def fake_bot_api(token, method, payload):
        calls.append((method, payload))
        if method == "getManagedBotToken":
            return "synthetic-child-token"
        if method == "getMe":
            return {"id": bot_id, "is_bot": True, "username": "SyntheticCompanyBot"}
        if method == "getWebhookInfo":
            return {"url": f"https://example.test/v1/telegram/bots/{bot_id}/updates"}
        return True

    monkeypatch.setattr("leadflow.telegram.bot_api", fake_bot_api)
    manager_headers = {"X-Telegram-Bot-Api-Secret-Token": "synthetic-manager-secret"}
    manager_path = "/v1/telegram/manager/updates"
    start = {"update_id": 1, "message": {"text": "/start " + nonce,
            "from": {"id": owner_id}, "chat": {"id": owner_id, "type": "private"}}}
    assert client.post(manager_path, json=start).status_code == 401
    assert client.post(manager_path, json=start, headers=manager_headers).status_code == 200
    assert calls[0][0] == "sendMessage"
    pending = client.get(base, headers=headers).json()
    assert pending["status"] == "awaiting_bot" and pending["connected"] is False
    assert pending["link"].startswith("https://t.me/newbot/LeadFlowAI_gestor_bot/")

    created = {"update_id": 2, "managed_bot": {"user": {"id": owner_id},
                                                   "bot": {"id": bot_id}}}
    assert client.post(manager_path, json=created, headers=manager_headers).status_code == 200
    state = client.get(base, headers=headers).json()
    assert state == {"status": "connected", "botUsername": "SyntheticCompanyBot",
                     "failureCode": None, "connected": True}
    assert "token" not in str(state).lower()
    webhook_calls = sum(method == "setWebhook" for method, _ in calls)
    assert client.post(manager_path, json=created, headers=manager_headers).status_code == 200
    assert sum(method == "setWebhook" for method, _ in calls) == webhook_calls
    assert client.post(base + "/resume", headers=headers).json() == state
    beta, _ = organization(client, identity)
    with pytest.raises(psycopg.errors.ForeignKeyViolation), admin_connection() as conn:
        conn.execute("""INSERT INTO app.telegram_message_buffer
            (organization_id, bot_id, chat_id, telegram_message_id, body)
            VALUES (%s, %s, 88, 999, 'cross-tenant')""", (beta, bot_id))
    with admin_connection() as conn:
        stored = conn.execute("""SELECT token_ciphertext, webhook_secret_ciphertext
            FROM app.telegram_provisioning WHERE organization_id = %s""", (org,)).fetchone()
        assert stored is not None
        assert "synthetic-child-token" not in stored[0]
        assert "synthetic-child-token" not in stored[1]
    webhook_secret = next(payload["secret_token"] for method, payload in calls
                          if method == "setWebhook")
    path = f"/v1/telegram/bots/{bot_id}/updates"
    update_headers = {"X-Telegram-Bot-Api-Secret-Token": webhook_secret}
    event = {"update_id": 3, "message": {"message_id": 1, "text": "Olá",
             "from": {"id": 88, "is_bot": False},
             "chat": {"id": 88, "type": "private"}}}
    assert client.post(path, json=event).status_code == 401
    assert client.post(path, json=event, headers=update_headers).status_code == 200
    assert client.post(path, json=event, headers=update_headers).status_code == 200
    event["update_id"] = 4
    event["message"]["message_id"] = 2
    event["message"]["text"] = "Quero saber o preço"
    assert client.post(path, json=event, headers=update_headers).status_code == 200
    from leadflow.recovery import seal_telegram_due

    seal_telegram_due()
    with admin_connection() as conn:
        count = conn.execute("SELECT count(*) FROM app.telegram_message_buffer WHERE bot_id = %s",
                             (bot_id,)).fetchone()
        assert count == (2,)
        assert conn.execute("""SELECT count(*) FROM app.telegram_message_batches
            WHERE organization_id = %s""", (org,)).fetchone() == (0,)
        conn.execute("""UPDATE app.telegram_message_buffer
            SET received_at = now() - interval '6 seconds' WHERE bot_id = %s""",
                     (bot_id,))
    assert seal_telegram_due() >= 1
    assert seal_telegram_due() == 0
    with admin_connection() as conn:
        batch = conn.execute("""SELECT body FROM app.telegram_message_batches
            WHERE organization_id = %s""", (org,)).fetchone()
        assert batch == ("Olá\nQuero saber o preço",)


def test_manager_event_cannot_attach_unverified_owner(client, identity, monkeypatch):
    monkeypatch.setenv("TELEGRAM_MANAGER_USERNAME", "LeadFlowAI_gestor_bot")
    monkeypatch.setenv("TELEGRAM_MANAGER_WEBHOOK_SECRET", "synthetic-manager-secret")
    org, headers = organization(client, identity)
    assert client.post(f"/v1/orgs/{org}/telegram", headers=headers).status_code == 202
    event = {"update_id": 1, "managed_bot": {"user": {"id": 999},
                                                "bot": {"id": 888}}}
    response = client.post("/v1/telegram/manager/updates", json=event,
                           headers={"X-Telegram-Bot-Api-Secret-Token": "synthetic-manager-secret"})
    assert response.status_code == 200
    assert client.get(f"/v1/orgs/{org}/telegram", headers=headers).json()["connected"] is False


def test_managed_bot_cannot_be_connected_to_two_organizations(client, identity, monkeypatch):
    monkeypatch.setenv("TELEGRAM_MANAGER_USERNAME", "LeadFlowAI_gestor_bot")
    monkeypatch.setenv("TELEGRAM_MANAGER_TOKEN", "synthetic-manager-token")
    monkeypatch.setenv("TELEGRAM_MANAGER_WEBHOOK_SECRET", "synthetic-manager-secret")
    monkeypatch.setenv("TELEGRAM_PUBLIC_URL", "https://example.test")
    bot_id = uuid4().int % 900000000000 + 100000000000

    def fake_bot_api(token, method, payload):
        if method == "getManagedBotToken":
            return "synthetic-child-token"
        if method == "getMe":
            return {"id": bot_id, "is_bot": True, "username": "SyntheticCompanyBot"}
        if method == "getWebhookInfo":
            return {"url": f"https://example.test/v1/telegram/bots/{bot_id}/updates"}
        return True

    monkeypatch.setattr("leadflow.telegram.bot_api", fake_bot_api)
    manager = "/v1/telegram/manager/updates"
    manager_headers = {"X-Telegram-Bot-Api-Secret-Token": "synthetic-manager-secret"}
    for index in (1, 2):
        org, headers = organization(client, identity)
        base = f"/v1/orgs/{org}/telegram"
        nonce = parse_qs(urlparse(client.post(base, headers=headers).json()["link"]).query)["start"][0]
        owner = uuid4().int % 900000000000 + 100000000000
        assert client.post(manager, headers=manager_headers, json={
            "update_id": index * 2 - 1, "message": {"text": "/start " + nonce,
            "from": {"id": owner}, "chat": {"id": owner, "type": "private"}}}).status_code == 200
        assert client.post(manager, headers=manager_headers, json={
            "update_id": index * 2, "managed_bot": {"user": {"id": owner},
            "bot": {"id": bot_id}}}).status_code == 200
        state = client.get(base, headers=headers).json()
        assert state["status"] == ("connected" if index == 1 else "failed")
        if index == 2:
            assert state["failureCode"] == "bot_already_connected"


def test_same_telegram_manager_can_connect_distinct_bots_to_distinct_organizations(
        client, identity, monkeypatch):
    monkeypatch.setenv("TELEGRAM_MANAGER_USERNAME", "LeadFlowAI_gestor_bot")
    monkeypatch.setenv("TELEGRAM_MANAGER_TOKEN", "synthetic-manager-token")
    monkeypatch.setenv("TELEGRAM_MANAGER_WEBHOOK_SECRET", "synthetic-manager-secret")
    monkeypatch.setenv("TELEGRAM_PUBLIC_URL", "https://example.test")
    owner = uuid4().int % 900000000000 + 100000000000
    bots = [uuid4().int % 900000000000 + 100000000000 for _ in range(2)]
    calls = []

    def fake_bot_api(token, method, payload):
        calls.append((method, payload))
        if method == "getManagedBotToken":
            return str(payload["user_id"])
        if method == "getMe":
            return {"id": int(token), "is_bot": True,
                    "username": f"SyntheticBot{token}"}
        if method == "getWebhookInfo":
            return {"url": f"https://example.test/v1/telegram/bots/{token}/updates"}
        return True

    monkeypatch.setattr("leadflow.telegram.bot_api", fake_bot_api)
    manager = "/v1/telegram/manager/updates"
    manager_headers = {"X-Telegram-Bot-Api-Secret-Token": "synthetic-manager-secret"}
    organizations = []
    for index, bot in enumerate(bots, 1):
        org, headers = organization(client, identity)
        organizations.append((org, headers))
        base = f"/v1/orgs/{org}/telegram"
        nonce = parse_qs(urlparse(client.post(base, headers=headers).json()["link"]).query)["start"][0]
        start = {"update_id": index * 10, "message": {"text": "/start " + nonce,
                 "from": {"id": owner}, "chat": {"id": owner, "type": "private"}}}
        assert client.post(manager, headers=manager_headers, json=start).status_code == 200
        assert client.get(base, headers=headers).json()["status"] == "awaiting_bot"
        if index == 2:
            replay = {"update_id": 15, "managed_bot": {"user": {"id": owner},
                        "bot": {"id": bots[0]}}}
            assert client.post(manager, headers=manager_headers, json=replay).status_code == 200
            assert client.get(base, headers=headers).json()["status"] == "awaiting_bot"
        created = {"update_id": index * 10 + 1,
                   "managed_bot": {"user": {"id": owner}, "bot": {"id": bot}}}
        assert client.post(manager, headers=manager_headers, json=created).status_code == 200
        assert client.get(base, headers=headers).json()["status"] == "connected"
    with admin_connection() as conn:
        rows = conn.execute("""SELECT organization_id, bot_id FROM app.telegram_provisioning
            WHERE organization_id IN (%s, %s) ORDER BY bot_id""",
            (organizations[0][0], organizations[1][0])).fetchall()
    assert {(str(org), bot) for org, bot in rows} == set(
        zip((org for org, _ in organizations), bots))
    assert sum(method == "setWebhook" for method, _ in calls) == 2


def test_same_telegram_manager_has_only_one_pending_bot(client, identity, monkeypatch):
    monkeypatch.setenv("TELEGRAM_MANAGER_USERNAME", "LeadFlowAI_gestor_bot")
    monkeypatch.setenv("TELEGRAM_MANAGER_TOKEN", "synthetic-manager-token")
    monkeypatch.setenv("TELEGRAM_MANAGER_WEBHOOK_SECRET", "synthetic-manager-secret")
    calls = []
    monkeypatch.setattr("leadflow.telegram.bot_api",
                        lambda token, method, payload: calls.append((method, payload)))
    owner = uuid4().int % 900000000000 + 100000000000
    manager_headers = {"X-Telegram-Bot-Api-Secret-Token": "synthetic-manager-secret"}
    states = []
    for index in (1, 2):
        org, headers = organization(client, identity)
        base = f"/v1/orgs/{org}/telegram"
        nonce = parse_qs(urlparse(client.post(base, headers=headers).json()["link"]).query)["start"][0]
        response = client.post("/v1/telegram/manager/updates", headers=manager_headers,
                               json={"update_id": index, "message": {"text": "/start " + nonce,
                               "from": {"id": owner}, "chat": {"id": owner, "type": "private"}}})
        assert response.status_code == 200
        states.append(client.get(base, headers=headers).json()["status"])
    assert states == ["awaiting_bot", "awaiting_owner"]
    assert len(calls) == 2


def test_telegram_status_is_tenant_scoped(client, identity, monkeypatch):
    monkeypatch.setenv("TELEGRAM_MANAGER_USERNAME", "LeadFlowAI_gestor_bot")
    alpha, alpha_headers = organization(client, identity)
    beta, beta_headers = organization(client, identity)
    assert client.post(f"/v1/orgs/{beta}/telegram", headers=beta_headers).status_code == 202
    assert client.get(f"/v1/orgs/{beta}/telegram", headers=alpha_headers).status_code == 404
    assert client.post(f"/v1/orgs/{beta}/telegram", headers=alpha_headers).status_code == 404
    assert client.get(f"/v1/orgs/{alpha}/telegram", headers=alpha_headers).json()["status"] == "not_started"


def test_seller_cannot_start_telegram(client, identity, monkeypatch):
    monkeypatch.setenv("TELEGRAM_MANAGER_USERNAME", "LeadFlowAI_gestor_bot")
    org, headers = organization(client, identity)
    email = f"telegram-seller-{uuid4().hex}@example.test"
    seller = client.post(f"/v1/orgs/{org}/sellers", headers=headers, json={
        "name": "Vendedor", "email": email, "phone": "+5511999990000",
        "available": True}).json()
    enabled = client.post(f"/v1/orgs/{org}/sellers/{seller['id']}/enable", headers=headers)
    assert enabled.status_code == 200
    login = httpx.post("http://127.0.0.1:54321/token?grant_type=password", json={
        "email": email, "password": enabled.json()["temporary_password"]})
    assert login.status_code == 200
    seller_headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert client.post(f"/v1/orgs/{org}/telegram", headers=seller_headers).status_code == 403
    assert client.get(f"/v1/orgs/{org}/telegram", headers=seller_headers).status_code == 403


def test_unavailable_webhook_stays_disconnected_and_can_resume(client, identity, monkeypatch):
    monkeypatch.setenv("TELEGRAM_MANAGER_USERNAME", "LeadFlowAI_gestor_bot")
    monkeypatch.setenv("TELEGRAM_MANAGER_TOKEN", "synthetic-manager-token")
    monkeypatch.setenv("TELEGRAM_MANAGER_WEBHOOK_SECRET", "synthetic-manager-secret")
    monkeypatch.delenv("TELEGRAM_PUBLIC_URL", raising=False)
    org, headers = organization(client, identity)
    bot_id = uuid4().int % 900000000000 + 100000000000
    owner_id = uuid4().int % 900000000000 + 100000000000
    base = f"/v1/orgs/{org}/telegram"
    nonce = parse_qs(urlparse(client.post(base, headers=headers).json()["link"]).query)["start"][0]

    def fake_bot_api(token, method, payload):
        if method == "getManagedBotToken":
            return "synthetic-child-token"
        if method == "getMe":
            return {"id": bot_id, "is_bot": True, "username": "SyntheticCompanyBot"}
        if method == "getWebhookInfo":
            return {"url": f"https://example.test/v1/telegram/bots/{bot_id}/updates"}
        return True

    monkeypatch.setattr("leadflow.telegram.bot_api", fake_bot_api)
    manager_headers = {"X-Telegram-Bot-Api-Secret-Token": "synthetic-manager-secret"}
    manager_path = "/v1/telegram/manager/updates"
    assert client.post(manager_path, headers=manager_headers,
                       json={"update_id": 1, "message": {"text": "/start " + nonce,
                       "from": {"id": owner_id},
                       "chat": {"id": owner_id, "type": "private"}}}).status_code == 200
    assert client.post(manager_path, headers=manager_headers,
                       json={"update_id": 2, "managed_bot": {"user": {"id": owner_id},
                       "bot": {"id": bot_id}}}).status_code == 200
    failed = client.get(base, headers=headers).json()
    assert failed["status"] == "failed"
    assert failed["connected"] is False
    assert failed["failureCode"] == "webhook_unavailable"
    monkeypatch.setenv("TELEGRAM_PUBLIC_URL", "https://example.test")
    resumed = client.post(base + "/resume", headers=headers).json()
    assert resumed["status"] == "connected"


def test_invalid_managed_token_stays_disconnected_and_can_resume(client, identity, monkeypatch):
    monkeypatch.setenv("TELEGRAM_MANAGER_USERNAME", "LeadFlowAI_gestor_bot")
    monkeypatch.setenv("TELEGRAM_MANAGER_TOKEN", "synthetic-manager-token")
    monkeypatch.setenv("TELEGRAM_MANAGER_WEBHOOK_SECRET", "synthetic-manager-secret")
    monkeypatch.setenv("TELEGRAM_PUBLIC_URL", "https://example.test")
    org, headers = organization(client, identity)
    bot_id = uuid4().int % 900000000000 + 100000000000
    owner = uuid4().int % 900000000000 + 100000000000
    base = f"/v1/orgs/{org}/telegram"
    nonce = parse_qs(urlparse(client.post(base, headers=headers).json()["link"]).query)["start"][0]
    valid = False

    def fake_bot_api(token, method, payload):
        if method == "getManagedBotToken":
            return "synthetic-child-token"
        if method == "getMe":
            return {"id": bot_id if valid else bot_id + 1, "is_bot": True,
                    "username": "SyntheticCompanyBot"}
        if method == "getWebhookInfo":
            return {"url": f"https://example.test/v1/telegram/bots/{bot_id}/updates"}
        return True

    monkeypatch.setattr("leadflow.telegram.bot_api", fake_bot_api)
    manager = "/v1/telegram/manager/updates"
    manager_headers = {"X-Telegram-Bot-Api-Secret-Token": "synthetic-manager-secret"}
    assert client.post(manager, headers=manager_headers, json={
        "update_id": 1, "message": {"text": "/start " + nonce,
        "from": {"id": owner}, "chat": {"id": owner, "type": "private"}}}).status_code == 200
    assert client.post(manager, headers=manager_headers, json={
        "update_id": 2, "managed_bot": {"user": {"id": owner},
        "bot": {"id": bot_id}}}).status_code == 200
    assert client.get(base, headers=headers).json()["status"] == "failed"
    valid = True
    assert client.post(base + "/resume", headers=headers).json()["status"] == "connected"
