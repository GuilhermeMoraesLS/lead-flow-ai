"""Durable local recovery tasks. Celery messages contain IDs only."""

import os
from typing import Any
from uuid import UUID

import psycopg
from celery import Celery  # type: ignore[import-untyped]

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
    },
)


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
