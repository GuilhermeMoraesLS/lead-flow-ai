"""Managed Telegram bot onboarding and authenticated inbound staging."""

import hmac
import os
import secrets
from binascii import Error as BinasciiError
from hashlib import sha256
from typing import Annotated, Any
from urllib.parse import quote
from uuid import UUID

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import text

from leadflow.auth import actor_id
from leadflow.database import transaction

router = APIRouter()
Actor = Annotated[UUID, Depends(actor_id)]
INGRESS = UUID(int=0)


def setting(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise HTTPException(503, "Configuração Telegram indisponível.")
    return value


def keyring() -> tuple[dict[int, Fernet], int]:
    raw = os.environ.get("TELEGRAM_FERNET_KEYS", "")
    try:
        entries = (raw.split(",") if raw else
                   ["1:" + setting("TELEGRAM_FERNET_KEY")])
        keys = {int(version): Fernet(value.encode()) for entry in entries
                for version, separator, value in [entry.partition(":")] if separator}
        active = int(os.environ.get("TELEGRAM_FERNET_ACTIVE_VERSION", "1"))
        if not keys or active not in keys or any(version < 1 for version in keys):
            raise ValueError
        return keys, active
    except (ValueError, TypeError, BinasciiError):
        raise HTTPException(503, "Chave Telegram indisponível.") from None


def encrypt_secret(value: str) -> str:
    keys, active = keyring()
    return f"v{active}:" + keys[active].encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    keys, _ = keyring()
    version_text, separator, ciphertext = value.partition(":")
    try:
        version = int(version_text[1:]) if separator and version_text.startswith("v") else 1
        return keys[version].decrypt((ciphertext if separator else value).encode()).decode()
    except (KeyError, ValueError, InvalidToken, UnicodeDecodeError):
        raise HTTPException(503, "Segredo Telegram indisponível.") from None


def digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def bot_api(token: str, method: str, payload: dict[str, Any]) -> Any:
    try:
        response = httpx.post(f"https://api.telegram.org/bot{token}/{method}",
                              json=payload, timeout=10)
        response.raise_for_status()
        body = response.json()
        if body.get("ok") is not True:
            raise ValueError("Telegram rejected request")
        return body["result"]
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise HTTPException(503, "Telegram indisponível. Tente retomar.") from None


def manager_link(nonce: str) -> str:
    username = setting("TELEGRAM_MANAGER_USERNAME").lstrip("@")
    return f"https://t.me/{quote(username)}?start={quote(nonce)}"


def creation_link(org: UUID) -> str:
    username = setting("TELEGRAM_MANAGER_USERNAME").lstrip("@")
    suggestion = f"LeadFlow_{str(org).replace('-', '')[:8]}_bot"
    return f"https://t.me/newbot/{quote(username)}/{suggestion}?name=LeadFlow"


def manager_only(actor: UUID, org: UUID) -> None:
    with transaction(actor, org) as conn:
        row = conn.execute(text("""SELECT m.role FROM app.org_members m
            WHERE m.organization_id = :org AND m.user_id = :actor
              AND m.status = 'active'"""),
            {"org": org, "actor": actor}).first()
        if row is None:
            raise HTTPException(404, "Operação não encontrada.")
        if row.role != "gestor":
            raise HTTPException(403, "Acesso de gestor necessário.")


def public_status(org: UUID, row: Any) -> dict[str, Any]:
    result = {"status": row["status"], "botUsername": row["bot_username"],
              "failureCode": row["failure_code"],
              "connected": row["status"] == "connected"}
    if row["status"] == "awaiting_owner":
        result["link"] = manager_link(decrypt_secret(row["request_ciphertext"]))
    elif row["status"] == "awaiting_bot":
        result["link"] = creation_link(org)
    return result


@router.get("/v1/orgs/{org}/telegram/d0")
def telegram_d0_status(org: UUID, actor: Actor) -> dict[str, bool]:
    manager_only(actor, org)
    with transaction(actor, org) as conn:
        enabled = conn.execute(text("SELECT d0_enabled FROM app.organizations WHERE id = :org"),
                               {"org": org}).scalar_one()
    return {"enabled": bool(enabled)}


@router.post("/v1/orgs/{org}/telegram/d0")
def activate_telegram_d0(org: UUID, actor: Actor) -> dict[str, bool]:
    manager_only(actor, org)
    if os.environ.get("APP_ENV") != "local" or not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(503, "Demonstração D0 indisponível.")
    with transaction(actor, org) as conn:
        try:
            conn.execute(text("SELECT private.enable_telegram_d0(:org)"), {"org": org})
            conn.execute(text("""INSERT INTO app.channels(organization_id, kind, token_hash)
                VALUES (:org, 'telegram', :hash)
                ON CONFLICT (organization_id, kind) DO NOTHING"""),
                {"org": org, "hash": digest(secrets.token_urlsafe(32))})
        except Exception as exc:
            if getattr(getattr(exc, "orig", None), "sqlstate", None) == "23514":
                raise HTTPException(409, "Conclua configuração, catálogo e vínculo antes de ativar D0.") from None
            raise
    return {"enabled": True}


@router.get("/v1/orgs/{org}/telegram/d0/conversations")
def telegram_d0_conversations(org: UUID, actor: Actor) -> list[dict[str, Any]]:
    manager_only(actor, org)
    with transaction(actor, org) as conn:
        rows = conn.execute(text("""SELECT b.id, b.conversation_id, b.status,
            b.error_code, b.created_at, i.status AS delivery_status,
            r.model, r.prompt_version, r.commercial_revision, r.estimated_cost_usd
            FROM app.telegram_message_batches b
            LEFT JOIN app.outbound_intents i ON i.organization_id = b.organization_id
              AND i.id = b.intent_id
            LEFT JOIN app.catalog_agent_runs r ON r.organization_id = b.organization_id
              AND r.id = b.run_id
            WHERE b.organization_id = :org
            ORDER BY b.created_at DESC, b.id DESC LIMIT 20"""), {"org": org}).mappings().all()
    return [{"batchId": str(row["id"]),
             "conversationId": str(row["conversation_id"]) if row["conversation_id"] else None,
             "status": row["status"], "deliveryStatus": row["delivery_status"],
             "errorCode": row["error_code"], "createdAt": row["created_at"].isoformat(),
             "model": row["model"], "promptVersion": row["prompt_version"],
             "commercialRevision": row["commercial_revision"],
             "estimatedCostUsd": str(row["estimated_cost_usd"])
             if row["estimated_cost_usd"] is not None else None}
            for row in rows]


@router.get("/v1/orgs/{org}/telegram")
def telegram_status(org: UUID, actor: Actor) -> dict[str, Any]:
    manager_only(actor, org)
    with transaction(actor, org) as conn:
        row = conn.execute(text("""SELECT status, bot_username, failure_code,
            request_ciphertext
            FROM app.telegram_provisioning WHERE organization_id = :org"""),
            {"org": org}).mappings().first()
    return public_status(org, row) if row else {"status": "not_started", "botUsername": None,
                                           "failureCode": None, "connected": False}


@router.post("/v1/orgs/{org}/telegram", status_code=202)
def start_telegram(org: UUID, actor: Actor) -> dict[str, Any]:
    manager_only(actor, org)
    with transaction(actor, org) as conn:
        row = conn.execute(text("""SELECT request_ciphertext, status, bot_username,
            failure_code FROM app.telegram_provisioning
            WHERE organization_id = :org FOR UPDATE"""),
            {"org": org}).mappings().first()
        if row is None:
            nonce = secrets.token_urlsafe(24)
            conn.execute(text("""INSERT INTO app.telegram_provisioning
                (organization_id, request_hash, request_ciphertext)
                VALUES (:org, :hash, :ciphertext)"""),
                {"org": org, "hash": digest(nonce),
                 "ciphertext": encrypt_secret(nonce)})
            status = "awaiting_owner"
        else:
            nonce = decrypt_secret(row["request_ciphertext"])
            status = row["status"]
    return {"status": status, "connected": status == "connected",
            "link": manager_link(nonce) if status == "awaiting_owner" else
                    creation_link(org) if status == "awaiting_bot" else None}


def configure_bot(org: UUID, bot_id: int, token: str) -> None:
    """Verify identity and webhook state before presenting a connection."""
    base = setting("TELEGRAM_PUBLIC_URL").rstrip("/")
    if not base.startswith("https://"):
        raise HTTPException(503, "Webhook HTTPS público indisponível.")
    identity = bot_api(token, "getMe", {})
    if not isinstance(identity, dict) or identity.get("id") != bot_id or not identity.get("is_bot"):
        raise HTTPException(503, "Identidade do bot não confirmada.")
    secret = secrets.token_urlsafe(32)
    url = f"{base}/v1/telegram/bots/{bot_id}/updates"
    with transaction(INGRESS) as conn:
        conn.execute(text("""UPDATE app.telegram_provisioning SET bot_id = :bot,
            bot_username = :username, token_ciphertext = :token,
            webhook_secret_ciphertext = :secret, webhook_secret_hash = :secret_hash,
            status = 'configuring', failure_code = NULL, updated_at = now()
            WHERE organization_id = :org AND bot_id = :bot"""),
            {"org": org, "bot": bot_id, "username": identity.get("username"),
             "token": encrypt_secret(token),
             "secret": encrypt_secret(secret),
             "secret_hash": digest(secret)})
    bot_api(token, "setWebhook", {"url": url, "secret_token": secret,
                                  "allowed_updates": ["message"]})
    info = bot_api(token, "getWebhookInfo", {})
    if not isinstance(info, dict) or info.get("url") != url:
        raise HTTPException(503, "Webhook não confirmado.")
    with transaction(INGRESS) as conn:
        conn.execute(text("""UPDATE app.telegram_provisioning SET status = 'connected',
            failure_code = NULL, updated_at = now()
            WHERE organization_id = :org AND bot_id = :bot AND status = 'configuring'"""),
            {"org": org, "bot": bot_id})


@router.post("/v1/orgs/{org}/telegram/resume", status_code=202)
def resume_telegram(org: UUID, actor: Actor) -> dict[str, Any]:
    manager_only(actor, org)
    with transaction(actor, org) as conn:
        row = conn.execute(text("""SELECT bot_id, token_ciphertext, status
            FROM app.telegram_provisioning WHERE organization_id = :org"""),
            {"org": org}).mappings().first()
    if row is None:
        raise HTTPException(404, "Solicitação não encontrada.")
    if row["status"] == "connected":
        return telegram_status(org, actor)
    if row["bot_id"] is None:
        with transaction(actor, org) as conn:
            conn.execute(text("""UPDATE app.telegram_provisioning SET
                status = CASE WHEN telegram_owner_id IS NULL THEN 'awaiting_owner'
                              ELSE 'awaiting_bot' END,
                failure_code = NULL, updated_at = now()
                WHERE organization_id = :org AND status = 'failed'"""), {"org": org})
        return start_telegram(org, actor)
    try:
        token = (decrypt_secret(row["token_ciphertext"])
                 if row["token_ciphertext"] else
                 bot_api(setting("TELEGRAM_MANAGER_TOKEN"), "getManagedBotToken",
                         {"user_id": row["bot_id"]}))
        if not isinstance(token, str):
            raise HTTPException(503, "Token Telegram indisponível.")
        configure_bot(org, row["bot_id"], token)
    except HTTPException:
        with transaction(INGRESS) as conn:
            conn.execute(text("""UPDATE app.telegram_provisioning SET status = 'failed',
                failure_code = 'webhook_unavailable', updated_at = now()
                WHERE organization_id = :org"""), {"org": org})
    return telegram_status(org, actor)


def valid_manager_header(value: str) -> bool:
    expected = os.environ.get("TELEGRAM_MANAGER_WEBHOOK_SECRET", "")
    return bool(expected and hmac.compare_digest(value, expected))


def nested_id(value: Any, key: str) -> int | None:
    nested = value.get(key) if isinstance(value, dict) else None
    identifier = nested.get("id") if isinstance(nested, dict) else None
    return identifier if isinstance(identifier, int) else None


@router.post("/v1/telegram/manager/updates")
async def manager_update(request: Request,
                         secret: Annotated[str, Header(alias="X-Telegram-Bot-Api-Secret-Token")] = ""
                         ) -> dict[str, bool]:
    if not valid_manager_header(secret):
        raise HTTPException(401, "Origem Telegram inválida.")
    raw = await request.body()
    if len(raw) > 16384:
        raise HTTPException(413, "Atualização excede o limite.")
    try:
        update = await request.json()
        if not isinstance(update, dict) or not isinstance(update.get("update_id"), int):
            raise TypeError
    except (ValueError, TypeError):
        raise HTTPException(422, "Atualização inválida.") from None
    message = update.get("message")
    if isinstance(message, dict) and isinstance(message.get("text"), str):
        parts = message["text"].split(maxsplit=1)
        owner = nested_id(message, "from")
        chat = message.get("chat", {})
        if (len(parts) == 2 and parts[0] == "/start" and isinstance(owner, int)
                and isinstance(chat, dict) and chat.get("type") == "private"):
            with transaction(INGRESS) as conn:
                conn.execute(text("SELECT pg_advisory_xact_lock(:owner)"), {"owner": owner})
                target = conn.execute(text("""SELECT organization_id FROM app.telegram_provisioning
                    WHERE request_hash = :hash AND status IN ('awaiting_owner', 'awaiting_bot')
                      AND (telegram_owner_id IS NULL OR telegram_owner_id = :owner)"""),
                    {"owner": owner, "hash": digest(parts[1])}).mappings().first()
                pending = conn.execute(text("""SELECT organization_id FROM app.telegram_provisioning
                    WHERE telegram_owner_id = :owner
                      AND status IN ('awaiting_bot', 'configuring')"""),
                    {"owner": owner}).mappings().first()
                row = None
                if target is not None and (pending is None or
                                           pending["organization_id"] == target["organization_id"]):
                    row = conn.execute(text("""UPDATE app.telegram_provisioning
                        SET telegram_owner_id = :owner, status = 'awaiting_bot', updated_at = now()
                        WHERE organization_id = :org AND status IN ('awaiting_owner', 'awaiting_bot')
                          AND (telegram_owner_id IS NULL OR telegram_owner_id = :owner)
                        RETURNING organization_id"""),
                        {"owner": owner, "org": target["organization_id"]}).mappings().first()
            if row is not None:
                bot_api(setting("TELEGRAM_MANAGER_TOKEN"), "sendMessage",
                        {"chat_id": chat["id"], "text": "Confirme a criação do seu bot: "
                         + creation_link(row["organization_id"])})
            elif target is not None and pending is not None:
                bot_api(setting("TELEGRAM_MANAGER_TOKEN"), "sendMessage",
                        {"chat_id": chat["id"], "text":
                         "Conclua a criação do bot anterior antes de iniciar outra empresa."})
    managed = update.get("managed_bot")
    if isinstance(managed, dict):
        owner = nested_id(managed, "user")
        bot = nested_id(managed, "bot")
        if isinstance(owner, int) and isinstance(bot, int):
            with transaction(INGRESS) as conn:
                attached = conn.execute(text("""SELECT organization_id, telegram_owner_id,
                    status FROM app.telegram_provisioning WHERE bot_id = :bot FOR UPDATE"""),
                    {"bot": bot}).mappings().first()
                pending = conn.execute(text("""SELECT organization_id, telegram_owner_id,
                    status FROM app.telegram_provisioning
                    WHERE telegram_owner_id = :owner AND status = 'awaiting_bot'
                    FOR UPDATE"""), {"owner": owner}).mappings().first()
                row = attached if attached is not None and attached["telegram_owner_id"] == owner else pending
                accepted = False
                if row is not None and row["status"] in ("awaiting_bot", "failed", "configuring"):
                    if attached is not None and attached["organization_id"] != row["organization_id"]:
                        conn.execute(text("""UPDATE app.telegram_provisioning
                            SET status = 'failed', failure_code = 'bot_already_connected',
                                updated_at = now() WHERE organization_id = :org
                                AND bot_id IS NULL"""),
                            {"org": row["organization_id"]})
                    else:
                        accepted = conn.execute(text("""UPDATE app.telegram_provisioning
                            SET bot_id = :bot, status = 'configuring',
                                last_managed_update_id = :update_id, updated_at = now()
                            WHERE organization_id = :org AND (bot_id IS NULL OR bot_id = :bot)
                              AND (last_managed_update_id IS NULL
                                   OR last_managed_update_id < :update_id)"""),
                            {"org": row["organization_id"], "bot": bot,
                             "update_id": update["update_id"]}).rowcount == 1
            if row is not None and accepted:
                try:
                    token = bot_api(setting("TELEGRAM_MANAGER_TOKEN"), "getManagedBotToken",
                                    {"user_id": bot})
                    if not isinstance(token, str):
                        raise HTTPException(503, "Token Telegram inválido.")
                    configure_bot(row["organization_id"], bot, token)
                except HTTPException:
                    with transaction(INGRESS) as conn:
                        conn.execute(text("""UPDATE app.telegram_provisioning
                            SET status = 'failed', failure_code = 'webhook_unavailable',
                                updated_at = now()
                            WHERE organization_id = :org AND bot_id = :bot"""),
                            {"org": row["organization_id"], "bot": bot})
    return {"ok": True}


@router.post("/v1/telegram/bots/{bot_id}/updates")
async def bot_update(bot_id: int, request: Request,
                     secret: Annotated[str, Header(alias="X-Telegram-Bot-Api-Secret-Token")] = ""
                     ) -> dict[str, bool]:
    if not secret or len(secret) > 256:
        raise HTTPException(401, "Origem Telegram inválida.")
    raw = await request.body()
    if len(raw) > 16384:
        raise HTTPException(413, "Atualização excede o limite.")
    with transaction(INGRESS) as conn:
        binding = conn.execute(text("""SELECT organization_id, webhook_secret_hash
            FROM app.telegram_provisioning WHERE bot_id = :bot AND status = 'connected'"""),
            {"bot": bot_id}).mappings().first()
    if binding is None or not hmac.compare_digest(digest(secret), binding["webhook_secret_hash"]):
        raise HTTPException(401, "Origem Telegram inválida.")
    try:
        update = await request.json()
        if not isinstance(update, dict) or not isinstance(update.get("update_id"), int):
            raise TypeError
    except (ValueError, TypeError):
        raise HTTPException(422, "Atualização inválida.") from None
    message = update.get("message")
    if not isinstance(message, dict):
        return {"ok": True}
    chat = message.get("chat")
    sender = message.get("from")
    body = message.get("text")
    if (not isinstance(chat, dict) or chat.get("type") != "private"
            or not isinstance(chat.get("id"), int) or not isinstance(sender, dict)
            or sender.get("is_bot") or not isinstance(message.get("message_id"), int)
            or not isinstance(body, str) or not 1 <= len(body) <= 8000):
        return {"ok": True}
    with transaction(INGRESS) as conn:
        conn.execute(text("""SELECT pg_advisory_xact_lock(
            hashtext(CAST(:bot AS text)), hashtext(CAST(:chat AS text)))"""),
            {"bot": bot_id, "chat": chat["id"]})
        conn.execute(text("""INSERT INTO app.telegram_message_buffer
            (organization_id, bot_id, chat_id, telegram_message_id, body)
            VALUES (:org, :bot, :chat, :message, :body)
            ON CONFLICT (bot_id, chat_id, telegram_message_id) DO NOTHING"""),
            {"org": binding["organization_id"], "bot": bot_id,
             "chat": chat["id"], "message": message["message_id"], "body": body})
    return {"ok": True}
