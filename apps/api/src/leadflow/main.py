import os
import re
import secrets
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from leadflow.auth import actor_id
from leadflow.catalog_agent import MAX_COST_USD, MODEL, PROMPT_VERSION, Selection, select_product
from leadflow.database import transaction
from leadflow.telegram import router as telegram_router

app = FastAPI(title="LeadFlow API", version="1.0.0")
app.include_router(telegram_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["*"],
)
Actor = Annotated[UUID, Depends(actor_id)]


class OrganizationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)


class AgentView(BaseModel):
    id: UUID
    active: bool


class OrganizationView(BaseModel):
    id: UUID
    name: str
    role: str
    automation_enabled: bool
    automation_paused: bool
    simulation_enabled: bool
    automation_epoch: int
    version: int
    agent: AgentView


class MembershipView(BaseModel):
    id: UUID
    name: str
    role: str


class AgentConfigurationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: int = Field(ge=1)
    name: str = Field(max_length=120)
    identity: str = Field(max_length=500)
    instructions: str = Field(max_length=10000)


class AgentConfigurationView(BaseModel):
    name: str
    identity: str
    instructions: str
    version: int
    active: bool


class ProductInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)
    price: str | None = Field(default=None, pattern=r"^(?:0|[1-9][0-9]{0,15})(?:\.[0-9]{1,4})?$")
    available: bool


class ProductUpdate(ProductInput):
    version: int = Field(ge=1)


class ProductVersionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)


class ProductView(BaseModel):
    id: UUID
    name: str
    price: str | None
    available: bool
    status: str
    version: int
    commercialRevision: int


class SellerInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: str = Field(pattern=r"^\+[1-9][0-9]{1,14}$")
    available: bool = False


class SellerView(BaseModel):
    id: UUID
    name: str
    email: str | None
    phone: str | None
    available: bool
    active: bool
    access: str


class SellerPasswordInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(min_length=8)
    new_password: str = Field(min_length=12)


class SellerAvailabilityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    active: bool
    available: bool


class TestChannelInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["telegram", "whatsapp_evolution"]


class TextContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["text"]
    text: str = Field(min_length=1, max_length=8000)


class TestInboundEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    schema_version: Literal[1] = Field(alias="schemaVersion")
    event_type: Literal["message", "connection", "echo"] = Field(alias="eventType")
    external_event_id: str = Field(alias="externalEventId", min_length=1, max_length=256)
    external_message_id: str = Field(alias="externalMessageId", min_length=1, max_length=256)
    external_chat_id: str = Field(alias="externalChatId", min_length=1, max_length=256)
    external_user_id: str = Field(alias="externalUserId", min_length=1, max_length=256)
    occurred_at: datetime = Field(alias="occurredAt")
    provider_sequence: str | None = Field(alias="providerSequence", max_length=256)
    contact_name: str | None = Field(default=None, alias="contactName", max_length=120)
    content: TextContent


class ConversationVersionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)


class ConversationAssignInput(ConversationVersionInput):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    seller_id: UUID = Field(alias="sellerId")
    reason: str = Field(min_length=1, max_length=500)


class HumanReplyInput(ConversationVersionInput):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    command_id: UUID = Field(alias="commandId")
    text: str = Field(min_length=1, max_length=4096)


class TestAutomaticInput(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    command_id: UUID = Field(alias="commandId")
    text: str = Field(min_length=1, max_length=4096)


class TestRecoveryInput(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    advance_seconds: int = Field(default=0, alias="advanceSeconds", ge=0, le=3600)


class RecoveryResolutionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    evidence: str = Field(min_length=10, max_length=1000)


class TestContactBlockInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    blocked: bool


def is_explicit_human_request(value: str) -> bool:
    return value.casefold().strip().rstrip(".!? ") in {
        "quero falar com uma pessoa",
        "preciso falar com uma pessoa",
        "quero falar com um atendente",
        "preciso falar com um atendente",
        "quero falar com um humano",
    }


def is_greeting(value: str) -> bool:
    normalized = re.sub(r"[^\w]+", " ", value.casefold(), flags=re.UNICODE).strip()
    return normalized in {"oi", "ola", "olá", "bom dia", "boa tarde", "boa noite",
                          "e ai", "e aí", "oi tudo bem", "ola tudo bem",
                          "olá tudo bem"}


def is_explicit_opt_out(value: str) -> bool:
    return value.casefold().strip().rstrip(".!? ") in {
        "não quero mais mensagens automáticas",
        "não me envie mais mensagens automáticas",
        "pare de me enviar mensagens automáticas",
        "não quero receber mais mensagens",
        "pare de me enviar mensagens",
    }


def read_operation(conn: Connection, org: UUID) -> dict[str, Any]:
    conn.execute(text("SELECT set_config('app.organization_id', :org, true)"), {"org": str(org)})
    row = (
        conn.execute(
            text("""SELECT o.id, o.name, o.automation_enabled, o.automation_paused,
        o.simulation_enabled, o.automation_epoch, o.version,
        m.role, a.id AS agent_id, a.active FROM app.organizations o
        JOIN app.org_members m ON m.organization_id = o.id AND m.user_id = private.actor_id()
        JOIN app.agents a ON a.organization_id = o.id WHERE o.id = :org"""),
            {"org": org},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise HTTPException(404, "Operação não encontrada.")
    return {
        "id": row["id"],
        "name": row["name"],
        "role": row["role"],
        "automation_enabled": row["automation_enabled"],
        "automation_paused": row["automation_paused"],
        "simulation_enabled": row["simulation_enabled"],
        "automation_epoch": row["automation_epoch"],
        "version": row["version"],
        "agent": {"id": row["agent_id"], "active": row["active"]},
    }


@app.exception_handler(HTTPException)
def http_error(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": {401: "UNAUTHENTICATED", 404: "NOT_FOUND", 409: "VERSION_CONFLICT"}.get(
                    exc.status_code, "REQUEST_REJECTED"
                ),
                "message": str(exc.detail),
                "retryable": False,
                "request_id": str(uuid4()),
            }
        },
    )


@app.exception_handler(SQLAlchemyError)
def persistence_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "PERSISTENCE_UNAVAILABLE",
                "message": "Não foi possível salvar. Tente novamente.",
                "retryable": True,
                "request_id": str(uuid4()),
            }
        },
    )


@app.exception_handler(DBAPIError)
def database_error(request: Request, exc: DBAPIError) -> JSONResponse:
    if getattr(exc.orig, "sqlstate", None) == "22000":
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "IDEMPOTENCY_CONFLICT",
                    "message": "A chave de idempotência já foi usada com outro conteúdo.",
                    "retryable": False,
                    "request_id": str(uuid4()),
                }
            },
        )
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "PERSISTENCE_UNAVAILABLE",
                "message": "Não foi possível salvar. Tente novamente.",
                "retryable": True,
                "request_id": str(uuid4()),
            }
        },
    )


@app.post("/v1/organizations", status_code=201, response_model=OrganizationView)
def create_organization(
    body: OrganizationInput,
    actor: Actor,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> dict[str, Any]:
    request_hash = sha256(body.name.encode("utf-8")).hexdigest()
    with transaction(actor) as conn:
        row = conn.execute(
            text(
                "SELECT organization_id, created FROM private.create_organization(:name, :key, :hash)"
            ),
            {"name": body.name, "key": idempotency_key, "hash": request_hash},
        ).one()
        response = read_operation(conn, row.organization_id)
        if not row.created:
            return response
        return response


@app.get("/v1/me/organizations", response_model=list[MembershipView])
def list_own_organizations(actor: Actor) -> list[dict[str, Any]]:
    # Organization rows are only visible with the organization scope set, so read each name
    # inside its own scope after listing the actor's active memberships.
    with transaction(actor) as conn:
        memberships = conn.execute(
            text("""SELECT organization_id, role FROM app.org_members
                WHERE user_id = :actor AND status = 'active' ORDER BY created_at"""),
            {"actor": actor},
        ).mappings().all()
        result = []
        for membership in memberships:
            org = membership["organization_id"]
            conn.execute(text("SELECT set_config('app.organization_id', :org, true)"),
                         {"org": str(org)})
            name = conn.execute(text("SELECT name FROM app.organizations WHERE id = :org"),
                                {"org": org}).scalar_one_or_none()
            if name is not None:
                result.append({"id": org, "name": name, "role": membership["role"]})
        return result


@app.get("/v1/orgs/{org}", response_model=OrganizationView)
def get_organization(org: UUID, actor: Actor) -> dict[str, Any]:
    with transaction(actor, org) as conn:
        return read_operation(conn, org)


def read_agent_configuration(conn: Connection, org: UUID) -> dict[str, Any]:
    row = conn.execute(
        text("SELECT name, identity, instructions, version, active FROM app.agents WHERE organization_id = :org"),
        {"org": org},
    ).mappings().first()
    if row is None:
        raise HTTPException(404, "Configuração não encontrada.")
    return dict(row)


@app.get("/v1/orgs/{org}/agent-config", response_model=AgentConfigurationView)
def get_agent_configuration(org: UUID, actor: Actor) -> dict[str, Any]:
    with transaction(actor, org) as conn:
        return read_agent_configuration(conn, org)


@app.put("/v1/orgs/{org}/agent-config", response_model=AgentConfigurationView)
def save_agent_configuration(
    org: UUID, body: AgentConfigurationInput, actor: Actor
) -> dict[str, Any]:
    with transaction(actor, org) as conn:
        row = conn.execute(
            text("""UPDATE app.agents SET name = :name, identity = :identity,
                instructions = :instructions, version = version + 1, updated_at = now()
                WHERE organization_id = :org AND version = :version
                RETURNING name, identity, instructions, version, active"""),
            {"org": org, **body.model_dump()},
        ).mappings().first()
        if row is not None:
            return dict(row)
        read_agent_configuration(conn, org)
        raise HTTPException(409, "Configuração alterada em outra sessão. Recarregue os dados.")


def require_catalog_manager(conn: Connection, org: UUID) -> None:
    if read_operation(conn, org)["role"] != "gestor":
        raise HTTPException(403, "Catálogo restrito ao gestor.")


def product_view(row: Any) -> dict[str, Any]:
    return {"id": row["id"], "name": row["name"], "price": row["price"],
            "available": row["available"], "status": row["status"],
            "version": row["version"], "commercialRevision": row["commercial_revision"]}


def advance_commercial_revision(conn: Connection, org: UUID) -> int:
    row = conn.execute(text("""UPDATE app.organizations
        SET commercial_revision = commercial_revision + 1
        WHERE id = :org RETURNING commercial_revision"""), {"org": org}).first()
    if row is None:
        raise HTTPException(403, "Catálogo restrito ao gestor.")
    return int(row[0])


def record_product_version(conn: Connection, org: UUID, product: UUID) -> None:
    conn.execute(text("""INSERT INTO app.product_versions
        (organization_id, product_id, version, commercial_revision, name, price,
         available, status, recorded_by)
        SELECT organization_id, id, version, commercial_revision, name, price,
               available, status, private.actor_id()
        FROM app.products WHERE organization_id = :org AND id = :product"""),
        {"org": org, "product": product})


@app.get("/v1/orgs/{org}/products")
def list_products(org: UUID, actor: Actor) -> dict[str, Any]:
    with transaction(actor, org) as conn:
        require_catalog_manager(conn, org)
        rows = conn.execute(text("""SELECT o.commercial_revision AS catalog_revision,
            p.id, p.name, p.price::text AS price, p.available, p.status,
            p.version, p.commercial_revision
            FROM app.organizations o LEFT JOIN app.products p
              ON p.organization_id = o.id AND p.status = 'ready'
            WHERE o.id = :org ORDER BY p.name, p.id"""),
            {"org": org}).mappings().all()
        return {"commercialRevision": rows[0]["catalog_revision"],
                "products": [product_view(row) for row in rows if row["id"] is not None]}


@app.post("/v1/orgs/{org}/products", status_code=201, response_model=ProductView)
def create_product(org: UUID, body: ProductInput, actor: Actor) -> dict[str, Any]:
    with transaction(actor, org) as conn:
        require_catalog_manager(conn, org)
        revision = advance_commercial_revision(conn, org)
        try:
            row = conn.execute(text("""INSERT INTO app.products
                (organization_id, name, price, available, commercial_revision, created_by)
                VALUES (:org, :name, :price, :available, :revision, private.actor_id())
                RETURNING id, name, price::text AS price, available, status, version, commercial_revision"""),
                {"org": org, **body.model_dump(), "revision": revision}).mappings().one()
        except DBAPIError as exc:
            if getattr(exc.orig, "sqlstate", None) == "23505":
                raise HTTPException(409, "Já existe produto vigente com esse nome.") from None
            raise
        record_product_version(conn, org, row["id"])
        return product_view(row)


@app.put("/v1/orgs/{org}/products/{product}", response_model=ProductView)
def update_product(org: UUID, product: UUID, body: ProductUpdate, actor: Actor) -> dict[str, Any]:
    with transaction(actor, org) as conn:
        require_catalog_manager(conn, org)
        revision = advance_commercial_revision(conn, org)
        try:
            row = conn.execute(text("""UPDATE app.products
                SET name = :name, price = :price, available = :available,
                    version = version + 1, commercial_revision = :revision, updated_at = now()
                WHERE organization_id = :org AND id = :product AND version = :version
                    AND status = 'ready'
                RETURNING id, name, price::text AS price, available, status, version, commercial_revision"""),
                {"org": org, "product": product, **body.model_dump(), "revision": revision})\
                .mappings().first()
        except DBAPIError as exc:
            if getattr(exc.orig, "sqlstate", None) == "23505":
                raise HTTPException(409, "Já existe produto vigente com esse nome.") from None
            raise
        if row is None:
            exists = conn.execute(text("SELECT 1 FROM app.products WHERE organization_id = :org AND id = :product"),
                                  {"org": org, "product": product}).first()
            if exists is None:
                raise HTTPException(404, "Produto não encontrado.")
            raise HTTPException(409, "Produto alterado em outra sessão. Recarregue os dados.")
        record_product_version(conn, org, product)
        return product_view(row)


@app.get("/v1/orgs/{org}/products/{product}/versions")
def list_product_versions(org: UUID, product: UUID, actor: Actor) -> list[dict[str, Any]]:
    with transaction(actor, org) as conn:
        require_catalog_manager(conn, org)
        rows = conn.execute(text("""SELECT product_id AS id, name, price::text AS price,
            available, status, version, commercial_revision FROM app.product_versions
            WHERE organization_id = :org AND product_id = :product ORDER BY version"""),
            {"org": org, "product": product}).mappings().all()
        if not rows:
            raise HTTPException(404, "Produto não encontrado.")
        return [product_view(row) for row in rows]


@app.post("/v1/orgs/{org}/products/{product}/revoke", response_model=ProductView)
def revoke_product(org: UUID, product: UUID, body: ProductVersionInput, actor: Actor) -> dict[str, Any]:
    with transaction(actor, org) as conn:
        require_catalog_manager(conn, org)
        revision = advance_commercial_revision(conn, org)
        row = conn.execute(text("""UPDATE app.products
            SET status = 'revoked', version = version + 1,
                commercial_revision = :revision, updated_at = now()
            WHERE organization_id = :org AND id = :product AND version = :version
                AND status = 'ready'
            RETURNING id, name, price::text AS price, available, status, version, commercial_revision"""),
            {"org": org, "product": product, "version": body.version, "revision": revision})\
            .mappings().first()
        if row is None:
            exists = conn.execute(text("SELECT 1 FROM app.products WHERE organization_id = :org AND id = :product"),
                                  {"org": org, "product": product}).first()
            if exists is None:
                raise HTTPException(404, "Produto não encontrado.")
            raise HTTPException(409, "Produto alterado em outra sessão. Recarregue os dados.")
        record_product_version(conn, org, product)
        return product_view(row)


def pending_checks(configuration: dict[str, Any]) -> list[dict[str, str]]:
    checks = [
        ("commercial_source", "Fonte comercial utilizável"),
        ("channel", "Canal operacional"),
        ("qualification", "Critérios de qualificação"),
        ("contingency_owner", "Responsável de contingência"),
        ("v02", "Checklist definitivo V02"),
    ]
    if not configuration["instructions"]:
        checks.insert(0, ("instructions", "Instruções do agente"))
    return [{"code": code, "label": label, "status": "pending"} for code, label in checks]


@app.get("/v1/orgs/{org}/agent/readiness")
def get_agent_readiness(org: UUID, actor: Actor) -> dict[str, Any]:
    with transaction(actor, org) as conn:
        configuration = read_agent_configuration(conn, org)
    return {"ready": False, "blockers": pending_checks(configuration)}


@app.post("/v1/orgs/{org}/agent/activate", status_code=409)
def activate_agent(org: UUID, actor: Actor) -> JSONResponse:
    with transaction(actor, org) as conn:
        configuration = read_agent_configuration(conn, org)
    return JSONResponse(status_code=409, content={
        "error": {"code": "AGENT_NOT_READY", "message": "A ativação tem impedimentos.",
                  "retryable": False, "request_id": str(uuid4())},
        "blockers": pending_checks(configuration),
    })


@app.post("/v1/orgs/{org}/test-automation/enable")
def enable_test_automation(org: UUID, actor: Actor) -> dict[str, Any]:
    if os.environ.get("APP_ENV") != "local":
        raise HTTPException(404, "Simulação indisponível.")
    with transaction(actor, org) as conn:
        try:
            epoch = conn.execute(text("SELECT private.enable_test_automation(:org)"),
                                 {"org": org}).scalar_one()
        except DBAPIError as exc:
            if getattr(exc.orig, "sqlstate", None) == "42501":
                raise HTTPException(403, "Controle não autorizado.") from None
            raise
    return {"simulationEnabled": True, "automationEpoch": epoch}


@app.post("/v1/orgs/{org}/conversations/{conversation}/test-auto-intents", status_code=202)
def create_test_auto_intent(
    org: UUID, conversation: UUID, body: TestAutomaticInput, actor: Actor,
) -> dict[str, str]:
    if os.environ.get("APP_ENV") != "local":
        raise HTTPException(404, "Simulação indisponível.")
    with transaction(actor, org) as conn:
        try:
            intent = conn.execute(text("""SELECT private.prepare_test_auto_intent(
                :org, :conversation, :command, :body)"""),
                {"org": org, "conversation": conversation, "command": body.command_id,
                 "body": body.text}).scalar_one()
        except DBAPIError as exc:
            code = getattr(exc.orig, "sqlstate", None)
            if code == "P0002":
                raise HTTPException(404, "Conversa não encontrada.") from None
            if code == "42501":
                raise HTTPException(403, "Resposta automática inelegível.") from None
            raise
    return {"intentId": str(intent), "status": "pending"}


@app.post("/v1/orgs/{org}/conversations/{conversation}/test-catalog-reply", status_code=202)
def create_test_catalog_reply(org: UUID, conversation: UUID, actor: Actor) -> Any:
    if os.environ.get("APP_ENV") != "local":
        raise HTTPException(404, "Simulação indisponível.")
    with transaction(actor, org) as conn:
        operation = read_operation(conn, org)
        if operation["role"] != "gestor":
            raise HTTPException(403, "Acesso de gestor necessário.")
        organization = conn.execute(text("""SELECT commercial_revision, simulation_enabled,
            automation_paused FROM app.organizations WHERE id = :org FOR UPDATE"""),
            {"org": org}).mappings().one()
        current = conn.execute(text("""SELECT input_revision, mode, contact_blocked
            FROM app.conversations WHERE organization_id = :org AND id = :conversation"""),
            {"org": org, "conversation": conversation}).mappings().first()
        if current is None:
            raise HTTPException(404, "Conversa não encontrada.")
        message = conn.execute(text("""SELECT m.id, m.text FROM app.messages m
            WHERE m.organization_id = :org AND m.conversation_id = :conversation
            ORDER BY m.received_at DESC, m.id DESC LIMIT 1"""),
            {"org": org, "conversation": conversation}).mappings().first()
        if message is None:
            raise HTTPException(404, "Mensagem não encontrada.")
        existing = conn.execute(text("""SELECT id, intent_id, status, model, prompt_version,
            commercial_revision, estimated_cost_usd FROM app.catalog_agent_runs
            WHERE organization_id = :org AND conversation_id = :conversation
              AND message_id = :message"""),
            {"org": org, "conversation": conversation,
             "message": message["id"]}).mappings().first()
        if existing is not None:
            return {"runId": str(existing["id"]),
                    "intentId": str(existing["intent_id"]) if existing["intent_id"] else "",
                    "status": existing["status"], "model": existing["model"],
                    "promptVersion": existing["prompt_version"],
                    "commercialRevision": existing["commercial_revision"],
                    "estimatedCostUsd": str(existing["estimated_cost_usd"])
                    if existing["estimated_cost_usd"] is not None else "unknown"}
        if (not organization["simulation_enabled"] or organization["automation_paused"]
                or current["mode"] != "automatic" or current["contact_blocked"]):
            raise HTTPException(403, "Resposta automática inelegível.")
        spent = conn.execute(text("""SELECT COALESCE(SUM(
            COALESCE(estimated_cost_usd, 0.01)), 0)
            FROM app.catalog_agent_runs WHERE organization_id = :org"""),
            {"org": org}).scalar_one()
        if spent + Decimal("0.01") > MAX_COST_USD:
            raise HTTPException(429, "Limite de custo da demonstração atingido.")
        products = conn.execute(text("""SELECT id, name, price, available, version
            FROM app.products WHERE organization_id = :org AND status = 'ready'
            ORDER BY name, id LIMIT 100"""), {"org": org}).mappings().all()
        run = conn.execute(text("""INSERT INTO app.catalog_agent_runs(
            organization_id, conversation_id, message_id, status, model, prompt_version,
            commercial_revision) VALUES (:org, :conversation, :message, 'running',
            :model, :prompt, :revision) RETURNING id"""),
            {"org": org, "conversation": conversation, "message": message["id"],
             "model": MODEL, "prompt": PROMPT_VERSION,
             "revision": organization["commercial_revision"]}).scalar_one()
    choices = [{"id": str(p["id"]), "name": p["name"]} for p in products]
    if re.search(r"\b(desconto|descontos|cupom|abatimento)\b",
                 message["text"], re.IGNORECASE):
        with transaction(actor, org) as conn:
            conn.execute(text("""SELECT private.handoff_catalog_reply(
                :org, :conversation, :message, :revision, 'commercial_exception')"""),
                {"org": org, "conversation": conversation, "message": message["id"],
                 "revision": current["input_revision"]})
            conn.execute(text("""UPDATE app.catalog_agent_runs SET status = 'handoff',
                estimated_cost_usd = 0, updated_at = now()
                WHERE organization_id = :org AND id = :run"""),
                {"org": org, "run": run})
        return {"runId": str(run), "status": "handoff", "model": MODEL,
                "promptVersion": PROMPT_VERSION,
                "commercialRevision": organization["commercial_revision"],
                "estimatedCostUsd": "0.000000"}
    try:
        greeting = is_greeting(message["text"])
        selection = (Selection(None, 0, 0, Decimal(0)) if greeting else
                     select_product(message["text"], choices))
    except (RuntimeError, ValueError, TypeError, IndexError, KeyError,
            StopIteration, httpx.HTTPError):
        with transaction(actor, org) as conn:
            conn.execute(text("""SELECT private.handoff_catalog_reply(
                :org, :conversation, :message, :revision, 'provider_unavailable')"""),
                {"org": org, "conversation": conversation, "message": message["id"],
                 "revision": current["input_revision"]})
            conn.execute(text("""UPDATE app.catalog_agent_runs SET status = 'handoff',
                failure_code = 'provider_unavailable', updated_at = now()
                WHERE organization_id = :org AND id = :run"""),
                {"org": org, "run": run})
        return {"runId": str(run), "status": "handoff", "model": MODEL,
                "promptVersion": PROMPT_VERSION,
                "commercialRevision": organization["commercial_revision"],
                "estimatedCostUsd": "unknown"}
    product = next((p for p in products if p["id"] == selection.product_id), None)
    conflicting = product is not None and any(
        other["id"] != product["id"]
        and other["name"].strip().casefold() == product["name"].strip().casefold()
        and (other["price"] != product["price"]
             or other["available"] != product["available"])
        for other in products
    )
    name_supported = (product is not None and product["name"].strip().casefold()
                      in message["text"].casefold())
    if conflicting:
        with transaction(actor, org) as conn:
            conn.execute(text("""SELECT private.handoff_catalog_reply(
                :org, :conversation, :message, :revision, 'catalog_conflict')"""),
                {"org": org, "conversation": conversation, "message": message["id"],
                 "revision": current["input_revision"]})
            conn.execute(text("""UPDATE app.catalog_agent_runs SET status = 'handoff',
                input_tokens = :input_tokens, output_tokens = :output_tokens,
                estimated_cost_usd = :cost, updated_at = now()
                WHERE organization_id = :org AND id = :run"""),
                {"org": org, "run": run, "input_tokens": selection.input_tokens,
                 "output_tokens": selection.output_tokens,
                 "cost": selection.estimated_cost_usd})
        return {"runId": str(run), "status": "handoff", "model": MODEL,
                "promptVersion": PROMPT_VERSION,
                "commercialRevision": organization["commercial_revision"],
                "estimatedCostUsd": str(selection.estimated_cost_usd)}
    if product is None or not product["available"] or not name_supported:
        answer = ("Olá! Posso ajudar com informações dos produtos cadastrados. "
                  "Qual produto você gostaria de conhecer?" if greeting else
                  "Não encontrei essa informação no catálogo. Diga o nome de um produto "
                  "cadastrado para eu ajudar.")
    else:
        price = ("Preço sob consulta" if product["price"] is None else
                 f"R$ {product['price']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        answer = (f"Sou um atendimento automatizado. {product['name']} está disponível. "
                  f"{price}. Para falar com uma pessoa, é só pedir.")
    with transaction(actor, org) as conn:
        try:
            latest_revision = conn.execute(text("""SELECT commercial_revision
                FROM app.organizations WHERE id = :org FOR UPDATE"""),
                {"org": org}).scalar_one()
            if latest_revision != organization["commercial_revision"]:
                conn.execute(text("""SELECT private.handoff_catalog_reply(
                    :org, :conversation, :message, :revision, 'catalog_conflict')"""),
                    {"org": org, "conversation": conversation,
                     "message": message["id"], "revision": current["input_revision"]})
                conn.execute(text("""UPDATE app.catalog_agent_runs SET status = 'handoff',
                    failure_code = 'commercial_revision_changed',
                    input_tokens = :input_tokens, output_tokens = :output_tokens,
                    estimated_cost_usd = :cost, updated_at = now()
                    WHERE organization_id = :org AND id = :run"""),
                    {"org": org, "run": run, "input_tokens": selection.input_tokens,
                     "output_tokens": selection.output_tokens,
                     "cost": selection.estimated_cost_usd})
                return {"runId": str(run), "status": "handoff", "model": MODEL,
                        "promptVersion": PROMPT_VERSION,
                        "commercialRevision": latest_revision,
                        "estimatedCostUsd": str(selection.estimated_cost_usd)}
            latest_input = conn.execute(text("""SELECT input_revision FROM app.conversations
                WHERE organization_id = :org AND id = :conversation"""),
                {"org": org, "conversation": conversation}).scalar_one()
            if latest_input != current["input_revision"]:
                conn.execute(text("""UPDATE app.catalog_agent_runs SET status = 'failed',
                    failure_code = 'input_changed', input_tokens = :input_tokens,
                    output_tokens = :output_tokens, estimated_cost_usd = :cost,
                    updated_at = now() WHERE organization_id = :org AND id = :run"""),
                    {"org": org, "run": run, "input_tokens": selection.input_tokens,
                     "output_tokens": selection.output_tokens,
                     "cost": selection.estimated_cost_usd})
                return JSONResponse(status_code=409, content={
                    "runId": str(run), "status": "superseded", "model": MODEL,
                    "promptVersion": PROMPT_VERSION,
                    "commercialRevision": organization["commercial_revision"],
                    "estimatedCostUsd": str(selection.estimated_cost_usd),
                })
            intent = conn.execute(text("""SELECT private.prepare_test_auto_intent(
                :org, :conversation, :command, :body)"""),
                {"org": org, "conversation": conversation,
                 "command": message["id"], "body": answer}).scalar_one()
            conn.execute(text("""UPDATE app.catalog_agent_runs SET status = 'pending',
                intent_id = :intent, input_tokens = :input_tokens,
                output_tokens = :output_tokens, estimated_cost_usd = :cost,
                updated_at = now() WHERE organization_id = :org AND id = :run"""),
                {"org": org, "run": run, "intent": intent,
                 "input_tokens": selection.input_tokens,
                 "output_tokens": selection.output_tokens,
                 "cost": selection.estimated_cost_usd})
        except DBAPIError as exc:
            if getattr(exc.orig, "sqlstate", None) == "42501":
                raise HTTPException(403, "Resposta automática inelegível.") from None
            raise
    return {"runId": str(run), "intentId": str(intent), "status": "pending",
            "model": MODEL, "promptVersion": PROMPT_VERSION,
            "commercialRevision": organization["commercial_revision"],
            "estimatedCostUsd": str(selection.estimated_cost_usd)}


@app.post("/v1/orgs/{org}/automation/pause")
def pause_automation(org: UUID, actor: Actor) -> JSONResponse:
    with transaction(actor, org) as conn:
        try:
            row = conn.execute(text("""SELECT epoch, pending_attempts
                FROM private.pause_automation(:org)"""), {"org": org}).one()
            control_id = conn.execute(text("""SELECT private.record_control(
                :org, NULL, 'global_pause')"""), {"org": org}).scalar_one()
        except DBAPIError as exc:
            if getattr(exc.orig, "sqlstate", None) == "42501":
                raise HTTPException(403, "Controle não autorizado.") from None
            raise
    pending = row.pending_attempts > 0
    return JSONResponse(status_code=202 if pending else 200, content={
        "control_applied": True,
        "completion": "pending_external_attempt" if pending else "complete",
        "pendingAttempts": row.pending_attempts,
        "automationEpoch": row.epoch,
        "controlId": str(control_id),
    })


@app.get("/v1/orgs/{org}/controls/{control}")
def get_control_status(org: UUID, control: UUID, actor: Actor) -> dict[str, Any]:
    with transaction(actor, org) as conn:
        try:
            row = conn.execute(text("""SELECT completion, prior_accepted, rejected_count,
                unknown_count, pending_count FROM private.authorized_control_status(:org, :control)"""),
                {"org": org, "control": control}).one()
        except DBAPIError as exc:
            code = getattr(exc.orig, "sqlstate", None)
            if code == "P0002":
                raise HTTPException(404, "Controle não encontrado.") from None
            if code == "42501":
                raise HTTPException(403, "Controle não autorizado.") from None
            raise
    return {"control_applied": True, "completion": row.completion,
            "priorAccepted": row.prior_accepted, "rejectedCount": row.rejected_count,
            "unknownCount": row.unknown_count, "pendingAttempts": row.pending_count}


@app.post("/v1/orgs/{org}/automation/resume")
def resume_automation(org: UUID, actor: Actor) -> dict[str, Any]:
    with transaction(actor, org) as conn:
        try:
            epoch = conn.execute(text("SELECT private.resume_automation(:org)"),
                                 {"org": org}).scalar_one()
        except DBAPIError as exc:
            if getattr(exc.orig, "sqlstate", None) == "42501":
                raise HTTPException(403, "Controle não autorizado.") from None
            raise
    return {"control_applied": True, "completion": "complete", "automationEpoch": epoch}


@app.post("/v1/orgs/{org}/conversations/{conversation}/test-contact-block")
def set_test_contact_block(
    org: UUID, conversation: UUID, body: TestContactBlockInput, actor: Actor,
) -> dict[str, Any]:
    if os.environ.get("APP_ENV") != "local":
        raise HTTPException(404, "Simulação indisponível.")
    with transaction(actor, org) as conn:
        try:
            version = conn.execute(text("""SELECT private.set_test_contact_block(
                :org, :conversation, :blocked)"""),
                {"org": org, "conversation": conversation,
                 "blocked": body.blocked}).scalar_one()
        except DBAPIError as exc:
            code = getattr(exc.orig, "sqlstate", None)
            if code == "P0002":
                raise HTTPException(404, "Conversa não encontrada.") from None
            if code == "42501":
                raise HTTPException(403, "Controle não autorizado.") from None
            if code == "23514":
                raise HTTPException(409, "Contato com opt-out; reautorização não disponível.") from None
            raise
    return {"contactBlocked": body.blocked, "controlVersion": version}


@app.post("/v1/orgs/{org}/conversations/{conversation}/resume-ai")
def resume_ai(
    org: UUID, conversation: UUID, body: ConversationVersionInput, actor: Actor,
) -> dict[str, Any]:
    if os.environ.get("APP_ENV") != "local":
        raise HTTPException(409, "O retorno à IA depende da ativação real do agente.")
    with transaction(actor, org) as conn:
        try:
            version = conn.execute(text("SELECT private.resume_ai(:org, :conversation, :version)"),
                                   {"org": org, "conversation": conversation,
                                    "version": body.version}).scalar_one()
        except DBAPIError as exc:
            code = getattr(exc.orig, "sqlstate", None)
            if code == "P0002":
                raise HTTPException(404, "Conversa não encontrada.") from None
            if code == "42501":
                raise HTTPException(403, "Retorno não autorizado.") from None
            if code in {"40001", "23514"}:
                raise HTTPException(409, "Conversa inelegível. Recarregue antes de retomar a IA.") from None
            raise
    return {"mode": "automatic", "controlVersion": version}


@app.post("/v1/orgs/{org}/sellers", status_code=201, response_model=SellerView)
def create_seller(org: UUID, body: SellerInput, actor: Actor) -> dict[str, Any]:
    with transaction(actor, org) as conn:
        read_operation(conn, org)
        row = conn.execute(
            text("""INSERT INTO app.sellers(organization_id, name, email, phone, available)
                VALUES (:org, :name, lower(:email), :phone, :available)
                RETURNING id, name, email, phone, available, active"""),
            {"org": org, **body.model_dump()},
        ).mappings().one()
        return {**row, "access": "registered"}


@app.get("/v1/orgs/{org}/sellers", response_model=list[SellerView])
def list_sellers(org: UUID, actor: Actor) -> list[dict[str, Any]]:
    with transaction(actor, org) as conn:
        read_operation(conn, org)
        rows = conn.execute(
            text("""SELECT s.id, s.name, s.email, s.phone, s.available, s.active,
                m.status AS member_status, m.password_changed
                FROM app.sellers s LEFT JOIN app.org_members m
                  ON m.organization_id = s.organization_id AND m.seller_id = s.id
                WHERE s.organization_id = :org ORDER BY s.created_at, s.id"""),
            {"org": org},
        ).mappings().all()
        return [{"id": row["id"], "name": row["name"], "email": row["email"],
                 "phone": row["phone"], "available": row["available"], "active": row["active"],
                 "access": "registered" if row["member_status"] is None else
                 "revoked" if row["member_status"] == "revoked" else
                 "enabled" if row["password_changed"] else "password_change_required"}
                for row in rows]


@app.post("/v1/orgs/{org}/sellers/{seller}/enable")
def enable_seller(org: UUID, seller: UUID, actor: Actor) -> dict[str, str]:
    with transaction(actor, org) as conn:
        read_operation(conn, org)
        row = conn.execute(
            text("""SELECT s.email, m.user_id FROM app.sellers s
                LEFT JOIN app.org_members m ON m.organization_id = s.organization_id
                  AND m.seller_id = s.id
                WHERE s.organization_id = :org AND s.id = :seller"""),
            {"org": org, "seller": seller},
        ).mappings().first()
        if row is None:
            raise HTTPException(404, "Vendedor não encontrado.")
        if row["user_id"] is not None:
            raise HTTPException(409, "Vendedor já habilitado.")
        if not row["email"]:
            raise HTTPException(409, "Cadastre o e-mail do vendedor antes de habilitar.")
        email = row["email"]
    temporary_password = secrets.token_urlsafe(24)
    try:
        response = httpx.post(os.environ["AUTH_URL"] + "/signup",
                              json={"email": email, "password": temporary_password}, timeout=10)
    except httpx.HTTPError:
        raise HTTPException(503, "Autenticação indisponível.") from None
    if not response.is_success:
        raise HTTPException(409, "Não foi possível habilitar este e-mail.")
    user_id = UUID(response.json()["user"]["id"])
    with transaction(actor, org) as conn:
        conn.execute(text("SELECT private.enable_seller(:org, :seller, :user)"),
                     {"org": org, "seller": seller, "user": user_id})
    return {"temporary_password": temporary_password}


@app.get("/v1/orgs/{org}/sellers/me/eligibility", response_model=None)
def seller_eligibility(org: UUID, actor: Actor) -> dict[str, Any] | JSONResponse:
    with transaction(actor, org) as conn:
        row = conn.execute(text("""SELECT m.password_changed, s.active, s.available
            FROM app.org_members m JOIN app.sellers s
              ON s.organization_id = m.organization_id AND s.id = m.seller_id
            WHERE m.organization_id = :org AND m.user_id = :actor
              AND m.role = 'vendedor' AND m.status = 'active'"""),
            {"org": org, "actor": actor},
        ).mappings().first()
    if row is None:
        raise HTTPException(404, "Vínculo não encontrado.")
    if not row["password_changed"]:
        return JSONResponse(status_code=403, content={"error": {
            "code": "PASSWORD_CHANGE_REQUIRED", "message": "Troque a senha inicial para continuar.",
            "retryable": False, "request_id": str(uuid4())}})
    return {"eligible": row["active"] and row["available"],
            "active": row["active"], "available": row["available"]}


@app.post("/v1/orgs/{org}/sellers/me/password")
def change_seller_password(
    org: UUID, body: SellerPasswordInput, actor: Actor,
    authorization: Annotated[str, Header()],
) -> dict[str, bool]:
    if body.current_password == body.new_password:
        raise HTTPException(422, "A nova senha deve ser diferente da inicial.")
    with transaction(actor, org) as conn:
        row = conn.execute(text("""SELECT s.email FROM app.org_members m
            JOIN app.sellers s ON s.organization_id = m.organization_id AND s.id = m.seller_id
            WHERE m.organization_id = :org AND m.user_id = :actor
              AND m.role = 'vendedor' AND m.status = 'active' AND NOT m.password_changed"""),
            {"org": org, "actor": actor},
        ).mappings().first()
    if row is None:
        raise HTTPException(404, "Vínculo pendente não encontrado.")
    try:
        current = httpx.post(os.environ["AUTH_URL"] + "/token?grant_type=password",
                             json={"email": row["email"],
                                   "password": body.current_password}, timeout=10)
        if not current.is_success:
            raise HTTPException(400, "Senha atual incorreta.")
        changed = httpx.put(os.environ["AUTH_URL"] + "/user",
                            headers={"Authorization": authorization},
                            json={"password": body.new_password}, timeout=10)
    except httpx.HTTPError:
        raise HTTPException(503, "Autenticação indisponível.") from None
    if not changed.is_success:
        raise HTTPException(503, "Não foi possível trocar a senha.")
    with transaction(actor, org) as conn:
        conn.execute(text("SELECT private.complete_seller_password(:org)"), {"org": org})
    return {"password_changed": True}


@app.post("/v1/orgs/{org}/sellers/{seller}/revoke")
def revoke_seller(org: UUID, seller: UUID, actor: Actor) -> dict[str, bool]:
    with transaction(actor, org) as conn:
        read_operation(conn, org)
        exists = conn.execute(text("""SELECT 1 FROM app.org_members
            WHERE organization_id = :org AND seller_id = :seller
              AND role = 'vendedor' AND status = 'active'"""),
            {"org": org, "seller": seller},
        ).first()
        if exists is None:
            raise HTTPException(404, "Vínculo ativo não encontrado.")
        conn.execute(text("SELECT private.revoke_seller(:org, :seller)"),
                     {"org": org, "seller": seller})
    return {"revoked": True}


@app.put("/v1/orgs/{org}/sellers/{seller}/availability")
def update_seller_availability(
    org: UUID, seller: UUID, body: SellerAvailabilityInput, actor: Actor
) -> dict[str, bool]:
    with transaction(actor, org) as conn:
        read_operation(conn, org)
        row = conn.execute(text("""UPDATE app.sellers
            SET active = :active, available = :available
            WHERE organization_id = :org AND id = :seller
            RETURNING active, available"""),
            {"org": org, "seller": seller, **body.model_dump()},
        ).mappings().first()
        if row is None:
            raise HTTPException(404, "Vendedor não encontrado.")
        return dict(row)


@app.post("/v1/orgs/{org}/test-channels", status_code=201)
def create_test_channel(org: UUID, body: TestChannelInput, actor: Actor) -> dict[str, str]:
    if os.environ.get("APP_ENV") != "local":
        raise HTTPException(404, "Canal de teste indisponível.")
    token = secrets.token_urlsafe(32)
    with transaction(actor, org) as conn:
        operation = read_operation(conn, org)
        if operation["role"] != "gestor":
            raise HTTPException(403, "Acesso de gestor necessário.")
        row = conn.execute(
            text("""INSERT INTO app.channels(organization_id, kind, token_hash)
                VALUES (:org, :kind, :hash) RETURNING id"""),
            {"org": org, "kind": body.kind, "hash": sha256(token.encode()).hexdigest()},
        ).one()
    return {"id": str(row.id), "kind": body.kind, "token": token}


@app.post("/v1/test-channels/{channel}/events")
def receive_test_event(
    channel: UUID,
    body: TestInboundEvent,
    request: Request,
    response: Response,
    test_channel_token: Annotated[str, Header(alias="X-Test-Channel-Token")] = "",
) -> dict[str, Any]:
    if os.environ.get("APP_ENV") != "local":
        raise HTTPException(404, "Canal de teste indisponível.")
    if len(test_channel_token) > 256 or int(request.headers.get("content-length", "0")) > 16384:
        raise HTTPException(413, "Evento excede o limite do canal de teste.")
    token_hash = sha256(test_channel_token.encode()).hexdigest()
    opt_out = None
    with transaction(UUID(int=0)) as conn:
        try:
            row = conn.execute(
                text("""SELECT organization_id, conversation_id, outbox_id, duplicate, status
                    FROM private.receive_test_event_serialized(:channel, :hash, :type, :event, :message,
                        :chat, :user, :name, :body, :occurred, :sequence)"""),
                {"channel": channel, "hash": token_hash,
                 "type": body.event_type, "event": body.external_event_id,
                 "message": body.external_message_id, "chat": body.external_chat_id,
                 "user": body.external_user_id, "name": body.contact_name,
                 "body": body.content.text, "occurred": body.occurred_at,
                 "sequence": body.provider_sequence},
            ).mappings().one()
            if body.event_type == "message" and is_explicit_human_request(body.content.text):
                conn.execute(text("""SELECT private.request_human_from_test_event(
                    :channel, :hash, :event)"""),
                    {"channel": channel, "hash": token_hash, "event": body.external_event_id},
                )
            if (body.event_type == "message" and not row["duplicate"]
                    and is_explicit_opt_out(body.content.text)):
                opt_out = conn.execute(text("""SELECT source_event_id, pending_attempts
                    FROM private.apply_test_opt_out(:channel, :hash, :event)"""),
                    {"channel": channel, "hash": token_hash,
                     "event": body.external_event_id}).mappings().one()
            elif body.event_type == "message" and not row["duplicate"]:
                conn.execute(text("""SELECT private.forward_opted_out_test_event(
                    :channel, :hash, :event)"""),
                    {"channel": channel, "hash": token_hash,
                     "event": body.external_event_id})
        except DBAPIError as exc:
            if getattr(exc.orig, "sqlstate", None) == "28000":
                raise HTTPException(401, "Origem do canal inválida.") from None
            raise
    if opt_out and opt_out["pending_attempts"]:
        response.status_code = 202
    return {"organizationId": str(row["organization_id"]),
            "conversationId": str(row["conversation_id"]) if row["conversation_id"] else None,
            "outboxId": str(row["outbox_id"]) if row["outbox_id"] else None,
            "duplicate": row["duplicate"], "status": row["status"],
            **({"control_applied": True,
                "completion": "pending_external_attempt" if opt_out["pending_attempts"] else "complete",
                "sourceEventId": str(opt_out["source_event_id"])} if opt_out else {})}


@app.get("/v1/orgs/{org}/conversations/{conversation}")
def get_conversation(org: UUID, conversation: UUID, actor: Actor) -> dict[str, Any]:
    with transaction(actor, org) as conn:
        member = conn.execute(text("""SELECT role FROM app.org_members
            WHERE organization_id = :org AND user_id = :actor AND status = 'active'"""),
            {"org": org, "actor": actor},
        ).first()
        if member is None or member.role not in {"gestor", "vendedor"}:
            raise HTTPException(404, "Conversa não encontrada.")
        row = conn.execute(text("""SELECT c.id, c.input_revision, c.control_version,
            c.channel_id, c.external_chat_id,
            c.mode, c.assigned_seller_id, c.claimed_by, c.handoff_reason,
            c.contact_blocked, o.reason AS opt_out_reason,
            o.source_event_id AS opt_out_source_event_id,
            o.created_at AS opt_out_created_at,
            c.summary, c.summary_status, l.id AS lead_id, l.external_user_id, l.name, l.stage
            FROM app.conversations c JOIN app.leads l
              ON l.organization_id = c.organization_id AND l.id = c.lead_id
            LEFT JOIN app.contact_opt_outs o ON o.organization_id = c.organization_id
              AND o.channel_id = c.channel_id AND o.lead_id = c.lead_id
            WHERE c.organization_id = :org AND c.id = :conversation"""),
            {"org": org, "conversation": conversation},
        ).mappings().first()
        if row is None:
            raise HTTPException(404, "Conversa não encontrada.")
        messages = conn.execute(text("""SELECT id, external_message_id, text, occurred_at,
            received_at FROM app.messages
            WHERE organization_id = :org AND conversation_id = :conversation
            ORDER BY received_at, id LIMIT 100"""),
            {"org": org, "conversation": conversation},
        ).mappings().all()
        intents = conn.execute(text("""SELECT i.id, i.command_id, i.author_id, i.text, i.status,
            i.external_message_id, i.error_code, i.created_at, d.reason AS incident_reason,
            d.next_action AS incident_next_action FROM app.outbound_intents i
            LEFT JOIN app.delivery_incidents d ON d.organization_id = i.organization_id
              AND d.intent_id = i.id
            WHERE i.organization_id = :org AND i.conversation_id = :conversation
            ORDER BY i.created_at, i.id LIMIT 100"""),
            {"org": org, "conversation": conversation},
        ).mappings().all()
    return {"id": str(row["id"]), "channelId": str(row["channel_id"]),
            "externalChatId": row["external_chat_id"], "inputRevision": row["input_revision"],
            "controlVersion": row["control_version"],
            "mode": row["mode"], "contactBlocked": row["contact_blocked"],
            "optOut": {"reason": row["opt_out_reason"],
                       "sourceEventId": str(row["opt_out_source_event_id"]),
                       "createdAt": row["opt_out_created_at"].isoformat()}
            if row["opt_out_reason"] else None,
            "assignedSellerId": str(row["assigned_seller_id"])
            if row["assigned_seller_id"] else None,
            "claimedBy": str(row["claimed_by"]) if row["claimed_by"] else None,
            "handoffReason": row["handoff_reason"], "summary": row["summary"],
            "summaryStatus": row["summary_status"],
            "lead": {"id": str(row["lead_id"]), "externalUserId": row["external_user_id"],
                     "name": row["name"], "stage": row["stage"]},
            "messages": [{"id": str(item["id"]), "externalMessageId": item["external_message_id"],
                          "text": item["text"], "occurredAt": item["occurred_at"].isoformat(),
                          "receivedAt": item["received_at"].isoformat()} for item in messages],
            "outboundIntents": [{"id": str(item["id"]), "commandId": str(item["command_id"]),
                                 "authorId": str(item["author_id"]), "text": item["text"],
                                 "status": item["status"], "readStatus": "unknown",
                                 "externalMessageId": item["external_message_id"],
                                 "errorCode": item["error_code"],
                                 "incidentReason": item["incident_reason"],
                                 "incidentNextAction": item["incident_next_action"],
                                 "createdAt": item["created_at"].isoformat()} for item in intents]}


@app.post("/v1/orgs/{org}/conversations/{conversation}/claim")
def claim_conversation(
    org: UUID, conversation: UUID, body: ConversationVersionInput, actor: Actor,
) -> JSONResponse:
    with transaction(actor, org) as conn:
        try:
            row = conn.execute(text("""SELECT mode, claimed_by, control_version, pending_attempts
                FROM private.claim_conversation_control(:org, :conversation, :version)"""),
                {"org": org, "conversation": conversation, "version": body.version},
            ).mappings().one()
            control_id = conn.execute(text("""SELECT private.record_control(
                :org, :conversation, 'human_claim')"""),
                {"org": org, "conversation": conversation}).scalar_one()
        except DBAPIError as exc:
            code = getattr(exc.orig, "sqlstate", None)
            if code == "P0002":
                raise HTTPException(404, "Conversa não encontrada.") from None
            if code == "42501":
                raise HTTPException(403, "Assunção não autorizada.") from None
            if code == "40001":
                raise HTTPException(409, "Conversa alterada. Recarregue antes de assumir.") from None
            raise
    pending = row["pending_attempts"] > 0
    return JSONResponse(status_code=202 if pending else 200, content={
        "mode": row["mode"], "claimedBy": str(row["claimed_by"]),
        "controlVersion": row["control_version"], "control_applied": True,
        "completion": "pending_external_attempt" if pending else "complete",
        "controlId": str(control_id),
    })


@app.post("/v1/orgs/{org}/conversations/{conversation}/assign")
def assign_conversation(
    org: UUID, conversation: UUID, body: ConversationAssignInput, actor: Actor,
) -> dict[str, Any]:
    with transaction(actor, org) as conn:
        try:
            row = conn.execute(text("""SELECT mode, assigned_seller_id, claimed_by, control_version
                FROM private.assign_conversation(:org, :conversation, :seller, :reason, :version)"""),
                {"org": org, "conversation": conversation, "seller": body.seller_id,
                 "reason": body.reason, "version": body.version},
            ).mappings().one()
        except DBAPIError as exc:
            code = getattr(exc.orig, "sqlstate", None)
            if code == "P0002":
                raise HTTPException(404, "Conversa não encontrada.") from None
            if code == "42501":
                raise HTTPException(403, "Atribuição não autorizada ou vendedor inelegível.") from None
            if code == "40001":
                raise HTTPException(409, "Conversa alterada. Recarregue antes de atribuir.") from None
            raise
    return {"mode": row["mode"], "assignedSellerId": str(row["assigned_seller_id"]),
            "claimedBy": str(row["claimed_by"]) if row["claimed_by"] else None,
            "controlVersion": row["control_version"]}


@app.post("/v1/orgs/{org}/conversations/{conversation}/messages", status_code=202)
def create_human_message(
    org: UUID, conversation: UUID, body: HumanReplyInput, actor: Actor,
) -> dict[str, Any]:
    with transaction(actor, org) as conn:
        try:
            row = conn.execute(text("""SELECT intent_id, author_id, status
                FROM private.create_human_reply(:org, :conversation, :version, :command, :body)"""),
                {"org": org, "conversation": conversation, "version": body.version,
                 "command": body.command_id, "body": body.text},
            ).mappings().one()
        except DBAPIError as exc:
            code = getattr(exc.orig, "sqlstate", None)
            if code == "P0002":
                raise HTTPException(404, "Conversa não encontrada.") from None
            if code == "42501":
                raise HTTPException(403, "Resposta não autorizada.") from None
            if code == "40001":
                raise HTTPException(409, "Conversa ou comando alterado.") from None
            raise
    return {"intentId": str(row["intent_id"]), "authorId": str(row["author_id"]),
            "status": row["status"], "readStatus": "unknown"}


@app.get("/v1/orgs/{org}/human-queue")
def get_human_queue(org: UUID, actor: Actor) -> list[dict[str, Any]]:
    with transaction(actor, org) as conn:
        member = conn.execute(text("""SELECT role, password_changed FROM app.org_members
            WHERE organization_id = :org AND user_id = :actor AND status = 'active'"""),
            {"org": org, "actor": actor}).first()
        if member is not None and member.role == "vendedor" and not member.password_changed:
            raise HTTPException(404, "Fila não encontrada.")
        if member is not None and member.role == "vendedor":
            rows = conn.execute(text("""SELECT c.id AS conversation_id, c.claimed_by,
                c.assigned_seller_id, c.summary_status, l.name AS lead_name
                FROM app.conversations c JOIN app.leads l
                  ON l.organization_id = c.organization_id AND l.id = c.lead_id
                JOIN app.org_members m ON m.organization_id = c.organization_id
                  AND m.seller_id = c.assigned_seller_id
                WHERE c.organization_id = :org AND m.user_id = :actor
                  AND m.status = 'active' AND m.password_changed
                  AND c.mode IN ('awaiting_human', 'human')
                ORDER BY c.handoff_requested_at, c.id LIMIT 100"""),
                {"org": org, "actor": actor}).mappings().all()
            return [{"id": str(row["conversation_id"]),
                     "conversationId": str(row["conversation_id"]),
                     "reason": "explicit_request", "nextAction": "Assumir e responder.",
                     "state": "open", "createdAt": "", "leadName": row["lead_name"],
                     "assignedSellerId": str(row["assigned_seller_id"]),
                     "claimedBy": str(row["claimed_by"]) if row["claimed_by"] else None,
                     "summaryStatus": row["summary_status"]} for row in rows]
        if member is None or member.role != "gestor":
            raise HTTPException(404, "Fila não encontrada.")
        rows = conn.execute(text("""SELECT i.id, i.conversation_id, i.reason,
            i.owner_member_id, i.next_action, i.state, i.created_at,
            c.assigned_seller_id, c.claimed_by, c.summary_status, l.name AS lead_name
            FROM app.operation_incidents i
            JOIN app.conversations c ON c.organization_id = i.organization_id
              AND c.id = i.conversation_id
            JOIN app.leads l ON l.organization_id = c.organization_id AND l.id = c.lead_id
            WHERE i.organization_id = :org AND i.state = 'open'
            ORDER BY i.created_at, i.id LIMIT 100"""),
            {"org": org},
        ).mappings().all()
    return [{"id": str(row["id"]), "conversationId": str(row["conversation_id"]),
             "reason": row["reason"], "ownerMemberId": str(row["owner_member_id"]),
             "nextAction": row["next_action"], "state": row["state"],
             "createdAt": row["created_at"].isoformat(), "leadName": row["lead_name"],
             "assignedSellerId": str(row["assigned_seller_id"])
             if row["assigned_seller_id"] else None,
             "claimedBy": str(row["claimed_by"]) if row["claimed_by"] else None,
             "summaryStatus": row["summary_status"]} for row in rows]


@app.post("/v1/orgs/{org}/test-dispatch/{intent}")
def dispatch_test_message(
    org: UUID, intent: UUID, actor: Actor,
    outcome: Annotated[str, Header(alias="X-Test-Delivery-Outcome")] = "accepted",
    delay_ms: Annotated[int, Header(alias="X-Test-Dispatch-Delay-Ms")] = 0,
    crash_after_start: Annotated[bool, Header(alias="X-Test-Crash-After-Start")] = False,
) -> dict[str, str]:
    if os.environ.get("APP_ENV") != "local":
        raise HTTPException(404, "Dispatcher de teste indisponível.")
    if outcome not in {"accepted", "rejected", "timeout_after_accept"}:
        raise HTTPException(422, "Resultado de teste inválido.")
    if not 0 <= delay_ms <= 1000:
        raise HTTPException(422, "Atraso de teste inválido.")
    try:
        with transaction(actor, org) as conn:
            started, status = conn.execute(text("""SELECT started, current_status
                FROM private.authorize_test_dispatch(:org, :intent)"""),
                {"org": org, "intent": intent}).one()
        if not started:
            return {"status": status}
        if crash_after_start:
            raise HTTPException(503, "Worker de teste interrompido após iniciar tentativa.")
        if delay_ms:
            time.sleep(delay_ms / 1000)
        with transaction(actor, org) as conn:
            status = conn.execute(text("SELECT private.finish_test_dispatch(:org, :intent, :outcome)"),
                                  {"org": org, "intent": intent, "outcome": outcome}).scalar_one()
    except DBAPIError as exc:
        code = getattr(exc.orig, "sqlstate", None)
        if code == "P0002":
            raise HTTPException(404, "Intenção não encontrada.") from None
        if code == "42501":
            raise HTTPException(403, "Envio não autorizado.") from None
        raise
    return {"status": status}


@app.post("/v1/orgs/{org}/test-recovery/run")
def run_test_recovery(org: UUID, body: TestRecoveryInput, actor: Actor) -> dict[str, int]:
    if os.environ.get("APP_ENV") != "local":
        raise HTTPException(404, "Recuperação de teste indisponível.")
    with transaction(actor, org) as conn:
        try:
            count = conn.execute(text("""SELECT private.recover_test_dispatches(:org, :as_of)"""),
                                 {"org": org,
                                  "as_of": datetime.now(UTC)
                                  + timedelta(seconds=body.advance_seconds)}).scalar_one()
        except DBAPIError as exc:
            if getattr(exc.orig, "sqlstate", None) == "42501":
                raise HTTPException(403, "Recuperação não autorizada.") from None
            raise
    return {"abandonedDispatches": count}


@app.get("/v1/orgs/{org}/recovery/incidents")
def get_recovery_incidents(org: UUID, actor: Actor) -> list[dict[str, Any]]:
    with transaction(actor, org) as conn:
        operation = read_operation(conn, org)
        if operation["role"] != "gestor":
            raise HTTPException(403, "Acesso de gestor necessário.")
        rows = conn.execute(text("""SELECT d.id, d.intent_id, i.conversation_id,
            d.reason, d.state, d.owner_member_id, d.next_action, d.created_at
            FROM app.delivery_incidents d JOIN app.outbound_intents i
              ON i.organization_id = d.organization_id AND i.id = d.intent_id
            WHERE d.organization_id = :org ORDER BY d.created_at DESC, d.id DESC LIMIT 100"""),
            {"org": org}).mappings().all()
    return [{"id": str(row["id"]), "intentId": str(row["intent_id"]),
             "conversationId": str(row["conversation_id"]), "reason": row["reason"],
             "state": row["state"], "ownerMemberId": str(row["owner_member_id"])
             if row["owner_member_id"] else None,
             "nextAction": row["next_action"], "createdAt": row["created_at"].isoformat()}
            for row in rows]


@app.get("/v1/orgs/{org}/recovery/outbox-incidents")
def get_outbox_recovery_incidents(org: UUID, actor: Actor) -> list[dict[str, Any]]:
    with transaction(actor, org) as conn:
        operation = read_operation(conn, org)
        if operation["role"] != "gestor":
            raise HTTPException(403, "Acesso de gestor necessário.")
        rows = conn.execute(text("""SELECT i.id, i.outbox_id, i.reason,
            i.owner_member_id, i.next_action, i.created_at, o.recovery_attempts
            FROM app.outbox_recovery_incidents i JOIN app.outbox_events o
              ON o.organization_id = i.organization_id AND o.id = i.outbox_id
            WHERE i.organization_id = :org ORDER BY i.created_at DESC, i.id DESC LIMIT 100"""),
            {"org": org}).mappings().all()
    return [{"id": str(row["id"]), "outboxId": str(row["outbox_id"]),
             "reason": row["reason"], "ownerMemberId": str(row["owner_member_id"]),
             "nextAction": row["next_action"], "attempts": row["recovery_attempts"],
             "createdAt": row["created_at"].isoformat()} for row in rows]


@app.post("/v1/orgs/{org}/recovery/incidents/{incident}/resolve")
def resolve_recovery_incident(
    org: UUID, incident: UUID, body: RecoveryResolutionInput, actor: Actor,
) -> dict[str, str]:
    with transaction(actor, org) as conn:
        try:
            state = conn.execute(text("""SELECT private.resolve_delivery_incident(
                :org, :incident, :evidence)"""), {"org": org, "incident": incident,
                                                   "evidence": body.evidence}).scalar_one()
        except DBAPIError as exc:
            code = getattr(exc.orig, "sqlstate", None)
            if code == "P0002":
                raise HTTPException(404, "Incidente não encontrado.") from None
            if code == "42501":
                raise HTTPException(403, "Resolução não autorizada.") from None
            if code == "23514":
                raise HTTPException(409, "Incidente sem envio incerto.") from None
            raise
    return {"state": state, "intentStatus": "unknown"}


@app.get("/v1/orgs/{org}/test-channels/{channel}/sent")
def get_test_channel_messages(org: UUID, channel: UUID, actor: Actor) -> list[dict[str, str]]:
    if os.environ.get("APP_ENV") != "local":
        raise HTTPException(404, "Canal de teste indisponível.")
    with transaction(actor, org) as conn:
        operation = read_operation(conn, org)
        if operation["role"] != "gestor":
            raise HTTPException(403, "Acesso de gestor necessário.")
        rows = conn.execute(text("""SELECT intent_id, external_message_id, text
            FROM app.test_channel_messages WHERE organization_id = :org AND channel_id = :channel
            ORDER BY accepted_at, id"""), {"org": org, "channel": channel}).mappings().all()
    return [{"intentId": str(row["intent_id"]), "externalMessageId": row["external_message_id"],
             "text": row["text"]} for row in rows]


@app.post("/v1/orgs/{org}/test-outbox/{outbox}/publish")
def publish_test_outbox(
    org: UUID, outbox: UUID, actor: Actor,
    test_crash_after_effect: Annotated[bool, Header(alias="X-Test-Crash-After-Effect")] = False,
) -> dict[str, Any]:
    if os.environ.get("APP_ENV") != "local":
        raise HTTPException(404, "Publicação de teste indisponível.")
    with transaction(actor, org) as conn:
        operation = read_operation(conn, org)
        if operation["role"] != "gestor":
            raise HTTPException(403, "Acesso de gestor necessário.")
        exists = conn.execute(text("""SELECT 1 FROM app.outbox_events
            WHERE organization_id = :org AND id = :outbox"""),
            {"org": org, "outbox": outbox},
        ).first()
        if exists is None:
            raise HTTPException(404, "Evento não encontrado.")
        row = conn.execute(text("""SELECT new_effect, effect_count
            FROM private.consume_test_outbox(:org, :outbox)"""),
            {"org": org, "outbox": outbox},
        ).one()
    if test_crash_after_effect:
        raise HTTPException(503, "Publicação de teste interrompida após efeito.")
    with transaction(actor, org) as conn:
        conn.execute(text("""UPDATE app.outbox_events SET published_at = coalesce(published_at, now())
            WHERE organization_id = :org AND id = :outbox"""),
            {"org": org, "outbox": outbox},
        )
    return {"newEffect": row.new_effect, "effectCount": row.effect_count}
