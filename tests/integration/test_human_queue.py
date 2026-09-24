from uuid import uuid4

import httpx


def setup_conversation(client, identity):
    manager_id, headers = identity()
    headers["Idempotency-Key"] = str(uuid4())
    organization = client.post(
        "/v1/organizations", headers=headers, json={"name": "Alfa atendimento humano"}
    )
    assert organization.status_code == 201
    org = organization.json()["id"]
    channel = client.post(
        f"/v1/orgs/{org}/test-channels", headers=headers, json={"kind": "telegram"}
    )
    assert channel.status_code == 201
    return manager_id, org, headers, channel.json()


def send(client, channel, event_id, text):
    return client.post(
        f"/v1/test-channels/{channel['id']}/events",
        headers={"X-Test-Channel-Token": channel["token"]},
        json={
            "schemaVersion": 1,
            "eventType": "message",
            "externalEventId": event_id,
            "externalMessageId": event_id,
            "externalChatId": "chat-1",
            "externalUserId": "lead-1",
            "occurredAt": "2026-09-23T12:00:00Z",
            "providerSequence": None,
            "contactName": "Ana",
            "content": {"kind": "text", "text": text},
        },
    )


def test_explicit_request_suspends_automation_and_appears_with_history(client, identity):
    manager, org, headers, channel = setup_conversation(client, identity)
    first = send(client, channel, "first", "Tenho uma dúvida sobre o produto.")
    assert first.status_code == 200
    assert client.get(f"/v1/orgs/{org}/human-queue", headers=headers).json() == []
    requested = send(client, channel, "request", "Quero falar com uma pessoa")
    assert requested.status_code == 200
    conversation = requested.json()["conversationId"]

    queue = client.get(f"/v1/orgs/{org}/human-queue", headers=headers)
    assert queue.status_code == 200
    assert len(queue.json()) == 1
    item = queue.json()[0]
    assert item["conversationId"] == conversation
    assert item["reason"] == "explicit_request"
    assert item["ownerMemberId"] == manager
    assert item["nextAction"] == "Atribuir manualmente a vendedor elegível."
    assert item["assignedSellerId"] is None
    assert item["claimedBy"] is None

    history = client.get(f"/v1/orgs/{org}/conversations/{conversation}", headers=headers)
    assert history.status_code == 200
    assert history.json()["mode"] == "awaiting_human"
    assert history.json()["lead"]["stage"] == "handed_off"
    assert history.json()["handoffReason"] == "explicit_request"
    assert [message["text"] for message in history.json()["messages"]] == [
        "Tenho uma dúvida sobre o produto.", "Quero falar com uma pessoa"
    ]


def test_no_eligible_seller_keeps_manager_queue_without_a_promise(client, identity):
    _, org, headers, channel = setup_conversation(client, identity)
    seller = client.post(
        f"/v1/orgs/{org}/sellers", headers=headers,
        json={"name": "Bia", "email": f"bia-{uuid4().hex}@example.test",
              "phone": "+5511999990000", "available": False},
    )
    assert seller.status_code == 201
    requested = send(client, channel, "request", "Preciso falar com um atendente")
    assert requested.status_code == 200
    item = client.get(f"/v1/orgs/{org}/human-queue", headers=headers).json()[0]
    assert item["state"] == "open"
    assert item["assignedSellerId"] is None
    assert item["nextAction"] == "Atribuir manualmente a vendedor elegível."
    assert "imediato" not in str(item).lower()
    history = client.get(
        f"/v1/orgs/{org}/conversations/{requested.json()['conversationId']}", headers=headers
    ).json()
    assert [message["text"] for message in history["messages"]] == [
        "Preciso falar com um atendente"
    ]


def test_missing_summary_and_repeated_request_preserve_one_pending_handoff(client, identity):
    _, org, headers, channel = setup_conversation(client, identity)
    first = send(client, channel, "request", "Quero falar com uma pessoa")
    assert first.status_code == 200
    again = send(client, channel, "request", "Quero falar com uma pessoa")
    assert again.status_code == 200
    assert again.json()["duplicate"] is True
    later = send(client, channel, "more-context", "Meu pedido é sobre entrega.")
    assert later.status_code == 200
    conversation = first.json()["conversationId"]
    history = client.get(f"/v1/orgs/{org}/conversations/{conversation}", headers=headers).json()
    assert history["mode"] == "awaiting_human"
    assert history["summary"] is None
    assert history["summaryStatus"] == "unavailable"
    assert len(history["messages"]) == 2
    queue = client.get(f"/v1/orgs/{org}/human-queue", headers=headers).json()
    assert len(queue) == 1
    assert queue[0]["conversationId"] == conversation


def test_queue_and_history_do_not_leak_to_another_tenant_or_seller(client, identity):
    _, org, headers, channel = setup_conversation(client, identity)
    conversation = send(client, channel, "request", "Quero falar com uma pessoa").json()["conversationId"]
    _, other_headers = identity()
    assert client.get(f"/v1/orgs/{org}/human-queue", headers=other_headers).status_code == 404
    assert client.get(
        f"/v1/orgs/{org}/conversations/{conversation}", headers=other_headers
    ).status_code == 404

    email = f"seller-{uuid4().hex}@example.test"
    seller = client.post(f"/v1/orgs/{org}/sellers", headers=headers, json={
        "name": "Bia", "email": email, "phone": "+5511999990000", "available": True,
    }).json()
    enabled = client.post(f"/v1/orgs/{org}/sellers/{seller['id']}/enable", headers=headers)
    assert enabled.status_code == 200
    login = httpx.post("http://127.0.0.1:54321/token?grant_type=password", json={
        "email": email, "password": enabled.json()["temporary_password"],
    })
    assert login.status_code == 200
    seller_headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert client.get(f"/v1/orgs/{org}/human-queue", headers=seller_headers).status_code == 404
    assert client.get(
        f"/v1/orgs/{org}/conversations/{conversation}", headers=seller_headers
    ).status_code == 404
