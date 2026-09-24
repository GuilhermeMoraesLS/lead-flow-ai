import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from time import monotonic, sleep
from uuid import uuid4

from tests.integration.test_automation_controls import pending_automatic_reply
from tests.integration.test_inbound_history import channel as create_channel
from tests.integration.test_inbound_history import deliver, event


def test_explicit_stop_persists_origin_and_cancels_pending_automatic_reply(client, identity):
    _, org, headers, channel, conversation, intent = pending_automatic_reply(client, identity)
    stopped = deliver(client, channel, event(str(uuid4()), user="lead-1",
                                             text="Não quero mais mensagens automáticas"))
    assert stopped.status_code == 200, stopped.text
    assert stopped.json()["control_applied"] is True
    history = client.get(f"/v1/orgs/{org}/conversations/{conversation}", headers=headers)
    assert history.status_code == 200
    assert history.json()["optOut"]["reason"] == "explicit_stop_request"
    assert history.json()["optOut"]["sourceEventId"] == stopped.json()["sourceEventId"]
    assert history.json()["outboundIntents"][0]["status"] == "cancelled"
    separate_process = subprocess.run([sys.executable, "-c", """
import json, sys
from fastapi.testclient import TestClient
from leadflow.main import app
data = json.load(sys.stdin)
with TestClient(app) as client:
    result = client.get(data['path'], headers=data['headers'])
    assert result.status_code == 200
    assert result.json()['optOut']['sourceEventId'] == data['source']
    assert result.json()['contactBlocked'] is True
"""], input=json.dumps({"path": f"/v1/orgs/{org}/conversations/{conversation}",
                        "headers": headers, "source": stopped.json()["sourceEventId"]}),
        text=True, capture_output=True, check=False)
    assert separate_process.returncode == 0, separate_process.stderr
    dispatch = client.post(f"/v1/orgs/{org}/test-dispatch/{intent}", headers=headers)
    assert dispatch.json()["status"] == "cancelled"
    assert client.get(f"/v1/orgs/{org}/test-channels/{channel['id']}/sent",
                      headers=headers).json() == []


def test_new_contact_retry_global_resume_and_test_unblock_preserve_opt_out(client, identity):
    _, org, headers, channel, conversation, _ = pending_automatic_reply(client, identity)
    stopped_event = event(str(uuid4()), user="lead-1", text="Pare de me enviar mensagens")
    stopped = deliver(client, channel, stopped_event)
    assert stopped.status_code == 200
    repeated = deliver(client, channel, stopped_event)
    assert repeated.json()["duplicate"] is True
    assert client.get(f"/v1/orgs/{org}/conversations/{conversation}",
                      headers=headers).json()["optOut"]["sourceEventId"] == stopped.json()["sourceEventId"]
    assert deliver(client, channel, event(str(uuid4()), user="lead-1",
                                          text="Olá novamente")).status_code == 200
    assert client.post(f"/v1/orgs/{org}/automation/pause", headers=headers).status_code == 200
    assert client.post(f"/v1/orgs/{org}/automation/resume", headers=headers).status_code == 200
    path = f"/v1/orgs/{org}/conversations/{conversation}"
    history = client.get(path, headers=headers).json()
    assert history["optOut"]["sourceEventId"] == stopped.json()["sourceEventId"]
    assert history["contactBlocked"] is True
    assert [m["text"] for m in history["messages"]][-2:] == [
        "Pare de me enviar mensagens", "Olá novamente"]
    assert client.post(path + "/test-contact-block", headers=headers,
                       json={"blocked": False}).status_code == 409
    assert client.post(path + "/test-auto-intents", headers=headers,
                       json={"commandId": str(uuid4()), "text": "Não enviar"}).status_code == 403
    new_chat = deliver(client, channel, event(str(uuid4()), user="lead-1",
                                              chat="chat-2", text="Nova conversa"))
    assert new_chat.status_code == 200
    new_history = client.get(f"/v1/orgs/{org}/conversations/{new_chat.json()['conversationId']}",
                             headers=headers).json()
    assert new_history["contactBlocked"] is True
    assert new_history["optOut"]["sourceEventId"] == stopped.json()["sourceEventId"]
    assert new_history["mode"] == "awaiting_human"
    assert new_history["handoffReason"] == "opt_out"
    queue = client.get(f"/v1/orgs/{org}/human-queue", headers=headers).json()
    assert any(item["conversationId"] == new_chat.json()["conversationId"]
               and item["reason"] == "opt_out" for item in queue)


def test_duplicate_event_with_different_body_cannot_create_opt_out(client, identity):
    _, org, headers, channel, conversation, _ = pending_automatic_reply(client, identity)
    first = event(str(uuid4()), user="lead-1", text="Olá")
    assert deliver(client, channel, first).status_code == 200
    spoofed_retry = {**first, "content": {"kind": "text", "text": "Pare de me enviar mensagens"}}
    assert deliver(client, channel, spoofed_retry).json()["duplicate"] is True
    history = client.get(f"/v1/orgs/{org}/conversations/{conversation}", headers=headers).json()
    assert history["optOut"] is None


def test_opt_out_is_scoped_to_organization_channel_and_contact(client, identity):
    _, org, headers, telegram, _, _ = pending_automatic_reply(client, identity)
    stop = deliver(client, telegram, event(str(uuid4()), user="lead-1",
                                           text="Não quero receber mais mensagens"))
    assert stop.status_code == 200
    another_contact = deliver(client, telegram, event(str(uuid4()), user="lead-2", chat="other"))
    whatsapp = create_channel(client, org, headers, "whatsapp_evolution")
    another_channel = deliver(client, whatsapp, event(str(uuid4()), user="lead-1"))
    for result in (another_contact, another_channel):
        history = client.get(f"/v1/orgs/{org}/conversations/{result.json()['conversationId']}",
                             headers=headers).json()
        assert history["optOut"] is None
        assert history["contactBlocked"] is False


def test_opt_out_during_external_attempt_reports_pending_without_false_cancellation(client, identity):
    _, org, headers, channel, conversation, intent = pending_automatic_reply(client, identity)
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
        stopped = deliver(client, channel, event(str(uuid4()), user="lead-1",
                                                 text="Não quero mais mensagens automáticas"))
        assert stopped.status_code == 202
        assert stopped.json()["control_applied"] is True
        assert stopped.json()["completion"] == "pending_external_attempt"
        assert sending.result().json()["status"] == "accepted"
    history = client.get(path, headers=headers).json()
    assert history["optOut"]["reason"] == "explicit_stop_request"
    assert history["outboundIntents"][0]["status"] == "accepted"
    assert client.post(path + "/test-auto-intents", headers=headers,
                       json={"commandId": str(uuid4()), "text": "Não enviar"}).status_code == 403
