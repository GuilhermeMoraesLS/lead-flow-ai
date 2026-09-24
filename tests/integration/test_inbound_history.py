from uuid import uuid4


def organization(client, identity, name):
    _, headers = identity()
    headers["Idempotency-Key"] = str(uuid4())
    response = client.post("/v1/organizations", headers=headers, json={"name": name})
    assert response.status_code == 201
    return response.json()["id"], headers


def channel(client, org, headers, kind="telegram"):
    response = client.post(f"/v1/orgs/{org}/test-channels", headers=headers, json={"kind": kind})
    assert response.status_code == 201
    return response.json()


def event(event_id, user="contact-1", text="Olá", name="Ana", chat="chat-1"):
    return {
        "schemaVersion": 1,
        "eventType": "message",
        "externalEventId": event_id,
        "externalMessageId": event_id,
        "externalChatId": chat,
        "externalUserId": user,
        "occurredAt": "2026-09-23T12:00:00Z",
        "providerSequence": None,
        "contactName": name,
        "content": {"kind": "text", "text": text},
    }


def deliver(client, channel_binding, payload):
    return client.post(
        f"/v1/test-channels/{channel_binding['id']}/events",
        headers={"X-Test-Channel-Token": channel_binding["token"]},
        json=payload,
    )


def test_inbound_is_durable_and_repeated_event_has_one_effect(client, identity):
    org, headers = organization(client, identity, "Alfa inbound")
    binding = channel(client, org, headers)
    first = deliver(client, binding, event("event-1"))
    assert first.status_code == 200
    assert first.json()["organizationId"] == org
    assert first.json()["duplicate"] is False
    again = deliver(client, binding, event("event-1"))
    assert again.status_code == 200
    assert again.json()["duplicate"] is True
    assert again.json()["conversationId"] == first.json()["conversationId"]

    history = client.get(f"/v1/orgs/{org}/conversations/{first.json()['conversationId']}", headers=headers)
    assert history.status_code == 200
    assert history.json()["lead"]["externalUserId"] == "contact-1"
    assert [item["text"] for item in history.json()["messages"]] == ["Olá"]
    assert history.json()["inputRevision"] == 1

    second = deliver(client, binding, event("event-2"))
    assert second.status_code == 200
    assert second.json()["conversationId"] == first.json()["conversationId"]
    history = client.get(f"/v1/orgs/{org}/conversations/{first.json()['conversationId']}", headers=headers)
    assert [item["text"] for item in history.json()["messages"]] == ["Olá", "Olá"]
    assert history.json()["inputRevision"] == 2


def test_homonyms_and_channel_or_tenant_do_not_merge(client, identity):
    alpha, alpha_headers = organization(client, identity, "Alfa contacts")
    beta, beta_headers = organization(client, identity, "Beta contacts")
    telegram = channel(client, alpha, alpha_headers)
    whatsapp = channel(client, alpha, alpha_headers, "whatsapp_evolution")
    beta_channel = channel(client, beta, beta_headers)
    first = deliver(client, telegram, event("a1", "one", name="Ana")).json()["conversationId"]
    second = deliver(client, telegram, event("a2", "two", name="Ana")).json()["conversationId"]
    third = deliver(client, whatsapp, event("a3", "one", name="Ana")).json()["conversationId"]
    fourth = deliver(client, beta_channel, event("a4", "one", name="Ana")).json()["conversationId"]
    assert len({first, second, third, fourth}) == 4
    assert client.get(f"/v1/orgs/{beta}/conversations/{first}", headers=beta_headers).status_code == 404
    assert client.get(f"/v1/orgs/{alpha}/conversations/{fourth}", headers=alpha_headers).status_code == 404


def test_untrusted_origin_and_non_message_events_do_not_create_history(client, identity):
    org, headers = organization(client, identity, "Alfa origin")
    binding = channel(client, org, headers)
    invalid = client.post(
        f"/v1/test-channels/{binding['id']}/events",
        headers={"X-Test-Channel-Token": "incorrect"},
        json=event("invalid"),
    )
    assert invalid.status_code == 401
    spoofed = event("spoofed")
    spoofed["organizationId"] = str(uuid4())
    assert deliver(client, binding, spoofed).status_code == 422
    callback = event("callback")
    callback["eventType"] = "connection"
    ignored = deliver(client, binding, callback)
    assert ignored.status_code == 200
    assert ignored.json()["status"] == "ignored"
    received = deliver(client, binding, event("valid"))
    assert received.status_code == 200
    history = client.get(f"/v1/orgs/{org}/conversations/{received.json()['conversationId']}", headers=headers)
    assert len(history.json()["messages"]) == 1


def test_persistence_failure_does_not_ack_or_leave_partial_history(client, identity):
    org, headers = organization(client, identity, "Alfa rollback")
    binding = channel(client, org, headers)
    first = deliver(client, binding, event("message-1"))
    conversation = first.json()["conversationId"]
    collision = event("event-2")
    collision["externalMessageId"] = "message-1"
    failed = deliver(client, binding, collision)
    assert failed.status_code == 503
    assert failed.json()["error"]["retryable"] is True
    history = client.get(f"/v1/orgs/{org}/conversations/{conversation}", headers=headers).json()
    assert history["inputRevision"] == 1
    assert len(history["messages"]) == 1
    retried = deliver(client, binding, event("event-2"))
    assert retried.status_code == 200
    assert retried.json()["duplicate"] is False
    history = client.get(f"/v1/orgs/{org}/conversations/{conversation}", headers=headers).json()
    assert history["inputRevision"] == 2
    assert len(history["messages"]) == 2


def test_outbox_republication_has_one_consumed_effect(client, identity):
    org, headers = organization(client, identity, "Alfa outbox")
    binding = channel(client, org, headers)
    received = deliver(client, binding, event("outbox-1")).json()
    url = f"/v1/orgs/{org}/test-outbox/{received['outboxId']}/publish"
    crashed = client.post(url, headers={**headers, "X-Test-Crash-After-Effect": "true"})
    assert crashed.status_code == 503
    first = client.post(url, headers=headers)
    second = client.post(url, headers=headers)
    assert first.status_code == 200
    assert first.json()["newEffect"] is False
    assert second.status_code == 200
    assert second.json()["newEffect"] is False
    assert second.json()["effectCount"] == 1
