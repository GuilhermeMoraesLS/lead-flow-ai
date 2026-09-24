import os
import subprocess
import sys
from time import monotonic, sleep
from uuid import uuid4

import redis
from leadflow.recovery import celery_app, consume_outbox, scan, worker_connection

from scripts.local import admin_connection
from tests.integration.test_human_reply import pending_reply
from tests.integration.test_inbound_history import channel, deliver, event, organization


def claim_new_outbox(org, outbox):
    with admin_connection() as conn:
        conn.execute("UPDATE app.outbox_events SET available_at = '2000-01-01' "
                     "WHERE organization_id=%s AND id=%s", (org, outbox))
    with worker_connection() as conn:
        claims = conn.execute("SELECT * FROM private.worker_claim_outbox()").fetchall()
    return next(str(row[2]) for row in claims if str(row[1]) == outbox)


def test_broker_rebuilds_durable_outbox_once(client, identity):
    org, headers = organization(client, identity, "Alfa worker recovery")
    binding = channel(client, org, headers)
    received = deliver(client, binding, event(str(uuid4())))
    assert received.status_code == 200
    outbox = received.json()["outboxId"]
    lost_token = claim_new_outbox(org, outbox)
    lost_queue = f"sl09-loss-{uuid4().hex}"
    consume_outbox.apply_async(args=(org, outbox, lost_token), queue=lost_queue)
    assert redis.Redis.from_url(os.environ["CELERY_BROKER_URL"]).delete(lost_queue) == 1
    with admin_connection() as conn:
        conn.execute("UPDATE app.outbox_events SET recovery_claimed_until = now() - interval '1 second' "
                     "WHERE organization_id=%s AND id=%s", (org, outbox))

    worker = subprocess.Popen(
        [sys.executable, "-m", "celery", "-A", "leadflow.recovery:celery_app",
         "worker", "--pool=solo", "--loglevel=warning", "--without-gossip",
         "--without-mingle", "--without-heartbeat"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        deadline = monotonic() + 20
        while monotonic() < deadline:
            if celery_app.control.ping(timeout=1):
                break
            sleep(0.2)
        else:
            raise AssertionError("Worker não iniciou")

        while monotonic() < deadline:
            assert worker.poll() is None
            scan.delay()
            with admin_connection() as conn:
                consumed = conn.execute(
                    "SELECT EXISTS (SELECT 1 FROM app.outbox_effects "
                    "WHERE organization_id=%s AND outbox_id=%s)", (org, outbox),
                ).fetchone()[0]
            if consumed:
                break
            sleep(0.5)
        else:
            raise AssertionError("Outbox durável não foi consumida pelo worker")
    finally:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(worker.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           check=False)
        else:
            worker.terminate()
        worker.wait(timeout=10)

    published = client.post(f"/v1/orgs/{org}/test-outbox/{outbox}/publish", headers=headers)
    assert published.status_code == 200
    assert published.json() == {"newEffect": False, "effectCount": 1}
    again = client.post(f"/v1/orgs/{org}/test-outbox/{outbox}/publish", headers=headers)
    assert again.json() == {"newEffect": False, "effectCount": 1}


def test_worker_crash_after_commit_before_ack_keeps_one_effect(client, identity):
    org, headers = organization(client, identity, "Alfa crash before ack")
    binding = channel(client, org, headers)
    outbox = deliver(client, binding, event(str(uuid4()))).json()["outboxId"]
    token = claim_new_outbox(org, outbox)
    worker_env = os.environ.copy()
    worker_env["LOCAL_RECOVERY_CRASH_AFTER_COMMIT"] = outbox
    worker = subprocess.Popen(
        [sys.executable, "-m", "celery", "-A", "leadflow.recovery:celery_app",
         "worker", "--pool=solo", "--loglevel=warning", "--without-gossip",
         "--without-mingle", "--without-heartbeat"],
        env=worker_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        deadline = monotonic() + 20
        while monotonic() < deadline:
            if celery_app.control.ping(timeout=1):
                break
            sleep(0.2)
        else:
            raise AssertionError("Worker não iniciou")
        consume_outbox.delay(org, outbox, token)
        while monotonic() < deadline:
            with admin_connection() as conn:
                effect_count = conn.execute(
                    "SELECT count(*) FROM app.outbox_effects "
                    "WHERE organization_id=%s AND outbox_id=%s", (org, outbox),
                ).fetchone()[0]
            if effect_count == 1 and worker.poll() is not None:
                break
            sleep(0.2)
        else:
            raise AssertionError("Crash após commit e antes do ack não ocorreu")
    finally:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(worker.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           check=False)
        elif worker.poll() is None:
            worker.terminate()
        worker.wait(timeout=10)
    assert consume_outbox(org, outbox, token) is False
    assert client.post(f"/v1/orgs/{org}/test-outbox/{outbox}/publish",
                       headers=headers).json() == {"newEffect": False, "effectCount": 1}


def test_expired_outbox_executor_cannot_commit(client, identity):
    org, headers = organization(client, identity, "Alfa outbox fencing")
    binding = channel(client, org, headers)
    outbox = deliver(client, binding, event(str(uuid4()))).json()["outboxId"]
    old_token = claim_new_outbox(org, outbox)
    with admin_connection() as conn:
        conn.execute("UPDATE app.outbox_events SET recovery_claimed_until = now() - interval '1 second' "
                     "WHERE organization_id=%s AND id=%s", (org, outbox))
    with worker_connection() as conn:
        claims = conn.execute("SELECT * FROM private.worker_claim_outbox()").fetchall()
        new_token = next(str(row[2]) for row in claims if str(row[1]) == outbox)
        old = conn.execute("SELECT private.worker_consume_outbox(%s,%s,%s)",
                           (org, outbox, old_token)).fetchone()[0]
        new = conn.execute("SELECT private.worker_consume_outbox(%s,%s,%s)",
                           (org, outbox, new_token)).fetchone()[0]
    assert old is False
    assert new is True
    assert client.post(f"/v1/orgs/{org}/test-outbox/{outbox}/publish",
                       headers=headers).json() == {"newEffect": False, "effectCount": 1}


def test_safe_retries_end_in_visible_incident(client, identity):
    org, headers = organization(client, identity, "Alfa bounded retries")
    binding = channel(client, org, headers)
    outbox = deliver(client, binding, event(str(uuid4()))).json()["outboxId"]
    for attempt in range(1, 6):
        token = claim_new_outbox(org, outbox)
        with worker_connection() as conn:
            state = conn.execute("SELECT private.worker_retry_outbox(%s,%s,%s,%s,%s)",
                                 (org, outbox, token, "rate_limited", 1)).fetchone()[0]
        assert state == ("exhausted" if attempt == 5 else "scheduled")
        if attempt < 5:
            with admin_connection() as conn:
                conn.execute("UPDATE app.outbox_events SET recovery_claimed_until = "
                             "now() - interval '1 second' WHERE organization_id=%s AND id=%s",
                             (org, outbox))
    incidents = client.get(f"/v1/orgs/{org}/recovery/outbox-incidents", headers=headers)
    assert incidents.status_code == 200
    incident = next(item for item in incidents.json() if item["outboxId"] == outbox)
    assert incident["attempts"] == 5
    assert incident["ownerMemberId"]
    assert incident["reason"] == "rate_limited"
    assert incident["nextAction"]
    with worker_connection() as conn:
        assert outbox not in {str(row[1]) for row in conn.execute(
            "SELECT * FROM private.worker_claim_outbox()").fetchall()}
    other_outbox = deliver(client, binding, event(str(uuid4()), user="contact-2",
                                                   chat="chat-2")).json()["outboxId"]
    other_token = claim_new_outbox(org, other_outbox)
    assert consume_outbox(org, other_outbox, other_token) is True
    assert client.post(f"/v1/orgs/{org}/test-outbox/{other_outbox}/publish",
                       headers=headers).json() == {"newEffect": False, "effectCount": 1}
    other_org, other_headers = organization(client, identity, "Beta bounded retries")
    assert client.get(f"/v1/orgs/{other_org}/recovery/outbox-incidents",
                      headers=other_headers).json() == []


def test_retry_after_cannot_exceed_total_deadline(client, identity):
    org, headers = organization(client, identity, "Alfa retry deadline")
    binding = channel(client, org, headers)
    outbox = deliver(client, binding, event(str(uuid4()))).json()["outboxId"]
    token = claim_new_outbox(org, outbox)
    with worker_connection() as conn:
        assert conn.execute("SELECT private.worker_retry_outbox(%s,%s,%s,%s,%s)",
                            (org, outbox, token, "rate_limited", 300)).fetchone()[0] == "exhausted"
    incident = next(item for item in client.get(
        f"/v1/orgs/{org}/recovery/outbox-incidents", headers=headers,
    ).json() if item["outboxId"] == outbox)
    assert incident["attempts"] == 1


def test_broker_recovers_abandoned_dispatch_as_unknown(client, identity):
    _, org, headers, channel_binding, conversation, intent = pending_reply(client, identity)
    crashed = client.post(f"/v1/orgs/{org}/test-dispatch/{intent}", headers={
        **headers, "X-Test-Crash-After-Start": "true",
    })
    assert crashed.status_code == 503
    with admin_connection() as conn:
        conn.execute("UPDATE app.delivery_attempts SET started_at = "
                     "now() - interval '121 seconds' WHERE organization_id=%s AND intent_id=%s",
                     (org, intent))

    worker = subprocess.Popen(
        [sys.executable, "-m", "celery", "-A", "leadflow.recovery:celery_app",
         "worker", "--pool=solo", "--loglevel=warning", "--without-gossip",
         "--without-mingle", "--without-heartbeat"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        deadline = monotonic() + 20
        while monotonic() < deadline:
            if celery_app.control.ping(timeout=1):
                break
            sleep(0.2)
        else:
            raise AssertionError("Worker não iniciou")
        while monotonic() < deadline:
            scan.delay()
            history = client.get(f"/v1/orgs/{org}/conversations/{conversation}",
                                 headers=headers).json()["outboundIntents"][0]
            if history["status"] == "unknown":
                break
            sleep(0.5)
        else:
            raise AssertionError("Watchdog não recuperou dispatch abandonado")
    finally:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(worker.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           check=False)
        else:
            worker.terminate()
        worker.wait(timeout=10)
    assert client.post(f"/v1/orgs/{org}/test-dispatch/{intent}",
                       headers=headers).json()["status"] == "unknown"
    assert client.get(f"/v1/orgs/{org}/test-channels/{channel_binding['id']}/sent",
                      headers=headers).json() == []
