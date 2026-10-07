"""Manager knowledge base: private uploads, isolated extraction and fixed-profile vectors.

A version is usable only after validation, extraction and embedding finish in one fenced
publication. Failures stay on their own version and never touch other documents.
"""

import hashlib
import json
import os
import secrets
import subprocess
import sys
from dataclasses import dataclass
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import UUID

import httpx
import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError

from leadflow.auth import actor_id
from leadflow.database import transaction

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
EMBEDDING_PROFILE = f"openai:{EMBEDDING_MODEL}:{EMBEDDING_DIMENSIONS}"
EMBEDDING_USD_PER_MILLION = Decimal("0.02")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
UPLOAD_TTL = timedelta(minutes=15)
LEASE_SECONDS = 300
MAX_ATTEMPTS = 3
PARSER_TIMEOUT_SECONDS = 30
# SPEC §4.8 proposes 400–800 tokens with 80 overlap; ~4 characters per token.
CHUNK_CHARS = 2400
CHUNK_OVERLAP = 320
MAX_EVIDENCE = 6
PARSER_PATH = Path(__file__).with_name("knowledge_parser.py")
EXTENSIONS = {"pdf": (".pdf",), "docx": (".docx",), "txt": (".txt",),
              "md": (".md", ".markdown")}
RETRYABLE = {"embedding_unavailable", "ingestion_retry_exhausted"}
MESSAGES = {
    "type_mismatch": "O conteúdo não corresponde ao tipo informado. Envie um PDF textual, "
                     "DOCX, TXT ou Markdown válido.",
    "invalid_encoding": "O texto não está em UTF-8. Salve o arquivo em UTF-8 e envie novamente.",
    "no_text": "Não encontramos texto extraível; OCR não é suportado. Envie uma versão com "
               "texto selecionável.",
    "active_content": "O arquivo contém conteúdo ativo (macros, scripts, anexos ou entidades "
                      "externas) e foi recusado. Salve uma cópia sem esse conteúdo e envie "
                      "novamente.",
    "archive_limits": "O DOCX excede os limites seguros de descompactação. Reduza o arquivo "
                      "e envie novamente.",
    "encrypted": "PDF protegido por senha. Remova a proteção e envie novamente.",
    "too_many_pages": "O PDF passa de 500 páginas. Divida o documento e envie as partes.",
    "text_too_large": "O texto extraído é grande demais. Divida o documento e envie as partes.",
    "malformed": "Arquivo corrompido ou ilegível. Gere o arquivo novamente e envie outra vez.",
    "parser_timeout": "A leitura excedeu o tempo limite. Divida o documento e envie as partes.",
    "object_mismatch": "O arquivo armazenado não corresponde ao enviado. Envie novamente.",
    "embedding_unavailable": "O serviço de indexação ficou indisponível. Envie o mesmo arquivo "
                             "novamente para tentar outra vez.",
    "embedding_budget_exhausted": "Limite de custo de indexação do ambiente de teste atingido. "
                                  "Fale com o responsável técnico antes de enviar novamente.",
    "embedding_profile_mismatch": "A indexação retornou um formato inesperado. Envie novamente; "
                                  "se persistir, fale com o responsável técnico.",
    "ingestion_retry_exhausted": "O processamento foi interrompido repetidas vezes. Envie o "
                                 "mesmo arquivo novamente para tentar outra vez.",
}

router = APIRouter()
Actor = Annotated[UUID, Depends(actor_id)]


class UploadInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    filename: str = Field(min_length=1, max_length=200)
    mediaType: Literal["pdf", "docx", "txt", "md"]
    size: int = Field(ge=1)
    documentId: UUID | None = None


class SubmitInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sha256: str = Field(pattern="^[0-9a-f]{64}$")


class SearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=1000)


class EmbeddingError(Exception):
    pass


@dataclass(frozen=True)
class Embeddings:
    vectors: list[list[float]]
    tokens: int


@dataclass(frozen=True)
class Chunk:
    location: str
    text: str


@dataclass(frozen=True)
class Claim:
    organization_id: str
    version_id: str
    document_id: str
    claim_token: str
    attempts: int
    media_type: str
    size_bytes: int
    object_key: str
    content_hash: str


def storage_root() -> Path:
    return Path(os.environ["KNOWLEDGE_STORAGE_DIR"])


def object_path(key: str) -> Path:
    organization, upload = key.split("/")
    return storage_root() / str(UUID(organization)) / str(UUID(upload))


def embedding_cost(tokens: int) -> Decimal:
    cost = Decimal(tokens) * EMBEDDING_USD_PER_MILLION / Decimal(1_000_000)
    return cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def embed_texts(texts: list[str]) -> Embeddings:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise EmbeddingError("unavailable")
    vectors: list[list[float]] = []
    tokens = 0
    for start in range(0, len(texts), 64):
        try:
            response = httpx.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": EMBEDDING_MODEL, "input": texts[start:start + 64],
                      "encoding_format": "float"},
                timeout=30,
            )
            response.raise_for_status()
            body = response.json()
            if not str(body["model"]).startswith(EMBEDDING_MODEL):
                raise EmbeddingError("unexpected model")
            vectors.extend(item["embedding"] for item in
                           sorted(body["data"], key=lambda item: item["index"]))
            tokens += int(body["usage"]["total_tokens"])
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            raise EmbeddingError("unavailable") from error
    return Embeddings(vectors, tokens)


def vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(repr(float(value)) for value in vector) + "]"


def require_manager(conn: Connection, org: UUID) -> None:
    if not conn.execute(text("SELECT private.gestor_of(:org)"), {"org": org}).scalar_one():
        raise HTTPException(404, "Operação não encontrada.")


def version_view(row: Any) -> dict[str, Any]:
    code = row["error_code"]
    return {"id": row["version_id"], "status": row["status"], "errorCode": code,
            "errorMessage": MESSAGES.get(code) if code else None,
            "retryable": code in RETRYABLE, "mediaType": row["media_type"],
            "sizeBytes": row["size_bytes"], "chunkCount": row["chunk_count"],
            "contentHash": row["content_hash"], "createdAt": row["version_created_at"],
            "readyAt": row["ready_at"]}


VERSION_COLUMNS = """v.id AS version_id, v.status, v.error_code, v.media_type, v.size_bytes,
    v.chunk_count, v.content_hash, v.created_at AS version_created_at, v.ready_at"""


@router.get("/v1/orgs/{org}/knowledge")
def list_documents(org: UUID, actor: Actor) -> dict[str, Any]:
    with transaction(actor, org) as conn:
        require_manager(conn, org)
        rows = conn.execute(text(f"""SELECT d.id, d.title, d.active_version_id, {VERSION_COLUMNS}
            FROM app.knowledge_documents d
            JOIN LATERAL (SELECT * FROM app.knowledge_versions x
              WHERE x.organization_id = d.organization_id AND x.document_id = d.id
              ORDER BY x.created_at DESC, x.id LIMIT 1) v ON true
            WHERE d.organization_id = :org ORDER BY d.created_at DESC, d.id"""),
            {"org": org}).mappings().all()
    return {"profile": EMBEDDING_PROFILE, "maxBytes": MAX_UPLOAD_BYTES,
            "formats": list(EXTENSIONS),
            "documents": [{"id": row["id"], "title": row["title"],
                           "usable": row["active_version_id"] is not None,
                           "activeVersionId": row["active_version_id"],
                           "latest": version_view(row)} for row in rows]}


@router.get("/v1/orgs/{org}/knowledge/{document}/versions")
def list_versions(org: UUID, document: UUID, actor: Actor) -> list[dict[str, Any]]:
    with transaction(actor, org) as conn:
        require_manager(conn, org)
        rows = conn.execute(text(f"""SELECT {VERSION_COLUMNS} FROM app.knowledge_versions v
            WHERE v.organization_id = :org AND v.document_id = :document
            ORDER BY v.created_at, v.id"""), {"org": org, "document": document}).mappings().all()
        if not rows:
            raise HTTPException(404, "Documento não encontrado.")
    return [version_view(row) for row in rows]


@router.post("/v1/orgs/{org}/knowledge/uploads", status_code=201)
def create_upload(org: UUID, body: UploadInput, actor: Actor) -> dict[str, Any]:
    if body.size > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Arquivo acima de 10 MiB. Divida ou reduza o documento.")
    if not body.filename.lower().endswith(EXTENSIONS[body.mediaType]):
        raise HTTPException(422, "A extensão do arquivo não corresponde ao tipo informado.")
    token = secrets.token_urlsafe(32)
    with transaction(actor, org) as conn:
        require_manager(conn, org)
        if body.documentId is not None:
            document = conn.execute(text("""SELECT active_version_id FROM app.knowledge_documents
                WHERE organization_id = :org AND id = :document"""),
                {"org": org, "document": body.documentId}).first()
            if document is None:
                raise HTTPException(404, "Documento não encontrado.")
            if document[0] is not None:
                raise HTTPException(409, "Este documento já está disponível; a substituição de "
                                         "versões ainda não é suportada.")
        row = conn.execute(text("""INSERT INTO app.knowledge_uploads
            (organization_id, document_id, filename, media_type, declared_size, token_hash,
             expires_at, created_by)
            VALUES (:org, :document, :filename, :media_type, :size, :token_hash,
                    now() + make_interval(secs => :ttl), private.actor_id())
            RETURNING id, expires_at"""),
            {"org": org, "document": body.documentId, "filename": body.filename.strip(),
             "media_type": body.mediaType, "size": body.size,
             "token_hash": hashlib.sha256(token.encode()).hexdigest(),
             "ttl": UPLOAD_TTL.total_seconds()}).mappings().one()
    return {"uploadId": row["id"], "expiresAt": row["expires_at"], "maxBytes": body.size,
            "uploadUrl": f"/v1/orgs/{org}/knowledge/uploads/{row['id']}?token={token}"}


def authorize_put(actor: UUID, org: UUID, upload: UUID, token: str) -> int:
    with transaction(actor, org) as conn:
        require_manager(conn, org)
        row = conn.execute(text("""SELECT declared_size, status, token_hash,
            expires_at <= now() AS expired FROM app.knowledge_uploads
            WHERE organization_id = :org AND id = :upload"""),
            {"org": org, "upload": upload}).mappings().first()
    if row is None or not secrets.compare_digest(
            row["token_hash"], hashlib.sha256(token.encode()).hexdigest()):
        raise HTTPException(404, "Envio não encontrado.")
    if row["status"] == "submitted":
        raise HTTPException(409, "Este envio já foi submetido.")
    if row["expired"]:
        raise HTTPException(410, "Link de envio expirado. Inicie um novo envio.")
    return int(row["declared_size"])


def mark_received(actor: UUID, org: UUID, upload: UUID, digest: str, size: int) -> None:
    with transaction(actor, org) as conn:
        updated = conn.execute(text("""UPDATE app.knowledge_uploads
            SET status = 'received', object_sha256 = :digest, received_size = :size
            WHERE organization_id = :org AND id = :upload AND status <> 'submitted'
              AND expires_at > now()"""),
            {"org": org, "upload": upload, "digest": digest, "size": size}).rowcount
    if updated != 1:
        raise HTTPException(409, "O envio mudou durante a transferência. Inicie um novo envio.")


@router.put("/v1/orgs/{org}/knowledge/uploads/{upload}", status_code=204)
async def put_object(org: UUID, upload: UUID, token: str, request: Request,
                     actor: Actor) -> Response:
    declared = await run_in_threadpool(authorize_put, actor, org, upload, token)
    path = object_path(f"{org}/{upload}")
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".part")
    digest = hashlib.sha256()
    size = 0
    try:
        with partial.open("wb") as handle:
            async for chunk in request.stream():
                size += len(chunk)
                if size > declared:
                    raise HTTPException(413, "O arquivo é maior que o tamanho informado.")
                digest.update(chunk)
                handle.write(chunk)
        if size != declared:
            raise HTTPException(422, "Tamanho recebido difere do informado. Envie novamente.")
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)
    await run_in_threadpool(mark_received, actor, org, upload, digest.hexdigest(), size)
    return Response(status_code=204)


@router.post("/v1/orgs/{org}/knowledge/{upload}/submit", status_code=202)
def submit_upload(org: UUID, upload: UUID, body: SubmitInput, actor: Actor) -> dict[str, Any]:
    with transaction(actor, org) as conn:
        require_manager(conn, org)
        row = conn.execute(text("""SELECT * FROM app.knowledge_uploads
            WHERE organization_id = :org AND id = :upload FOR UPDATE"""),
            {"org": org, "upload": upload}).mappings().first()
        if row is None:
            raise HTTPException(404, "Envio não encontrado.")
        if row["status"] == "submitted":
            return submission(conn, org, row["version_id"], duplicate=False)
        if row["status"] != "received":
            raise HTTPException(409, "O arquivo ainda não foi recebido.")
        if row["object_sha256"] != body.sha256:
            raise HTTPException(409, "O hash não confere com o arquivo recebido. Envie novamente.")
        conn.execute(text("SELECT pg_advisory_xact_lock(hashtext(:org), hashtext(:hash))"),
                     {"org": str(org), "hash": body.sha256})
        existing = conn.execute(text("""SELECT v.id, v.status, v.error_code
            FROM app.knowledge_versions v
            WHERE v.organization_id = :org AND v.content_hash = :hash
              AND v.embedding_profile = :profile
              AND (CAST(:document AS uuid) IS NULL OR v.document_id = :document)
            ORDER BY v.created_at, v.id LIMIT 1 FOR UPDATE"""),
            {"org": org, "hash": body.sha256, "profile": EMBEDDING_PROFILE,
             "document": row["document_id"]}).mappings().first()
        if existing is not None:
            if existing["status"] == "failed" and existing["error_code"] in RETRYABLE:
                conn.execute(text("""UPDATE app.knowledge_versions
                    SET status = 'uploaded', error_code = NULL, attempts = 0, claim_token = NULL,
                        lease_until = NULL, updated_at = now()
                    WHERE organization_id = :org AND id = :version"""),
                    {"org": org, "version": existing["id"]})
            version = existing["id"]
            duplicate = True
        else:
            document = row["document_id"] or conn.execute(text("""INSERT INTO
                app.knowledge_documents (organization_id, title, created_by)
                VALUES (:org, :title, private.actor_id()) RETURNING id"""),
                {"org": org, "title": row["filename"]}).scalar_one()
            try:
                version = conn.execute(text("""INSERT INTO app.knowledge_versions
                    (organization_id, document_id, upload_id, content_hash, embedding_profile,
                     media_type, size_bytes, object_key, created_by)
                    VALUES (:org, :document, :upload, :hash, :profile, :media_type, :size,
                            :key, private.actor_id()) RETURNING id"""),
                    {"org": org, "document": document, "upload": upload, "hash": body.sha256,
                     "profile": EMBEDDING_PROFILE, "media_type": row["media_type"],
                     "size": row["received_size"], "key": f"{org}/{upload}"}).scalar_one()
            except DBAPIError as exc:
                if getattr(exc.orig, "sqlstate", None) == "23505":
                    raise HTTPException(409, "Envio concorrente. Atualize a lista.") from None
                raise
            duplicate = False
        conn.execute(text("""UPDATE app.knowledge_uploads SET status = 'submitted',
            version_id = :version WHERE organization_id = :org AND id = :upload"""),
            {"org": org, "upload": upload, "version": version})
        result = submission(conn, org, version, duplicate)
    if duplicate:
        object_path(f"{org}/{upload}").unlink(missing_ok=True)
    return result


def submission(conn: Connection, org: UUID, version: UUID, duplicate: bool) -> dict[str, Any]:
    row = conn.execute(text("""SELECT document_id, id, status FROM app.knowledge_versions
        WHERE organization_id = :org AND id = :version"""),
        {"org": org, "version": version}).mappings().one()
    return {"documentId": row["document_id"], "versionId": row["id"], "status": row["status"],
            "duplicate": duplicate}


@router.get("/v1/orgs/{org}/knowledge/{document}/versions/{version}/file")
def download(org: UUID, document: UUID, version: UUID, actor: Actor) -> FileResponse:
    with transaction(actor, org) as conn:
        require_manager(conn, org)
        row = conn.execute(text("""SELECT v.object_key, u.filename
            FROM app.knowledge_versions v JOIN app.knowledge_uploads u
              ON u.organization_id = v.organization_id AND u.id = v.upload_id
            WHERE v.organization_id = :org AND v.document_id = :document AND v.id = :version"""),
            {"org": org, "document": document, "version": version}).mappings().first()
    if row is None or not object_path(row["object_key"]).is_file():
        raise HTTPException(404, "Arquivo não encontrado.")
    return FileResponse(object_path(row["object_key"]), media_type="application/octet-stream",
                        filename=row["filename"],
                        headers={"X-Content-Type-Options": "nosniff",
                                 "Cache-Control": "no-store"})


@router.post("/v1/orgs/{org}/knowledge/search")
def search(org: UUID, body: SearchInput, actor: Actor) -> dict[str, Any]:
    with transaction(actor, org) as conn:
        require_manager(conn, org)
    try:
        embedded = embed_texts([body.query])
    except EmbeddingError:
        raise HTTPException(503, "Busca indisponível no momento. Tente novamente.") from None
    if len(embedded.vectors) != 1 or len(embedded.vectors[0]) != EMBEDDING_DIMENSIONS:
        raise HTTPException(503, "Busca indisponível no momento. Tente novamente.")
    with transaction(actor, org) as conn:
        require_manager(conn, org)
        rows = conn.execute(text("""SELECT d.id AS document_id, d.title, c.version_id,
                c.ordinal, c.location, c.body,
                c.embedding <=> CAST(:vector AS public.vector) AS distance
            FROM app.knowledge_chunks c
            JOIN app.knowledge_versions v
              ON v.organization_id = c.organization_id AND v.id = c.version_id
            JOIN app.knowledge_documents d
              ON d.organization_id = v.organization_id AND d.id = v.document_id
             AND d.active_version_id = v.id
            WHERE c.organization_id = :org AND v.status = 'ready'
              AND v.embedding_profile = :profile
            ORDER BY distance, c.version_id, c.ordinal LIMIT :limit"""),
            {"org": org, "vector": vector_literal(embedded.vectors[0]),
             "profile": EMBEDDING_PROFILE, "limit": MAX_EVIDENCE}).mappings().all()
    return {"profile": EMBEDDING_PROFILE,
            "evidence": [{"documentId": row["document_id"], "title": row["title"],
                          "versionId": row["version_id"], "ordinal": row["ordinal"],
                          "location": row["location"], "text": row["body"],
                          "distance": float(row["distance"])} for row in rows]}


# Worker side: runs as app_worker; every state change is fenced by the claim token.

def worker_connection() -> psycopg.Connection[Any]:
    return psycopg.connect(os.environ["WORKER_DATABASE_URL"])


def claim_next(organization: str | None = None) -> Claim | None:
    with worker_connection() as conn:
        row = conn.execute("""UPDATE app.knowledge_versions v
            SET status = 'validating', attempts = v.attempts + 1,
                claim_token = gen_random_uuid(), updated_at = now(),
                lease_until = now() + make_interval(secs => %(lease)s)
            WHERE (v.organization_id, v.id) = (
              SELECT organization_id, id FROM app.knowledge_versions
              WHERE (%(org)s::uuid IS NULL OR organization_id = %(org)s::uuid)
                AND ((status = 'uploaded' AND (lease_until IS NULL OR lease_until <= now()))
                  OR (status IN ('validating', 'extracting', 'embedding')
                      AND lease_until <= now()))
              ORDER BY created_at, id LIMIT 1 FOR UPDATE SKIP LOCKED)
            RETURNING organization_id, id, document_id, claim_token, attempts, media_type,
                      size_bytes, object_key, content_hash""",
            {"lease": LEASE_SECONDS, "org": organization}).fetchone()
    if row is None:
        return None
    return Claim(str(row[0]), str(row[1]), str(row[2]), str(row[3]), int(row[4]), row[5],
                 int(row[6]), row[7], row[8])


def advance(claim: Claim, current: str, target: str, parser_version: str | None = None) -> bool:
    with worker_connection() as conn:
        row = conn.execute("""UPDATE app.knowledge_versions
            SET status = %s, parser_version = coalesce(%s, parser_version), updated_at = now()
            WHERE organization_id = %s AND id = %s AND status = %s AND claim_token = %s
            RETURNING 1""", (target, parser_version, claim.organization_id, claim.version_id,
                             current, claim.claim_token)).fetchone()
    return row is not None


def fail(claim: Claim, code: str) -> None:
    with worker_connection() as conn:
        conn.execute("""UPDATE app.knowledge_versions
            SET status = 'failed', error_code = %s, claim_token = NULL, lease_until = NULL,
                updated_at = now()
            WHERE organization_id = %s AND id = %s AND claim_token = %s
              AND status IN ('validating', 'extracting', 'embedding')""",
            (code, claim.organization_id, claim.version_id, claim.claim_token))


def retry_later(claim: Claim) -> None:
    if claim.attempts >= MAX_ATTEMPTS:
        fail(claim, "embedding_unavailable")
        return
    with worker_connection() as conn:
        conn.execute("""UPDATE app.knowledge_versions
            SET status = 'uploaded', claim_token = NULL, updated_at = now(),
                lease_until = now() + make_interval(secs => %s)
            WHERE organization_id = %s AND id = %s AND claim_token = %s
              AND status = 'embedding'""",
            (30 * claim.attempts, claim.organization_id, claim.version_id, claim.claim_token))


def extract_isolated(media_type: str, data: bytes) -> dict[str, Any]:
    environment = {name: os.environ[name] for name in ("SYSTEMROOT",) if name in os.environ}
    try:
        completed = subprocess.run(
            [sys.executable, "-I", str(PARSER_PATH), media_type], input=data,
            capture_output=True, timeout=PARSER_TIMEOUT_SECONDS, env=environment, check=False)
    except subprocess.TimeoutExpired:
        return {"error": "parser_timeout"}
    try:
        result = json.loads(completed.stdout) if completed.returncode == 0 else None
    except ValueError:
        result = None
    return result if isinstance(result, dict) else {"error": "malformed"}


def chunk_sections(sections: list[dict[str, Any]]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for section in sections:
        body = str(section["text"])
        start = 0
        while start < len(body):
            end = min(len(body), start + CHUNK_CHARS)
            if end < len(body):
                cut = max(body.rfind(mark, start + CHUNK_CHARS // 2, end) for mark in " \n\t")
                end = cut if cut > start else end
            piece = body[start:end].strip()
            if piece:
                location = str(section["location"])[:300]
                if "line" in section:
                    first = int(section["line"]) + body.count("\n", 0, start + body[start:end]
                                                              .find(piece[0]))
                    last = first + piece.count("\n")
                    location = f"linhas {first}–{last}"
                chunks.append(Chunk(location, piece))
            if end >= len(body):
                break
            start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks


def spent_budget() -> Decimal:
    with worker_connection() as conn:
        row = conn.execute("""SELECT coalesce(sum(estimated_cost_usd), 0)
            FROM app.knowledge_versions""").fetchone()
    return Decimal(row[0]) if row else Decimal(0)


def publish(claim: Claim, chunks: list[Chunk], embedded: Embeddings, parser: str) -> None:
    with worker_connection() as conn:
        ready = conn.execute("""UPDATE app.knowledge_versions
            SET status = 'ready', chunk_count = %s, embedding_tokens = %s,
                estimated_cost_usd = %s, parser_version = %s, ready_at = now(),
                updated_at = now(), claim_token = NULL, lease_until = NULL
            WHERE organization_id = %s AND id = %s AND status = 'embedding'
              AND claim_token = %s RETURNING 1""",
            (len(chunks), embedded.tokens, embedding_cost(embedded.tokens), parser,
             claim.organization_id, claim.version_id, claim.claim_token)).fetchone()
        if ready is None:
            conn.rollback()
            return
        with conn.cursor() as cursor:
            cursor.executemany("""INSERT INTO app.knowledge_chunks
                (organization_id, version_id, ordinal, location, body, embedding)
                VALUES (%s, %s, %s, %s, %s, CAST(%s AS public.vector))""",
                [(claim.organization_id, claim.version_id, ordinal, chunk.location, chunk.text,
                  vector_literal(vector))
                 for ordinal, (chunk, vector) in enumerate(zip(chunks, embedded.vectors,
                                                               strict=True))])
        conn.execute("""UPDATE app.knowledge_documents SET active_version_id = %s
            WHERE organization_id = %s AND id = %s AND active_version_id IS NULL""",
            (claim.version_id, claim.organization_id, claim.document_id))


def ingest(claim: Claim) -> None:
    if claim.attempts > MAX_ATTEMPTS:
        fail(claim, "ingestion_retry_exhausted")
        return
    try:
        data = object_path(claim.object_key).read_bytes()
    except OSError:
        data = b""
    if len(data) != claim.size_bytes or hashlib.sha256(data).hexdigest() != claim.content_hash:
        fail(claim, "object_mismatch")
        return
    if not advance(claim, "validating", "extracting"):
        return
    parsed = extract_isolated(claim.media_type, data)
    if "error" in parsed or not isinstance(parsed.get("sections"), list):
        fail(claim, str(parsed.get("error", "malformed")))
        return
    chunks = chunk_sections(parsed["sections"])
    if not chunks:
        fail(claim, "no_text")
        return
    parser = str(parsed.get("parserVersion", ""))
    if not advance(claim, "extracting", "embedding", parser):
        return
    budget = Decimal(os.environ.get("KNOWLEDGE_EMBEDDING_BUDGET_USD", "1.00"))
    estimate = embedding_cost(sum(len(chunk.text) for chunk in chunks) // 3 + 1)
    if spent_budget() + estimate > budget:
        fail(claim, "embedding_budget_exhausted")
        return
    try:
        embedded = embed_texts([chunk.text for chunk in chunks])
    except EmbeddingError:
        retry_later(claim)
        return
    if len(embedded.vectors) != len(chunks) or any(
            len(vector) != EMBEDDING_DIMENSIONS for vector in embedded.vectors):
        fail(claim, "embedding_profile_mismatch")
        return
    publish(claim, chunks, embedded, parser)


def process_due(organization: str | None = None) -> int:
    """Process one due version; called by beat and repeatable after any crash."""
    claim = claim_next(organization)
    if claim is None:
        return 0
    ingest(claim)
    return 1
