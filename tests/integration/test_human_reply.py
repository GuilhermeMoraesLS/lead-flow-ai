from concurrent.futures import ThreadPoolExecutor
from time import monotonic, sleep
from uuid import uuid4

import httpx


def requested_conversation(client, identity):
    manager, headers = identity()
    headers["Idempotency-Key"] = str(uuid4())
    org_response = client.post(
        "/v1/organizations", headers=headers, json={"name": "Alfa resposta humana"}
    )
    assert org_response.status_code == 201
    org = org_response.json()["id"]
    channel_response = client.post(
        f"/v1/orgs/{org}/test-channels", headers=headers, json={"kind": "telegram"}
    )
    assert channel_response.status_code == 201
    channel = channel_response.json()
    inbound = client.post(
        f"/v1/test-channels/{channel['id']}/events",
        headers={"X-Test-Channel-Token": channel["token"]},
        json={
            "schemaVersion": 1, "eventType": "message",
            "externalEventId": str(uuid4()), "externalMessageId": str(uuid4()),
            "externalChatId": "chat-1", "externalUserId": "lead-1",
            "occurredAt": "2026-09-23T12:00:00Z", "providerSequence": None,
            "contactName": "Ana",
            "content": {"kind": "text", "text": "Quero falar com uma pessoa"},
        },
    )
    assert inbound.status_code == 200
    return manager, org, headers, channel, inbound.json()["conversationId"]


def test_manager_claim_changes_mode_without_implying_seller_assignment(client, identity):
    manager, org, headers, _, conversation = requested_conversation(client, identity)
    path = f"/v1/orgs/{org}/conversations/{conversation}"
    before = client.get(path, headers=headers)
    assert before.status_code == 200
    assert before.json()["mode"] == "awaiting_human"
    assert before.json()["assignedSellerId"] is None

    claim = client.post(path + "/claim", headers=headers, json={"version": 1})
    assert claim.status_code == 200, claim.text
    assert claim.json()["claimedBy"] == manager
    assert claim.json()["mode"] == "human"

    after = client.get(path, headers=headers)
    assert after.status_code == 200
    assert after.json()["claimedBy"] == manager
    assert after.json()["assignedSellerId"] is None


def eligible_seller(client, org, manager_headers):
    email = f"reply-{uuid4().hex}@example.test"
    seller = client.post(f"/v1/orgs/{org}/sellers", headers=manager_headers, json={
        "name": "Bia", "email": email, "phone": "+5511999990000", "available": True,
    })
    assert seller.status_code == 201
    seller_id = seller.json()["id"]
    enabled = client.post(f"/v1/orgs/{org}/sellers/{seller_id}/enable", headers=manager_headers)
    assert enabled.status_code == 200
    temporary_password = enabled.json()["temporary_password"]
    login = httpx.post("http://127.0.0.1:54321/token?grant_type=password", json={
        "email": email, "password": temporary_password,
    })
    assert login.status_code == 200
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    changed = client.post(f"/v1/orgs/{org}/sellers/me/password", headers=headers, json={
        "current_password": temporary_password, "new_password": "NovaSenhaSintetica-2026!",
    })
    assert changed.status_code == 200
    return seller_id, headers


def test_assignment_does_not_claim_and_only_assigned_seller_can_claim(client, identity):
    _, org, manager_headers, _, conversation = requested_conversation(client, identity)
    seller_id, seller_headers = eligible_seller(client, org, manager_headers)
    path = f"/v1/orgs/{org}/conversations/{conversation}"

    assigned = client.post(path + "/assign", headers=manager_headers, json={
        "sellerId": seller_id, "reason": "Atendimento solicitado", "version": 1,
    })
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["assignedSellerId"] == seller_id
    assert assigned.json()["claimedBy"] is None
    assert assigned.json()["mode"] == "awaiting_human"

    claim = client.post(path + "/claim", headers=seller_headers, json={"version": 2})
    assert claim.status_code == 200, claim.text
    assert claim.json()["mode"] == "human"
    seller_view = client.get(path, headers=seller_headers)
    assert seller_view.status_code == 200, seller_view.text
    assert seller_view.json()["claimedBy"] == \
        client.get(path, headers=manager_headers).json()["claimedBy"]


def test_competing_claims_leave_one_current_owner(client, identity):
    _, org, manager_headers, _, conversation = requested_conversation(client, identity)
    seller_id, seller_headers = eligible_seller(client, org, manager_headers)
    path = f"/v1/orgs/{org}/conversations/{conversation}"
    assigned = client.post(path + "/assign", headers=manager_headers, json={
        "sellerId": seller_id, "reason": "Atendimento solicitado", "version": 1,
    })
    assert assigned.status_code == 200
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(client.post, path + "/claim", headers=headers,
                               json={"version": 2})
                   for headers in (manager_headers, seller_headers)]
        responses = [future.result() for future in futures]
    assert sorted(response.status_code for response in responses) == [200, 409]
    owner = client.get(path, headers=manager_headers).json()["claimedBy"]
    assert owner == next(response.json()["claimedBy"] for response in responses
                         if response.status_code == 200)


def test_manual_reply_is_pending_until_dispatch_and_keeps_author(client, identity):
    manager, org, headers, _, conversation = requested_conversation(client, identity)
    path = f"/v1/orgs/{org}/conversations/{conversation}"
    assert client.post(path + "/claim", headers=headers,
                       json={"version": 1}).status_code == 200
    command_id = str(uuid4())
    reply = client.post(path + "/messages", headers=headers, json={
        "version": 2, "commandId": command_id, "text": "Olá, posso ajudar com a entrega.",
    })
    assert reply.status_code == 202, reply.text
    assert reply.json()["status"] == "pending"
    assert reply.json()["authorId"] == manager
    history = client.get(path, headers=headers).json()
    assert history["outboundIntents"][0]["id"] == reply.json()["intentId"]
    assert history["outboundIntents"][0]["status"] == "pending"
    assert history["outboundIntents"][0]["readStatus"] == "unknown"
    assert [item["text"] for item in history["messages"]] == ["Quero falar com uma pessoa"]


def pending_reply(client, identity):
    manager, org, headers, channel, conversation = requested_conversation(client, identity)
    path = f"/v1/orgs/{org}/conversations/{conversation}"
    assert client.post(path + "/claim", headers=headers,
                       json={"version": 1}).status_code == 200
    reply = client.post(path + "/messages", headers=headers, json={
        "version": 2, "commandId": str(uuid4()), "text": "Olá, posso ajudar com a entrega.",
    })
    assert reply.status_code == 202
    return manager, org, headers, channel, conversation, reply.json()["intentId"]


def test_dispatch_acceptance_is_visible_but_not_read_receipt(client, identity):
    _, org, headers, channel, conversation, intent = pending_reply(client, identity)
    dispatched = client.post(f"/v1/orgs/{org}/test-dispatch/{intent}", headers={
        **headers, "X-Test-Delivery-Outcome": "accepted",
    })
    assert dispatched.status_code == 200, dispatched.text
    assert dispatched.json()["status"] == "accepted"
    history = client.get(f"/v1/orgs/{org}/conversations/{conversation}",
                         headers=headers).json()
    assert history["outboundIntents"][0]["status"] == "accepted"
    assert history["outboundIntents"][0]["readStatus"] == "unknown"
    sent = client.get(f"/v1/orgs/{org}/test-channels/{channel['id']}/sent",
                      headers=headers)
    assert sent.status_code == 200
    assert [message["intentId"] for message in sent.json()] == [intent]


def test_rejected_and_unknown_remain_distinct_and_never_send_twice(client, identity):
    for outcome, expected_sent in (("rejected", 0), ("timeout_after_accept", 1)):
        _, org, headers, channel, conversation, intent = pending_reply(client, identity)
        path = f"/v1/orgs/{org}/test-dispatch/{intent}"
        first = client.post(path, headers={**headers, "X-Test-Delivery-Outcome": outcome})
        assert first.status_code == 200, first.text
        expected_status = "unknown" if outcome == "timeout_after_accept" else "rejected"
        assert first.json()["status"] == expected_status
        repeated = client.post(path, headers={**headers, "X-Test-Delivery-Outcome": "accepted"})
        assert repeated.status_code == 200
        assert repeated.json()["status"] == expected_status
        history = client.get(f"/v1/orgs/{org}/conversations/{conversation}",
                             headers=headers).json()
        assert history["outboundIntents"][0]["status"] == expected_status
        assert history["outboundIntents"][0]["readStatus"] == "unknown"
        if expected_status == "unknown":
            assert history["outboundIntents"][0]["incidentReason"] == "confirmation_lost"
            assert "Não reenviar" in history["outboundIntents"][0]["incidentNextAction"]
        sent = client.get(f"/v1/orgs/{org}/test-channels/{channel['id']}/sent",
                          headers=headers).json()
        assert len(sent) == expected_sent


def test_reply_limit_rejects_whole_text_without_creating_intent(client, identity):
    _, org, headers, _, conversation = requested_conversation(client, identity)
    path = f"/v1/orgs/{org}/conversations/{conversation}"
    assert client.post(path + "/claim", headers=headers,
                       json={"version": 1}).status_code == 200
    too_long = client.post(path + "/messages", headers=headers, json={
        "version": 2, "commandId": str(uuid4()), "text": "x" * 4097,
    })
    assert too_long.status_code == 422
    assert client.get(path, headers=headers).json()["outboundIntents"] == []


def test_dispatch_rejects_foreign_manager(client, identity):
    _, org, _, _, _, intent = pending_reply(client, identity)
    _, other_headers = identity()
    denied = client.post(f"/v1/orgs/{org}/test-dispatch/{intent}",
                         headers=other_headers)
    assert denied.status_code in (403, 404)


def test_assigned_seller_can_see_queue_reply_and_dispatch(client, identity):
    _, org, manager_headers, _, conversation = requested_conversation(client, identity)
    seller_id, seller_headers = eligible_seller(client, org, manager_headers)
    path = f"/v1/orgs/{org}/conversations/{conversation}"
    assigned = client.post(path + "/assign", headers=manager_headers, json={
        "sellerId": seller_id, "reason": "Atendimento solicitado", "version": 1,
    })
    assert assigned.status_code == 200
    queue = client.get(f"/v1/orgs/{org}/human-queue", headers=seller_headers)
    assert queue.status_code == 200, queue.text
    assert [item["conversationId"] for item in queue.json()] == [conversation]
    assert client.post(path + "/claim", headers=seller_headers,
                       json={"version": 2}).status_code == 200
    reply = client.post(path + "/messages", headers=seller_headers, json={
        "version": 3, "commandId": str(uuid4()), "text": "Resposta da vendedora",
    })
    assert reply.status_code == 202, reply.text
    sent = client.post(f"/v1/orgs/{org}/test-dispatch/{reply.json()['intentId']}",
                       headers=seller_headers)
    assert sent.status_code == 200, sent.text
    assert sent.json()["status"] == "accepted"


def test_revoked_seller_cannot_inspect_completed_dispatch_with_old_token(client, identity):
    _, org, manager_headers, _, conversation = requested_conversation(client, identity)
    seller_id, seller_headers = eligible_seller(client, org, manager_headers)
    path = f"/v1/orgs/{org}/conversations/{conversation}"
    assert client.post(path + "/assign", headers=manager_headers, json={
        "sellerId": seller_id, "reason": "Atendimento solicitado", "version": 1,
    }).status_code == 200
    assert client.post(path + "/claim", headers=seller_headers,
                       json={"version": 2}).status_code == 200
    reply = client.post(path + "/messages", headers=seller_headers, json={
        "version": 3, "commandId": str(uuid4()), "text": "Resposta da vendedora",
    })
    assert reply.status_code == 202
    dispatch_path = f"/v1/orgs/{org}/test-dispatch/{reply.json()['intentId']}"
    assert client.post(dispatch_path, headers=seller_headers).json()["status"] == "accepted"
    assert client.post(f"/v1/orgs/{org}/sellers/{seller_id}/revoke",
                       headers=manager_headers).status_code == 200
    assert client.post(dispatch_path, headers=seller_headers).status_code == 403


def test_only_one_intent_dispatches_at_a_time_for_conversation(client, identity):
    _, org, headers, channel, conversation, first_intent = pending_reply(client, identity)
    path = f"/v1/orgs/{org}/conversations/{conversation}"
    second = client.post(path + "/messages", headers=headers, json={
        "version": 2, "commandId": str(uuid4()), "text": "Segunda mensagem",
    })
    assert second.status_code == 202
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(client.post, f"/v1/orgs/{org}/test-dispatch/{first_intent}",
                            headers={**headers, "X-Test-Dispatch-Delay-Ms": "500"})
        deadline = monotonic() + 2
        while monotonic() < deadline:
            history = client.get(path, headers=headers).json()
            if any(item["status"] == "dispatching" for item in history["outboundIntents"]):
                break
            sleep(0.01)
        else:
            raise AssertionError("A primeira tentativa não iniciou")
        waiting = client.post(f"/v1/orgs/{org}/test-dispatch/{second.json()['intentId']}",
                              headers=headers)
        assert waiting.status_code == 200
        assert waiting.json()["status"] == "pending"
        assert first.result().json()["status"] == "accepted"
    sent = client.get(f"/v1/orgs/{org}/test-channels/{channel['id']}/sent",
                      headers=headers).json()
    assert [item["intentId"] for item in sent] == [first_intent]
