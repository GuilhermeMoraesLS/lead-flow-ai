from concurrent.futures import ThreadPoolExecutor
from time import monotonic, sleep

from tests.integration.test_human_reply import pending_reply


def test_abandoned_dispatch_becomes_unknown_without_resend(client, identity):
    _, org, headers, channel, conversation, intent = pending_reply(client, identity)
    crashed = client.post(f"/v1/orgs/{org}/test-dispatch/{intent}", headers={
        **headers, "X-Test-Crash-After-Start": "true",
    })
    assert crashed.status_code == 503
    path = f"/v1/orgs/{org}/conversations/{conversation}"
    assert client.get(path, headers=headers).json()["outboundIntents"][0]["status"] == "dispatching"

    recovered = client.post(f"/v1/orgs/{org}/test-recovery/run", headers=headers,
                            json={"advanceSeconds": 121})
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["abandonedDispatches"] == 1
    history = client.get(path, headers=headers).json()["outboundIntents"][0]
    assert history["status"] == "unknown"
    assert history["incidentReason"] == "confirmation_lost"
    assert "Não reenviar" in history["incidentNextAction"]
    incidents = client.get(f"/v1/orgs/{org}/recovery/incidents", headers=headers)
    assert incidents.status_code == 200
    incident = next(item for item in incidents.json() if item["intentId"] == intent)
    assert incident["reason"] == "confirmation_lost"
    assert incident["ownerMemberId"]
    assert incident["nextAction"]
    assert incident["state"] == "open"
    resolve_path = f"/v1/orgs/{org}/recovery/incidents/{incident['id']}/resolve"
    assert client.post(resolve_path, headers=headers, json={}).status_code == 422
    resolved = client.post(resolve_path, headers=headers,
                           json={"evidence": "Canal consultado manualmente; resultado não conclusivo."})
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["state"] == "resolved"
    assert client.get(path, headers=headers).json()["outboundIntents"][0]["status"] == "unknown"
    assert next(item for item in client.get(f"/v1/orgs/{org}/recovery/incidents",
                                           headers=headers).json() if item["id"] == incident["id"])["state"] == "resolved"
    assert client.post(f"/v1/orgs/{org}/test-dispatch/{intent}", headers=headers).json()["status"] == "unknown"
    assert client.get(f"/v1/orgs/{org}/test-channels/{channel['id']}/sent",
                      headers=headers).json() == []
    assert client.post(f"/v1/orgs/{org}/test-recovery/run", headers=headers,
                       json={"advanceSeconds": 121}).json()["abandonedDispatches"] == 0


def test_recovery_does_not_block_another_conversation(client, identity):
    _, org, headers, _, _, abandoned = pending_reply(client, identity)
    assert client.post(f"/v1/orgs/{org}/test-dispatch/{abandoned}", headers={
        **headers, "X-Test-Crash-After-Start": "true",
    }).status_code == 503
    _, other_org, other_headers, _, _, healthy = pending_reply(client, identity)
    assert client.post(f"/v1/orgs/{org}/test-recovery/run", headers=headers,
                       json={"advanceSeconds": 121}).status_code == 200
    assert client.post(f"/v1/orgs/{other_org}/test-dispatch/{healthy}",
                       headers=other_headers).json()["status"] == "accepted"


def test_expired_attempt_rejects_late_worker_result(client, identity):
    _, org, headers, channel, conversation, intent = pending_reply(client, identity)
    path = f"/v1/orgs/{org}/conversations/{conversation}"
    with ThreadPoolExecutor(max_workers=2) as pool:
        old_worker = pool.submit(client.post, f"/v1/orgs/{org}/test-dispatch/{intent}",
                                 headers={**headers, "X-Test-Dispatch-Delay-Ms": "500"})
        deadline = monotonic() + 2
        while monotonic() < deadline:
            if client.get(path, headers=headers).json()["outboundIntents"][0]["status"] == "dispatching":
                break
            sleep(0.01)
        else:
            raise AssertionError("Tentativa não iniciou")
        recovered = client.post(f"/v1/orgs/{org}/test-recovery/run", headers=headers,
                                json={"advanceSeconds": 121})
        assert recovered.json()["abandonedDispatches"] == 1
        assert old_worker.result().json()["status"] == "unknown"
    assert client.get(path, headers=headers).json()["outboundIntents"][0]["status"] == "unknown"
    assert client.get(f"/v1/orgs/{org}/test-channels/{channel['id']}/sent",
                      headers=headers).json() == []
