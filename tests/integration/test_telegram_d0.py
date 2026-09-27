"""D0 Telegram path with synthetic provider responses and a real local database."""

from hashlib import sha256
from uuid import uuid4

import httpx

from scripts.local import admin_connection


def test_d0_sender_distinguishes_proven_rejection_from_uncertainty(monkeypatch):
    from leadflow.recovery import _send_telegram

    class Rejected:
        status_code = 403
        is_success = False

        def json(self):
            return {"ok": False}

    monkeypatch.setattr("httpx.post", lambda *args, **kwargs: Rejected())
    assert _send_telegram("synthetic", 88, "synthetic") == ("rejected", None)


def test_d0_activation_batch_reply_and_replay(client, identity, monkeypatch):
    from leadflow.recovery import process_telegram_due, seal_telegram_due
    from leadflow.telegram import encrypt_secret

    _, headers = identity()
    org = client.post("/v1/organizations", headers={**headers,
        "Idempotency-Key": str(uuid4())}, json={"name": "D0 sintética"}).json()["id"]
    base = f"/v1/orgs/{org}"
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    assert client.post(base + "/telegram/d0", headers=headers).status_code == 409
    created_product = client.post(base + "/products", headers=headers,
        json={"name": "Consulta", "price": "0", "available": True})
    assert created_product.status_code == 201
    config = client.get(base + "/agent-config", headers=headers).json()
    assert client.put(base + "/agent-config", headers=headers, json={
        "name": "Atendente", "identity": "Demonstração", "instructions": "Consultar catálogo",
        "version": config["version"],
    }).status_code == 200
    bot_id = uuid4().int % 900000000000 + 100000000000
    secret = "synthetic-webhook-" + uuid4().hex
    with admin_connection() as conn:
        conn.execute("""INSERT INTO app.telegram_provisioning
            (organization_id, request_hash, request_ciphertext,
             bot_id, bot_username, token_ciphertext,
             webhook_secret_ciphertext, webhook_secret_hash, status)
            VALUES (%s, %s, %s, %s, 'D0SyntheticBot', %s, %s, %s, 'connected')""",
            (org, sha256(str(uuid4()).encode()).hexdigest(), encrypt_secret("synthetic-nonce"),
             bot_id, encrypt_secret("synthetic-bot-token"),
             encrypt_secret(secret), sha256(secret.encode()).hexdigest()))
        old_batch = conn.execute("""INSERT INTO app.telegram_message_batches
            (organization_id, bot_id, chat_id, body)
            VALUES (%s, %s, 77, 'Pergunta antes da ativação') RETURNING id""",
            (org, bot_id)).fetchone()[0]
    assert client.post(base + "/telegram/d0", headers=headers).json() == {"enabled": True}
    assert client.get(base + "/telegram/d0", headers=headers).json() == {"enabled": True}
    with admin_connection() as conn:
        assert conn.execute("""SELECT status, error_code FROM app.telegram_message_batches
            WHERE id = %s""", (old_batch,)).fetchone() == ("processed", "before_activation")
    product = created_product.json()
    _, other_headers = identity()
    calls = []

    class Response:
        status_code = 200
        is_success = True

        def __init__(self, data):
            self.data = data

        def raise_for_status(self):
            pass

        def json(self):
            return self.data

    def provider(url, **kwargs):
        calls.append(url)
        if "api.openai.com" in url:
            return Response({"model": "gpt-5.4-mini-2026-03-17", "usage": {
                "input_tokens": 100, "output_tokens": 20},
                "output": [{"type": "message", "content": [{"type": "output_text",
                    "text": '{"product_id":"' + product["id"] + '"}'}]}]})
        if kwargs["json"]["chat_id"] == 90:
            raise httpx.ReadTimeout("synthetic uncertain send")
        return Response({"ok": True, "result": {"message_id": 123}})

    monkeypatch.setattr("httpx.post", provider)
    event = {"update_id": 1, "message": {"message_id": 1,
        "text": "Quanto custa a Consulta?", "from": {"id": 88, "is_bot": False},
        "chat": {"id": 88, "type": "private"}}}
    path = f"/v1/telegram/bots/{bot_id}/updates"
    webhook_headers = {"X-Telegram-Bot-Api-Secret-Token": secret}
    assert client.post(path, json=event).status_code == 401
    assert client.post(path, json=event, headers=webhook_headers).status_code == 200
    assert client.post(path, json=event, headers=webhook_headers).status_code == 200
    with admin_connection() as conn:
        conn.execute("""UPDATE app.telegram_message_buffer
            SET received_at = now() - interval '6 seconds' WHERE bot_id = %s""", (bot_id,))
    assert seal_telegram_due() >= 1
    assert process_telegram_due() >= 1
    assert process_telegram_due() == 0
    assert len([url for url in calls if "api.openai.com" in url]) == 1
    assert len([url for url in calls if "/sendMessage" in url]) == 1
    batch = client.get(base + "/telegram/d0/conversations", headers=headers).json()[0]
    assert batch["deliveryStatus"] == "accepted"
    assert batch["model"] == "gpt-5.4-mini-2026-03-17"
    assert batch["promptVersion"] == "catalog-d01-v1"
    assert batch["commercialRevision"] == 2
    assert batch["estimatedCostUsd"] == "0.000165"
    history = client.get(base + "/conversations/" + batch["conversationId"],
                         headers=headers).json()
    assert history["messages"][0]["text"] == "Quanto custa a Consulta?"
    assert history["outboundIntents"][0]["status"] == "accepted"

    def inbound(chat_id, message_id, body):
        incoming = {"update_id": message_id + 10, "message": {
            "message_id": message_id, "text": body,
            "from": {"id": chat_id, "is_bot": False},
            "chat": {"id": chat_id, "type": "private"}}}
        assert client.post(path, json=incoming, headers=webhook_headers).status_code == 200
        with admin_connection() as conn:
            conn.execute("""UPDATE app.telegram_message_buffer
                SET received_at = now() - interval '6 seconds'
                WHERE bot_id = %s AND chat_id = %s AND batch_id IS NULL""", (bot_id, chat_id))
        assert seal_telegram_due() >= 1
        assert process_telegram_due() >= 1
        return client.get(base + "/telegram/d0/conversations", headers=headers).json()[0]

    uncertain = inbound(90, 2, "Quanto custa a Consulta?")
    assert uncertain["deliveryStatus"] == "unknown"
    sent_before = len([url for url in calls if "/sendMessage" in url])
    assert process_telegram_due() == 0
    assert len([url for url in calls if "/sendMessage" in url]) == sent_before
    unsupported = inbound(93, 6, "Olá")
    unsupported_history = client.get(base + "/conversations/" + unsupported["conversationId"],
                                     headers=headers).json()
    assert unsupported_history["mode"] == "automatic"
    assert unsupported_history["outboundIntents"][0]["status"] == "accepted"
    assert unsupported["deliveryStatus"] == "accepted"
    assert unsupported["estimatedCostUsd"] == "0.000000"
    human = inbound(88, 3, "Quero falar com uma pessoa")
    assert human["deliveryStatus"] is None
    human_history = client.get(base + "/conversations/" + human["conversationId"],
                               headers=headers).json()
    assert human_history["mode"] == "awaiting_human"
    opted_out = inbound(91, 4, "Pare de me enviar mensagens")
    blocked = client.get(base + "/conversations/" + opted_out["conversationId"],
                         headers=headers).json()
    assert blocked["contactBlocked"] is True
    assert client.post(base + "/automation/pause", headers=headers).status_code == 200
    paused = inbound(92, 5, "Quanto custa a Consulta?")
    assert paused["deliveryStatus"] is None
    assert len([url for url in calls if "/sendMessage" in url]) == sent_before
    assert client.get(base + "/telegram/d0/conversations", headers=other_headers).status_code == 404
