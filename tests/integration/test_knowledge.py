import io
import math
import os
import re
import subprocess
import sys
import zipfile
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
from xml.sax.saxutils import escape

import httpx
import psycopg
import pytest
from leadflow import knowledge

from scripts.local import admin_connection

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def create_org(client, headers, name):
    return client.post(
        "/v1/organizations",
        headers={**headers, "Idempotency-Key": str(uuid4())},
        json={"name": name},
    ).json()["id"]


def fake_embeddings(texts):
    """Deterministic bag-of-words vectors: shared words mean closer evidence."""
    vectors = []
    for value in texts:
        vector = [0.0] * knowledge.EMBEDDING_DIMENSIONS
        for word in re.findall(r"\w+", value.lower()):
            vector[int(sha256(word.encode()).hexdigest(), 16) % len(vector)] += 1.0
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        vectors.append([x / norm for x in vector])
    return knowledge.Embeddings(vectors, sum(len(t) // 4 for t in texts))


@pytest.fixture
def embeddings(monkeypatch):
    monkeypatch.setattr(knowledge, "embed_texts", fake_embeddings)


def run_worker(org):
    processed = 0
    while knowledge.process_due(organization=org):
        processed += 1
        assert processed < 20
    return processed


def start(client, headers, org, filename, media_type, size, document=None):
    body = {"filename": filename, "mediaType": media_type, "size": size}
    if document:
        body["documentId"] = document
    return client.post(f"/v1/orgs/{org}/knowledge/uploads", headers=headers, json=body)


def send(client, headers, org, filename, media_type, data, document=None):
    created = start(client, headers, org, filename, media_type, len(data), document)
    assert created.status_code == 201, created.text
    put = client.put(created.json()["uploadUrl"], headers=headers, content=data)
    assert put.status_code == 204, put.text
    submitted = client.post(
        f"/v1/orgs/{org}/knowledge/{created.json()['uploadId']}/submit",
        headers=headers, json={"sha256": sha256(data).hexdigest()},
    )
    assert submitted.status_code == 202, submitted.text
    return submitted.json()


def documents(client, headers, org):
    response = client.get(f"/v1/orgs/{org}/knowledge", headers=headers)
    assert response.status_code == 200, response.text
    return {d["id"]: d for d in response.json()["documents"]}


def search(client, headers, org, query):
    return client.post(f"/v1/orgs/{org}/knowledge/search", headers=headers, json={"query": query})


def pdf(lines, catalog_extra=b""):
    content = b"BT /F1 12 Tf 72 720 Td " + b" ".join(
        b"(" + line + b") Tj 0 -16 Td" for line in lines) + b" ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R " + catalog_extra + b">>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
         b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + obj + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1, xref)
    return bytes(out)


def docx(paragraphs, extra=None, document_prefix=""):
    body = "".join(
        "<w:p>" + (f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else "")
        + f"<w:r><w:t>{escape(value)}</w:t></w:r></w:p>"
        for style, value in paragraphs)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", (
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/'
            '2006/content-types"><Default Extension="xml" ContentType="application/xml"/>'
            "</Types>"))
        archive.writestr("word/document.xml", (
            f'<?xml version="1.0"?>{document_prefix}<w:document xmlns:w="{W_NS}">'
            f"<w:body>{body}</w:body></w:document>"))
        for name, data in (extra or {}).items():
            archive.writestr(name, data)
    return buffer.getvalue()


def test_document_is_usable_only_when_fully_ready(client, identity, embeddings):
    _, headers = identity()
    org = create_org(client, headers, "Alfa")
    data = "# Garantia\nA garantia do Plano Sol é de doze meses.\n\n# Entrega\nEntrega em 5 dias.\n"
    submitted = send(client, headers, org, "politicas.md", "md", data.encode())
    assert submitted["status"] == "uploaded" and submitted["duplicate"] is False

    pending = documents(client, headers, org)[submitted["documentId"]]
    assert pending["usable"] is False and pending["latest"]["status"] == "uploaded"
    assert search(client, headers, org, "garantia do Plano Sol").json()["evidence"] == []

    assert run_worker(org) == 1
    ready = documents(client, headers, org)[submitted["documentId"]]
    assert ready["usable"] is True and ready["activeVersionId"] == submitted["versionId"]
    assert ready["latest"]["status"] == "ready" and ready["latest"]["chunkCount"] == 2
    evidence = search(client, headers, org, "qual a garantia do Plano Sol").json()["evidence"]
    assert evidence[0]["location"] == "seção: Garantia"
    assert evidence[0]["versionId"] == submitted["versionId"]
    assert "doze meses" in evidence[0]["text"]
    file = client.get(f"/v1/orgs/{org}/knowledge/{submitted['documentId']}/versions/"
                      f"{submitted['versionId']}/file", headers=headers)
    assert file.status_code == 200 and file.content == data.encode()
    assert file.headers["content-type"] == "application/octet-stream"
    assert file.headers["x-content-type-options"] == "nosniff"


def test_failure_is_actionable_and_keeps_independent_sources(
    client, identity, embeddings, monkeypatch,
):
    _, headers = identity()
    org = create_org(client, headers, "Alfa")
    good = send(client, headers, org, "frete.txt", "txt", "Frete grátis acima de R$ 300.".encode())
    wrong = send(client, headers, org, "tabela.txt", "txt", pdf([b"Tabela"]))
    empty = send(client, headers, org, "scan.pdf", "pdf", pdf([]))
    run_worker(org)

    listed = documents(client, headers, org)
    assert listed[good["documentId"]]["usable"] is True
    for item, code in ((wrong, "type_mismatch"), (empty, "no_text")):
        latest = listed[item["documentId"]]["latest"]
        assert listed[item["documentId"]]["usable"] is False
        assert latest["status"] == "failed" and latest["errorCode"] == code
        assert "envie" in latest["errorMessage"].lower()
    assert search(client, headers, org, "frete grátis").json()["evidence"][0]["documentId"] == \
        good["documentId"]

    corrected = send(client, headers, org, "tabela.txt", "txt", "Tabela de preços revisada".encode(),
                     document=wrong["documentId"])
    assert corrected["documentId"] == wrong["documentId"]
    assert corrected["versionId"] != wrong["versionId"]
    run_worker(org)
    fixed = documents(client, headers, org)[wrong["documentId"]]
    assert fixed["usable"] is True and fixed["latest"]["status"] == "ready"
    replace = start(client, headers, org, "frete.txt", "txt", 10, document=good["documentId"])
    assert replace.status_code == 409

    def unavailable(texts):
        raise knowledge.EmbeddingError("unavailable")

    monkeypatch.setattr(knowledge, "embed_texts", unavailable)
    monkeypatch.setattr(knowledge, "MAX_ATTEMPTS", 1)
    content = "Horário de atendimento: 8h às 18h.".encode()
    outage = send(client, headers, org, "horario.txt", "txt", content)
    run_worker(org)
    failed = documents(client, headers, org)[outage["documentId"]]["latest"]
    assert failed["errorCode"] == "embedding_unavailable" and failed["retryable"] is True
    assert documents(client, headers, org)[good["documentId"]]["usable"] is True

    monkeypatch.setattr(knowledge, "embed_texts", fake_embeddings)
    retried = send(client, headers, org, "horario.txt", "txt", content)
    assert retried["versionId"] == outage["versionId"] and retried["status"] == "uploaded"
    run_worker(org)
    assert documents(client, headers, org)[outage["documentId"]]["usable"] is True


def test_abandoned_ingestion_is_reclaimed_after_lease(client, identity, embeddings):
    _, headers = identity()
    org = create_org(client, headers, "Alfa")
    item = send(client, headers, org, "faq.txt", "txt", "Aceitamos Pix e cartão.".encode())
    claim = knowledge.claim_next(organization=org)
    assert claim is not None and claim.version_id == item["versionId"]
    assert documents(client, headers, org)[item["documentId"]]["latest"]["status"] == "validating"
    with admin_connection() as conn:
        conn.execute("UPDATE app.knowledge_versions SET lease_until = now() - interval '1 second'"
                     " WHERE id = %s", (item["versionId"],))
    run_worker(org)
    assert documents(client, headers, org)[item["documentId"]]["usable"] is True
    assert knowledge.advance(claim, "validating", "extracting") is False


def test_type_size_and_active_content_follow_policy(client, identity, embeddings):
    _, headers = identity()
    org = create_org(client, headers, "Alfa")
    assert start(client, headers, org, "grande.pdf", "pdf", 10 * 1024 * 1024 + 1).status_code == 413
    assert start(client, headers, org, "planilha.xlsx", "docx", 10).status_code == 422
    assert start(client, headers, org, "script.exe", "txt", 10).status_code == 422

    created = start(client, headers, org, "a.txt", "txt", 5).json()
    assert client.put(created["uploadUrl"], headers=headers, content=b"123456").status_code == 413
    assert client.put(created["uploadUrl"], headers=headers, content=b"1234").status_code == 422
    forged = created["uploadUrl"].split("token=")[0] + "token=" + "x" * 43
    assert client.put(forged, headers=headers, content=b"12345").status_code == 404
    assert client.put(created["uploadUrl"], headers=headers, content=b"12345").status_code == 204
    submit = f"/v1/orgs/{org}/knowledge/{created['uploadId']}/submit"
    assert client.post(submit, headers=headers, json={"sha256": "0" * 64}).status_code == 409
    with admin_connection() as conn:
        conn.execute("UPDATE app.knowledge_uploads SET expires_at = now() - interval '1 second'"
                     " WHERE id = %s", (created["uploadId"],))
    assert client.put(created["uploadUrl"], headers=headers, content=b"12345").status_code == 410

    javascript = send(client, headers, org, "promo.pdf", "pdf", pdf(
        [b"Oferta"], b"/OpenAction << /S /JavaScript /JS (app.alert(1)) >> "))
    macro = send(client, headers, org, "macro.docx", "docx", docx(
        [(None, "Texto")], {"word/vbaProject.bin": b"\x00macro"}))
    bomb = send(client, headers, org, "bomba.docx", "docx", docx(
        [(None, "Texto")], {"word/media/zeros.xml": b"0" * (60 << 20)}))
    entity = send(client, headers, org, "xxe.docx", "docx", docx(
        [(None, "&xxe;")], document_prefix='<!DOCTYPE w [<!ENTITY xxe SYSTEM "http://x/">]>'))
    textual = send(client, headers, org, "catalogo.pdf", "pdf", pdf([b"Plano Lua custa sob consulta"]))
    word = send(client, headers, org, "prazos.docx", "docx", docx(
        [("Heading1", "Prazos"), (None, "Implantação em dez dias úteis.")]))
    run_worker(org)

    listed = documents(client, headers, org)
    assert listed[javascript["documentId"]]["latest"]["errorCode"] == "active_content"
    assert listed[macro["documentId"]]["latest"]["errorCode"] == "active_content"
    assert listed[bomb["documentId"]]["latest"]["errorCode"] == "archive_limits"
    assert listed[entity["documentId"]]["latest"]["errorCode"] == "active_content"
    assert listed[textual["documentId"]]["usable"] is True
    assert listed[word["documentId"]]["usable"] is True
    pdf_hit = search(client, headers, org, "Plano Lua consulta").json()["evidence"][0]
    assert pdf_hit["location"] == "página 1" and pdf_hit["documentId"] == textual["documentId"]
    word_hit = search(client, headers, org, "implantação dez dias").json()["evidence"][0]
    assert word_hit["location"] == "seção: Prazos"


@pytest.mark.parametrize("attempt", [
    "import socket; socket.create_connection(('127.0.0.1', 9), timeout=1)",
    "import subprocess; subprocess.run(['whoami'])",
    "import os; os.system('whoami')",
])
def test_extraction_sandbox_blocks_network_and_processes(attempt):
    parser = Path(knowledge.__file__).with_name("knowledge_parser.py")
    script = (f"import importlib.util as u; s = u.spec_from_file_location('p', r'{parser}'); "
              f"m = u.module_from_spec(s); s.loader.exec_module(m); m.install_guard(); {attempt}")
    result = subprocess.run([sys.executable, "-I", "-c", script], capture_output=True,
                            text=True, timeout=30, check=False)
    assert result.returncode != 0
    assert "blocked by extraction sandbox" in result.stderr


def test_resubmission_does_not_duplicate_ingestion(client, identity, embeddings):
    _, headers = identity()
    org = create_org(client, headers, "Alfa")
    data = "Parcelamos em até 10 vezes.".encode()
    first = send(client, headers, org, "pagamento.txt", "txt", data)
    again = send(client, headers, org, "pagamento-copia.txt", "txt", data)
    assert again["duplicate"] is True and again["versionId"] == first["versionId"]
    assert run_worker(org) == 1
    after = send(client, headers, org, "pagamento.txt", "txt", data)
    assert after["versionId"] == first["versionId"] and after["status"] == "ready"
    assert run_worker(org) == 0
    assert len(documents(client, headers, org)) == 1
    versions = client.get(f"/v1/orgs/{org}/knowledge/{first['documentId']}/versions",
                          headers=headers).json()
    assert [(v["id"], v["status"]) for v in versions] == [(first["versionId"], "ready")]
    evidence = search(client, headers, org, "parcelamos vezes").json()["evidence"]
    assert len(evidence) == 1 and evidence[0]["location"] == "linhas 1–1"
    assert evidence[0]["versionId"] == first["versionId"]


def test_other_company_cannot_download_or_retrieve_vectors(
    client, identity, embeddings, monkeypatch,
):
    alpha_actor, alpha = identity()
    _, beta = identity()
    alpha_org = create_org(client, alpha, "Alfa")
    beta_org = create_org(client, beta, "Beta")
    secret = send(client, beta, beta_org, "segredo.txt", "txt",
                  b"Desconto confidencial Beta de 40 por cento.")
    run_worker(beta_org)
    beta_file = (f"/v1/orgs/{beta_org}/knowledge/{secret['documentId']}/versions/"
                 f"{secret['versionId']}/file")
    assert client.get(beta_file, headers=beta).status_code == 200

    assert client.get(beta_file, headers=alpha).status_code == 404
    assert client.get(beta_file.replace(beta_org, alpha_org), headers=alpha).status_code == 404
    assert client.get(f"/v1/orgs/{beta_org}/knowledge", headers=alpha).status_code == 404
    assert search(client, alpha, beta_org, "desconto confidencial").status_code == 404
    assert search(client, alpha, alpha_org, "desconto confidencial Beta").json()["evidence"] == []
    pending = start(client, beta, beta_org, "b.txt", "txt", 3).json()
    assert client.put(pending["uploadUrl"], headers=alpha, content=b"abc").status_code == 404
    assert client.post(f"/v1/orgs/{alpha_org}/knowledge/{pending['uploadId']}/submit",
                       headers=alpha, json={"sha256": "0" * 64}).status_code == 404
    assert start(client, alpha, alpha_org, "x.txt", "txt", 3,
                 document=secret["documentId"]).status_code == 404

    email = f"seller-{uuid4().hex}@example.test"
    seller = client.post(f"/v1/orgs/{alpha_org}/sellers", headers=alpha, json={
        "name": "Bia", "email": email, "phone": "+5511999990000", "available": True,
    }).json()
    enabled = client.post(f"/v1/orgs/{alpha_org}/sellers/{seller['id']}/enable",
                          headers=alpha).json()
    login = httpx.post("http://127.0.0.1:54321/token?grant_type=password", json={
        "email": email, "password": enabled["temporary_password"],
    })
    seller_headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert client.get(f"/v1/orgs/{alpha_org}/knowledge", headers=seller_headers).status_code == 404

    with psycopg.connect(os.environ["DATABASE_URL"].replace("+psycopg", "")) as conn:
        conn.execute("SELECT set_config('app.user_id', %s, false), "
                     "set_config('app.organization_id', %s, false)",
                     (alpha_actor, beta_org))
        assert conn.execute("SELECT count(*) FROM app.knowledge_chunks").fetchone() == (0,)

    with admin_connection() as conn, pytest.raises(psycopg.errors.DataException):
        conn.execute("INSERT INTO app.knowledge_chunks VALUES (%s, %s, 99, 'x', 'x', '[1,2,3]')",
                     (beta_org, secret["versionId"]))
    monkeypatch.setattr(knowledge, "embed_texts",
                        lambda texts: knowledge.Embeddings([[0.1, 0.2, 0.3] for _ in texts], 3))
    mismatch = send(client, alpha, alpha_org, "dim.txt", "txt", "Dimensão errada.".encode())
    run_worker(alpha_org)
    latest = documents(client, alpha, alpha_org)[mismatch["documentId"]]["latest"]
    assert latest["errorCode"] == "embedding_profile_mismatch"


@pytest.mark.skipif(os.environ.get("LEADFLOW_LIVE_OPENAI") != "1",
                    reason="Opt-in: chamada real e paga ao provedor de embeddings.")
def test_live_openai_embeddings_index_and_retrieve(client, identity):
    _, headers = identity()
    org = create_org(client, headers, "Alfa")
    data = ("# Garantia\nO Plano Sol tem garantia de doze meses contra defeitos.\n\n"
            "# Entrega\nEnviamos para todo o Brasil em até cinco dias úteis.\n").encode()
    item = send(client, headers, org, "live.md", "md", data)
    run_worker(org)
    listed = documents(client, headers, org)[item["documentId"]]
    assert listed["usable"] is True, listed
    evidence = search(client, headers, org, "Quanto tempo de garantia tem o Plano Sol?").json()
    assert evidence["profile"] == "openai:text-embedding-3-small:1536"
    assert evidence["evidence"][0]["location"] == "seção: Garantia"
    with admin_connection() as conn:
        cost = conn.execute("SELECT estimated_cost_usd FROM app.knowledge_versions WHERE id = %s",
                            (item["versionId"],)).fetchone()[0]
    assert 0 < cost < 1
