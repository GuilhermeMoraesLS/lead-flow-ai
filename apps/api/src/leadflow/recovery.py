"""Durable local recovery tasks. Celery messages contain IDs only."""

import os
from typing import Any
from uuid import UUID

import httpx
import psycopg
from celery import Celery  # type: ignore[import-untyped]
from sqlalchemy import text

from leadflow.database import transaction

celery_app = Celery("leadflow_recovery", broker=os.environ.get("CELERY_BROKER_URL"))
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_transport_options={"visibility_timeout": 300},
    task_soft_time_limit=75,
    task_time_limit=90,
    beat_schedule={
        "durable-recovery-scan": {
            "task": "leadflow.recovery.scan",
            "schedule": 10.0,
        },
        "telegram-buffer-scan": {
            "task": "leadflow.telegram.seal_due",
            "schedule": 1.0,
        },
        "telegram-d0-scan": {
            "task": "leadflow.telegram.process_due",
            "schedule": 2.0,
        },
    },
)


@celery_app.task(name="leadflow.telegram.seal_due")  # type: ignore[untyped-decorator]
def seal_telegram_due() -> int:
    """Seal each quiet chat as one durable AI input after five seconds."""
    sealed = 0
    with worker_connection() as conn:
        due = conn.execute("""SELECT bot_id, chat_id FROM app.telegram_message_buffer
            WHERE batch_id IS NULL GROUP BY bot_id, chat_id
            HAVING max(received_at) <= now() - interval '5 seconds'
            ORDER BY bot_id, chat_id LIMIT 100""").fetchall()
        for bot_id, chat_id in due:
            with conn.transaction():
                conn.execute("""SELECT pg_advisory_xact_lock(
                    hashtext(%s::text), hashtext(%s::text))""", (bot_id, chat_id))
                quiet = conn.execute("""SELECT max(received_at) <= now() - interval '5 seconds'
                    FROM app.telegram_message_buffer
                    WHERE bot_id = %s AND chat_id = %s AND batch_id IS NULL""",
                    (bot_id, chat_id)).fetchone()
                if quiet is None or quiet[0] is not True:
                    continue
                rows = conn.execute("""SELECT id, organization_id, body
                    FROM app.telegram_message_buffer
                    WHERE bot_id = %s AND chat_id = %s AND batch_id IS NULL
                      AND received_at <= now() - interval '5 seconds'
                    ORDER BY telegram_message_id, id FOR UPDATE SKIP LOCKED""",
                    (bot_id, chat_id)).fetchall()
                if not rows:
                    continue
                selected: list[tuple[Any, Any, str]] = []
                length = 0
                for row in rows:
                    added = len(row[2]) + (1 if selected else 0)
                    if selected and length + added > 8000:
                        break
                    selected.append(row)
                    length += added
                body = "\n".join(row[2] for row in selected)
                batch = conn.execute("""INSERT INTO app.telegram_message_batches
                    (organization_id, bot_id, chat_id, body)
                    VALUES (%s, %s, %s, %s) RETURNING id""",
                    (selected[0][1], bot_id, chat_id, body)).fetchone()
                assert batch is not None
                conn.execute("""UPDATE app.telegram_message_buffer SET batch_id = %s
                    WHERE id = ANY(%s)""", (batch[0], [row[0] for row in selected]))
                sealed += 1
    return sealed


@celery_app.task(name="leadflow.telegram.process_due")  # type: ignore[untyped-decorator]
def process_telegram_due() -> int:
    """Claim sealed batches. A lost sender is reconciled as unknown, never replayed."""
    processed = 0
    with worker_connection() as conn:
        conn.execute("""UPDATE app.telegram_message_batches SET status = 'failed',
            error_code = 'processing_lease_expired'
            WHERE status = 'processing' AND claimed_at < now() - interval '180 seconds'""")
        rows = conn.execute("SELECT batch_id FROM private.worker_telegram_due()").fetchall()
    for (batch_id,) in rows[:2]:
        if process_telegram_batch(batch_id):
            processed += 1
    return processed


def process_telegram_batch(batch_id: UUID) -> bool:
    from leadflow.main import (
        create_test_catalog_reply,
        is_explicit_human_request,
        is_explicit_opt_out,
    )
    from leadflow.telegram import decrypt_secret

    with worker_connection() as conn:
        row = conn.execute("""UPDATE app.telegram_message_batches
            SET status = 'processing', claimed_at = now()
            WHERE id = %s AND status = 'ready'
            RETURNING organization_id, bot_id, chat_id, body""", (batch_id,)).fetchone()
        if row is None:
            return False
        org, bot_id, chat_id, body = row
        manager_row = conn.execute("SELECT private.worker_telegram_manager(%s)",
                                   (org,)).fetchone()
        assert manager_row is not None
        manager = manager_row[0]
        fragments = conn.execute("""SELECT body FROM app.telegram_message_buffer
            WHERE organization_id = %s AND batch_id = %s
            ORDER BY telegram_message_id, id""", (org, batch_id)).fetchall()
    if manager is None:
        _finish_telegram_batch(batch_id, "failed", "manager_unavailable")
        return True
    event = f"telegram-batch:{batch_id}"
    with transaction(manager, org) as conn:
        channel = conn.execute(text("""SELECT id, token_hash FROM app.channels
            WHERE organization_id = :org AND kind = 'telegram'"""), {"org": org}).mappings().first()
        if channel is None:
            _finish_telegram_batch(batch_id, "failed", "channel_unavailable")
            return True
        recorded = conn.execute(text("""SELECT conversation_id FROM
            private.receive_test_event_serialized(:channel, :hash, 'message', :event,
                :message, :chat, :user, NULL, :body, now(), NULL)"""),
            {"channel": channel["id"], "hash": channel["token_hash"],
             "event": event, "message": event, "chat": str(chat_id),
             "user": str(chat_id), "body": body}).scalar_one()
        if any(is_explicit_opt_out(part[0]) for part in fragments):
            conn.execute(text("SELECT private.apply_test_opt_out(:channel, :hash, :event)"),
                         {"channel": channel["id"], "hash": channel["token_hash"],
                          "event": event})
        elif any(is_explicit_human_request(part[0]) for part in fragments):
            conn.execute(text("SELECT private.request_human_from_test_event(:channel, :hash, :event)"),
                         {"channel": channel["id"], "hash": channel["token_hash"],
                          "event": event})
        enabled = conn.execute(text("""SELECT d0_enabled AND NOT automation_paused
            FROM app.organizations WHERE id = :org"""), {"org": org}).scalar_one()
        eligible = conn.execute(text("""SELECT mode = 'automatic' AND NOT contact_blocked
            FROM app.conversations WHERE organization_id = :org AND id = :conversation"""),
            {"org": org, "conversation": recorded}).scalar_one()
        bot = conn.execute(text("""SELECT token_ciphertext FROM app.telegram_provisioning
            WHERE organization_id = :org AND bot_id = :bot AND status = 'connected'"""),
            {"org": org, "bot": bot_id}).mappings().first()
    with worker_connection() as conn:
        conn.execute("""UPDATE app.telegram_message_batches SET conversation_id = %s
            WHERE id = %s AND status = 'processing'""", (recorded, batch_id))
    if not enabled or not eligible or bot is None:
        _finish_telegram_batch(batch_id, "processed", None)
        return True
    reply = create_test_catalog_reply(org, recorded, manager)
    if isinstance(reply, dict) and reply.get("runId"):
        with worker_connection() as conn:
            conn.execute("""UPDATE app.telegram_message_batches SET run_id = %s
                WHERE id = %s AND status = 'processing'""", (UUID(reply["runId"]), batch_id))
    if not isinstance(reply, dict) or reply.get("status") != "pending":
        _finish_telegram_batch(batch_id, "processed", None)
        return True
    intent = UUID(reply["intentId"])
    with worker_connection() as conn:
        conn.execute("""UPDATE app.telegram_message_batches SET intent_id = %s
            WHERE id = %s AND status = 'processing'""", (intent, batch_id))
    with transaction(manager, org) as conn:
        started, _ = conn.execute(text("""SELECT started, current_status
            FROM private.authorize_test_dispatch(:org, :intent)"""),
            {"org": org, "intent": intent}).one()
        answer = conn.execute(text("""SELECT text FROM app.outbound_intents
            WHERE organization_id = :org AND id = :intent"""),
            {"org": org, "intent": intent}).scalar_one()
    if not started:
        _finish_telegram_batch(batch_id, "processed", None)
        return True
    outcome, external_id = _send_telegram(decrypt_secret(bot["token_ciphertext"]),
                                           chat_id, answer)
    with transaction(manager, org) as conn:
        conn.execute(text("""SELECT private.finish_telegram_dispatch(
            :org, :intent, :outcome, :external)"""),
            {"org": org, "intent": intent, "outcome": outcome, "external": external_id})
    _finish_telegram_batch(batch_id, "processed", None)
    return True


def _finish_telegram_batch(batch_id: UUID, status: str, error: str | None) -> None:
    with worker_connection() as conn:
        conn.execute("""UPDATE app.telegram_message_batches
            SET status = %s, error_code = %s WHERE id = %s AND status = 'processing'""",
            (status, error, batch_id))


def _send_telegram(token: str, chat_id: int, answer: str) -> tuple[str, str | None]:
    try:
        response = httpx.post(f"https://api.telegram.org/bot{token}/sendMessage",
                              json={"chat_id": chat_id, "text": answer}, timeout=10)
        data = response.json()
        if response.is_success and data.get("ok") is True:
            return "accepted", str(data["result"]["message_id"])
        if response.status_code in {400, 403, 404} and data.get("ok") is False:
            return "rejected", None
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        pass
    return "unknown", None


def worker_connection() -> psycopg.Connection[Any]:
    return psycopg.connect(os.environ["WORKER_DATABASE_URL"])


@celery_app.task(name="leadflow.recovery.scan")  # type: ignore[untyped-decorator]
def scan() -> dict[str, int]:
    """Recreate broker work from durable rows after any broker loss."""
    with worker_connection() as conn:
        organizations = [str(row[0]) for row in conn.execute(
            "SELECT organization_id FROM private.worker_due_organizations()"
        )]
        outbox = [(str(row[0]), str(row[1]), str(row[2])) for row in conn.execute(
            "SELECT organization_id, outbox_id, claim_token FROM private.worker_claim_outbox()"
        )]
    for organization_id in organizations:
        recover_organization.delay(organization_id)
    for organization_id, outbox_id, claim_token in outbox:
        consume_outbox.delay(organization_id, outbox_id, claim_token)
    return {"organizations": len(organizations), "outbox": len(outbox)}


@celery_app.task(name="leadflow.recovery.organization")  # type: ignore[untyped-decorator]
def recover_organization(organization_id: str) -> int:
    with worker_connection() as conn:
        row = conn.execute(
            "SELECT private.worker_recover_organization(%s)", (UUID(organization_id),)
        ).fetchone()
        assert row is not None
        return int(row[0])


@celery_app.task(name="leadflow.recovery.outbox")  # type: ignore[untyped-decorator]
def consume_outbox(organization_id: str, outbox_id: str, claim_token: str) -> bool:
    ids = (UUID(organization_id), UUID(outbox_id), UUID(claim_token))
    try:
        with worker_connection() as conn:
            row = conn.execute(
                "SELECT private.worker_consume_outbox(%s, %s, %s)", ids,
            ).fetchone()
            assert row is not None
            consumed = bool(row[0])
        if (os.environ.get("APP_ENV") == "local" and
                os.environ.get("LOCAL_RECOVERY_CRASH_AFTER_COMMIT") == outbox_id):
            os._exit(17)
        return consumed
    except (psycopg.errors.SerializationFailure, psycopg.errors.DeadlockDetected) as exc:
        reason = ("serialization_failure" if isinstance(exc, psycopg.errors.SerializationFailure)
                  else "deadlock_detected")
        with worker_connection() as conn:
            conn.execute("SELECT private.worker_retry_outbox(%s, %s, %s, %s, 0)",
                         (*ids, reason))
        return False
