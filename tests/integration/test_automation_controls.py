from concurrent.futures import ThreadPoolExecutor
from time import monotonic, sleep
from uuid import uuid4


def automatic_conversation(client, identity):
    manager, headers = identity()
    headers["Idempotency-Key"] = str(uuid4())
    organization = client.post("/v1/organizations", headers=headers,
                               json={"name": "Alfa controle sintético"})
    assert organization.status_code == 201
    org = organization.json()["id"]
    channel = client.post(f"/v1/orgs/{org}/test-channels", headers=headers,
                          json={"kind": "telegram"})
    assert channel.status_code == 201
    channel = channel.json()
    inbound = client.post(f"/v1/test-channels/{channel['id']}/events",
                          headers={"X-Test-Channel-Token": channel["token"]}, json={
        "schemaVersion": 1, "eventType": "message", "externalEventId": str(uuid4()),
        "externalMessageId": str(uuid4()), "externalChatId": "chat-1",
        "externalUserId": "lead-1", "occurredAt": "2026-09-24T12:00:00Z",
        "providerSequence": None, "contactName": "Ana",
        "content": {"kind": "text", "text": "Olá"},
    })
    assert inbound.status_code == 200
    return manager, org, headers, channel, inbound.json()["conversationId"]


def pending_automatic_reply(client, identity):
    manager, org, headers, channel, conversation = automatic_conversation(client, identity)
    enabled = client.post(f"/v1/orgs/{org}/test-automation/enable", headers=headers)
    assert enabled.status_code == 200, enabled.text
    prepared = client.post(f"/v1/orgs/{org}/conversations/{conversation}/test-auto-intents",
                           headers=headers, json={"commandId": str(uuid4()),
                                                  "text": "Resposta automática sintética"})
    assert prepared.status_code == 202, prepared.text
    return manager, org, headers, channel, conversation, prepared.json()["intentId"]


def request_human(client, channel):
    response = client.post(f"/v1/test-channels/{channel['id']}/events",
                           headers={"X-Test-Channel-Token": channel["token"]}, json={
        "schemaVersion": 1, "eventType": "message", "externalEventId": str(uuid4()),
        "externalMessageId": str(uuid4()), "externalChatId": "chat-1",
        "externalUserId": "lead-1", "occurredAt": "2026-09-24T12:01:00Z",
        "providerSequence": None, "contactName": "Ana",
        "content": {"kind": "text", "text": "Quero falar com uma pessoa"},
    })
    assert response.status_code == 200


def test_pause_before_authorization_cancels_synthetic_reply(client, identity):
    _, org, headers, channel, conversation, intent = pending_automatic_reply(client, identity)
    paused = client.post(f"/v1/orgs/{org}/automation/pause", headers=headers)
    assert paused.status_code == 200, paused.text
    assert paused.json()["control_applied"] is True
    assert paused.json()["completion"] == "complete"

    dispatch = client.post(f"/v1/orgs/{org}/test-dispatch/{intent}", headers=headers)
    assert dispatch.status_code == 200, dispatch.text
    assert dispatch.json()["status"] == "cancelled"
    history = client.get(f"/v1/orgs/{org}/conversations/{conversation}",
                         headers=headers).json()
    assert history["outboundIntents"][0]["status"] == "cancelled"
    assert client.get(f"/v1/orgs/{org}/test-channels/{channel['id']}/sent",
                      headers=headers).json() == []


def test_pause_before_preparation_rejects_new_automatic_intent(client, identity):
    _, org, headers, _, conversation = automatic_conversation(client, identity)
    assert client.post(f"/v1/orgs/{org}/test-automation/enable",
                       headers=headers).status_code == 200
    assert client.post(f"/v1/orgs/{org}/automation/pause", headers=headers).status_code == 200
    path = f"/v1/orgs/{org}/conversations/{conversation}"
    prepared = client.post(path + "/test-auto-intents", headers=headers, json={
        "commandId": str(uuid4()), "text": "Não preparar",
    })
    assert prepared.status_code == 403
    assert client.get(path, headers=headers).json()["outboundIntents"] == []


def test_pause_during_external_attempt_reports_pending_then_keeps_accepted_history(client, identity):
    _, org, headers, channel, conversation, intent = pending_automatic_reply(client, identity)
    path = f"/v1/orgs/{org}/conversations/{conversation}"
    with ThreadPoolExecutor(max_workers=2) as pool:
        sending = pool.submit(client.post, f"/v1/orgs/{org}/test-dispatch/{intent}",
                              headers={**headers, "X-Test-Dispatch-Delay-Ms": "500"})
        deadline = monotonic() + 2
        while monotonic() < deadline:
            history = client.get(path, headers=headers).json()
            if history["outboundIntents"][0]["status"] == "dispatching":
                break
            sleep(0.01)
        else:
            raise AssertionError("Tentativa externa não iniciou")
        paused = client.post(f"/v1/orgs/{org}/automation/pause", headers=headers)
        assert paused.status_code == 202, paused.text
        assert paused.json()["control_applied"] is True
        assert paused.json()["completion"] == "pending_external_attempt"
        control = f"/v1/orgs/{org}/controls/{paused.json()['controlId']}"
        assert client.get(control, headers=headers).json()["completion"] == "pending_external_attempt"
        assert sending.result().json()["status"] == "accepted"
        completed = client.get(control, headers=headers)
        assert completed.status_code == 200, completed.text
        assert completed.json()["completion"] == "complete"
        assert completed.json()["priorAccepted"] is True
    after = client.get(path, headers=headers).json()
    assert after["outboundIntents"][0]["status"] == "accepted"
    sent = client.get(f"/v1/orgs/{org}/test-channels/{channel['id']}/sent",
                      headers=headers).json()
    assert [message["intentId"] for message in sent] == [intent]


def test_claim_before_authorization_cancels_pending_automatic_reply(client, identity):
    manager, org, headers, channel, conversation, intent = pending_automatic_reply(client, identity)
    request_human(client, channel)
    claim = client.post(f"/v1/orgs/{org}/conversations/{conversation}/claim",
                        headers=headers, json={"version": 1})
    assert claim.status_code == 200, claim.text
    assert claim.json()["claimedBy"] == manager
    assert claim.json()["control_applied"] is True
    assert claim.json()["completion"] == "complete"
    dispatched = client.post(f"/v1/orgs/{org}/test-dispatch/{intent}", headers=headers)
    assert dispatched.json()["status"] == "cancelled"
    assert client.get(f"/v1/orgs/{org}/test-channels/{channel['id']}/sent",
                      headers=headers).json() == []


def test_claim_during_external_attempt_reports_pending_without_erasing_delivery(client, identity):
    manager, org, headers, channel, conversation, intent = pending_automatic_reply(client, identity)
    path = f"/v1/orgs/{org}/conversations/{conversation}"
    with ThreadPoolExecutor(max_workers=2) as pool:
        sending = pool.submit(client.post, f"/v1/orgs/{org}/test-dispatch/{intent}",
                              headers={**headers, "X-Test-Dispatch-Delay-Ms": "500"})
        deadline = monotonic() + 2
        while monotonic() < deadline:
            if client.get(path, headers=headers).json()["outboundIntents"][0]["status"] == "dispatching":
                break
            sleep(0.01)
        else:
            raise AssertionError("Tentativa externa não iniciou")
        request_human(client, channel)
        claimed = client.post(path + "/claim", headers=headers, json={"version": 1})
        assert claimed.status_code == 202, claimed.text
        assert claimed.json()["claimedBy"] == manager
        assert claimed.json()["completion"] == "pending_external_attempt"
        assert sending.result().json()["status"] == "accepted"
    history = client.get(path, headers=headers).json()
    assert history["mode"] == "human"
    assert history["outboundIntents"][0]["status"] == "accepted"


def test_global_resume_keeps_human_and_contact_block_until_explicit_eligible_return(client, identity):
    _, org, headers, channel, conversation, intent = pending_automatic_reply(client, identity)
    request_human(client, channel)
    path = f"/v1/orgs/{org}/conversations/{conversation}"
    assert client.post(path + "/claim", headers=headers, json={"version": 1}).status_code == 200
    blocked = client.post(path + "/test-contact-block", headers=headers, json={"blocked": True})
    assert blocked.status_code == 200, blocked.text
    assert client.post(f"/v1/orgs/{org}/automation/pause", headers=headers).status_code == 200
    paused_version = client.get(path, headers=headers).json()["controlVersion"]
    assert client.post(path + "/resume-ai", headers=headers,
                       json={"version": paused_version}).status_code == 409
    resumed = client.post(f"/v1/orgs/{org}/automation/resume", headers=headers)
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["control_applied"] is True
    history = client.get(path, headers=headers).json()
    assert history["mode"] == "human"
    assert history["contactBlocked"] is True
    assert history["outboundIntents"][0]["status"] == "cancelled"
    denied = client.post(path + "/resume-ai", headers=headers,
                         json={"version": history["controlVersion"]})
    assert denied.status_code == 409

    assert client.post(path + "/test-contact-block", headers=headers,
                       json={"blocked": False}).status_code == 200
    version = client.get(path, headers=headers).json()["controlVersion"]
    _, other_headers = identity()
    assert client.post(path + "/resume-ai", headers=other_headers,
                       json={"version": version}).status_code in (403, 404)
    returned = client.post(path + "/resume-ai", headers=headers, json={"version": version})
    assert returned.status_code == 200, returned.text
    assert returned.json()["mode"] == "automatic"
    assert client.post(f"/v1/orgs/{org}/test-dispatch/{intent}",
                       headers=headers).json()["status"] == "cancelled"


def test_global_pause_preserves_history_and_allows_manual_reply(client, identity):
    _, org, headers, channel, conversation = automatic_conversation(client, identity)
    request_human(client, channel)
    path = f"/v1/orgs/{org}/conversations/{conversation}"
    assert client.post(path + "/claim", headers=headers, json={"version": 1}).status_code == 200
    assert client.post(f"/v1/orgs/{org}/automation/pause", headers=headers).status_code == 200
    reply = client.post(path + "/messages", headers=headers, json={
        "version": 2, "commandId": str(uuid4()), "text": "Atendimento manual continua",
    })
    assert reply.status_code == 202, reply.text
    sent = client.post(f"/v1/orgs/{org}/test-dispatch/{reply.json()['intentId']}",
                       headers=headers)
    assert sent.status_code == 200
    assert sent.json()["status"] == "accepted"
    history = client.get(path, headers=headers).json()
    assert [message["text"] for message in history["messages"]] == [
        "Olá", "Quero falar com uma pessoa"]


def test_contact_block_prevents_pending_and_new_synthetic_sends(client, identity):
    _, org, headers, channel, conversation, intent = pending_automatic_reply(client, identity)
    path = f"/v1/orgs/{org}/conversations/{conversation}"
    blocked = client.post(path + "/test-contact-block", headers=headers, json={"blocked": True})
    assert blocked.status_code == 200
    assert client.post(f"/v1/orgs/{org}/test-dispatch/{intent}",
                       headers=headers).json()["status"] == "cancelled"
    new_intent = client.post(path + "/test-auto-intents", headers=headers, json={
        "commandId": str(uuid4()), "text": "Nova resposta indevida",
    })
    assert new_intent.status_code == 403
    assert client.get(f"/v1/orgs/{org}/test-channels/{channel['id']}/sent",
                      headers=headers).json() == []


def test_unknown_attempt_keeps_control_uncertain_and_blocks_return_to_ai(client, identity):
    _, org, headers, channel, conversation, intent = pending_automatic_reply(client, identity)
    path = f"/v1/orgs/{org}/conversations/{conversation}"
    with ThreadPoolExecutor(max_workers=2) as pool:
        sending = pool.submit(client.post, f"/v1/orgs/{org}/test-dispatch/{intent}",
                              headers={**headers, "X-Test-Dispatch-Delay-Ms": "500",
                                       "X-Test-Delivery-Outcome": "timeout_after_accept"})
        deadline = monotonic() + 2
        while monotonic() < deadline:
            if client.get(path, headers=headers).json()["outboundIntents"][0]["status"] == "dispatching":
                break
            sleep(0.01)
        else:
            raise AssertionError("Tentativa externa não iniciou")
        request_human(client, channel)
        claimed = client.post(path + "/claim", headers=headers, json={"version": 1})
        assert claimed.status_code == 202
        assert sending.result().json()["status"] == "unknown"
    control = client.get(f"/v1/orgs/{org}/controls/{claimed.json()['controlId']}",
                         headers=headers)
    assert control.status_code == 200
    assert control.json()["completion"] == "unknown"
    assert control.json()["priorAccepted"] is False
    assert control.json()["unknownCount"] == 1
    version = client.get(path, headers=headers).json()["controlVersion"]
    assert client.post(path + "/resume-ai", headers=headers,
                       json={"version": version}).status_code == 409
    assert client.post(f"/v1/orgs/{org}/test-dispatch/{intent}",
                       headers=headers).json()["status"] == "unknown"


def test_other_organization_cannot_control_or_inspect_attempts(client, identity):
    _, org, headers, _, _, intent = pending_automatic_reply(client, identity)
    paused = client.post(f"/v1/orgs/{org}/automation/pause", headers=headers)
    _, other_headers = identity()
    assert client.post(f"/v1/orgs/{org}/automation/resume",
                       headers=other_headers).status_code in (403, 404)
    assert client.post(f"/v1/orgs/{org}/test-dispatch/{intent}",
                       headers=other_headers).status_code in (403, 404)
    assert client.get(f"/v1/orgs/{org}/controls/{paused.json()['controlId']}",
                      headers=other_headers).status_code in (403, 404)


def test_enabling_simulation_does_not_clear_global_pause(client, identity):
    _, org, headers, _, _, intent = pending_automatic_reply(client, identity)
    assert client.post(f"/v1/orgs/{org}/automation/pause", headers=headers).status_code == 200
    assert client.post(f"/v1/orgs/{org}/test-automation/enable",
                       headers=headers).status_code == 200
    operation = client.get(f"/v1/orgs/{org}", headers=headers).json()
    assert operation["automation_paused"] is True
    assert client.post(f"/v1/orgs/{org}/test-dispatch/{intent}",
                       headers=headers).json()["status"] == "cancelled"


def test_local_simulation_cannot_resume_real_agent(client, identity, monkeypatch):
    _, org, headers, channel, conversation, _ = pending_automatic_reply(client, identity)
    request_human(client, channel)
    path = f"/v1/orgs/{org}/conversations/{conversation}"
    assert client.post(path + "/claim", headers=headers, json={"version": 1}).status_code == 200
    monkeypatch.setenv("APP_ENV", "production")
    response = client.post(path + "/resume-ai", headers=headers, json={"version": 2})
    assert response.status_code == 401
    monkeypatch.setenv("APP_ENV", "local")
    assert client.get(path, headers=headers).json()["mode"] == "human"
