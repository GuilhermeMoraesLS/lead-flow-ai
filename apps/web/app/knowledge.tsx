"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { BookOpen, Download, FileText, Upload } from "lucide-react";
import { Badge, EmptyState, Notice, Tone } from "./components/ui";
import { apiUrl } from "./lib/api";

type Session = { token: string; organizationId: string };
type Version = { id: string; status: string; errorCode: string | null; errorMessage: string | null;
  retryable: boolean; mediaType: string; sizeBytes: number; chunkCount: number | null;
  createdAt: string; readyAt: string | null };
type KnowledgeDocument = { id: string; title: string; usable: boolean; activeVersionId: string | null;
  latest: Version };
type Knowledge = { profile: string; maxBytes: number; documents: KnowledgeDocument[] };

const types: Record<string, string> = { pdf: "pdf", docx: "docx", txt: "txt", md: "md", markdown: "md" };
const statusLabels: Record<string, [string, Tone]> = {
  uploaded: ["Na fila", "info"], validating: ["Validando", "info"], extracting: ["Extraindo texto", "info"],
  embedding: ["Indexando", "info"], ready: ["Pronto para uso", "success"], failed: ["Falhou", "danger"],
};

async function sha256(file: File) {
  const digest = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function formatSize(bytes: number) {
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MiB` : `${Math.ceil(bytes / 1024)} KiB`;
}

export default function KnowledgeBase({ session }: { session: Session }) {
  const [knowledge, setKnowledge] = useState<Knowledge | null>(null);
  const [correcting, setCorrecting] = useState<KnowledgeDocument | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState(false);
  const base = `${apiUrl}/v1/orgs/${session.organizationId}/knowledge`;

  const request = useCallback(async (path: string, options?: RequestInit) => {
    const response = await fetch(path, { ...options, headers: {
      Authorization: "Bearer " + session.token, ...options?.headers,
    } });
    if (response.status === 204) return null;
    const body = await response.json();
    if (!response.ok) throw new Error(body.error?.message ?? "Não foi possível consultar os documentos.");
    return body;
  }, [session.token]);

  const reload = useCallback(async () => {
    try { setKnowledge(await request(base) as Knowledge); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Não foi possível consultar os documentos."); }
  }, [base, request]);

  useEffect(() => { void Promise.resolve().then(reload); }, [reload]);

  const processing = knowledge?.documents.some((d) => !["ready", "failed"].includes(d.latest.status)) ?? false;
  useEffect(() => {
    if (!processing) return;
    const timer = setInterval(() => void reload(), 3000);
    return () => clearInterval(timer);
  }, [processing, reload]);

  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setNotice("");
    const form = event.currentTarget;
    const file = (new FormData(form).get("file") as File | null);
    if (!file || file.size === 0) { setError("Selecione um arquivo com conteúdo."); return; }
    const mediaType = types[file.name.split(".").pop()?.toLowerCase() ?? ""];
    if (!mediaType) { setError("Formato não suportado. Envie PDF textual, DOCX, TXT ou Markdown."); return; }
    setPending(true);
    try {
      const upload = await request(`${base}/uploads`, { method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: file.name, mediaType, size: file.size,
          ...(correcting ? { documentId: correcting.id } : {}) }) });
      await request(apiUrl + upload.uploadUrl, { method: "PUT",
        headers: { "Content-Type": "application/octet-stream" }, body: file });
      const submitted = await request(`${base}/${upload.uploadId}/submit`, { method: "POST",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify({ sha256: await sha256(file) }) });
      setNotice(submitted.duplicate ? "Este conteúdo já tinha sido enviado; nenhuma nova ingestão foi criada."
        : "Documento recebido. Ele só será usado depois de ficar pronto.");
      setCorrecting(null); form.reset();
      await reload();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível enviar o documento.");
    } finally { setPending(false); }
  }

  async function download(item: KnowledgeDocument) {
    setError("");
    try {
      const response = await fetch(`${base}/${item.id}/versions/${item.latest.id}/file`,
        { headers: { Authorization: "Bearer " + session.token } });
      if (!response.ok) throw new Error("Arquivo indisponível.");
      const url = URL.createObjectURL(await response.blob());
      const link = Object.assign(window.document.createElement("a"), { href: url, download: item.title });
      link.click(); URL.revokeObjectURL(url);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Arquivo indisponível."); }
  }

  const usable = knowledge?.documents.filter((d) => d.usable).length ?? 0;

  return <>
    {notice && <Notice tone="success">{notice}</Notice>}
    {error && <Notice tone="error">{error}</Notice>}
    <div className="grid-side">
      <section className="card form-card">
        <div className="card-header"><h2><Upload size={18} aria-hidden="true" />
          {correcting ? "Enviar correção" : "Enviar documento"}</h2></div>
        <form onSubmit={send} className="form-stack" key={correcting?.id ?? "new"}>
          <label>Arquivo<input name="file" type="file" required accept=".pdf,.docx,.txt,.md,.markdown" /></label>
          <small className="field-hint">PDF com texto selecionável, DOCX, TXT ou Markdown, até 10 MiB. OCR,
            macros e links externos não são processados.</small>
          {correcting && <p className="muted small">Corrigindo {correcting.title}.</p>}
          <div className="button-row">
            <button className="btn" disabled={pending}>{pending ? "Enviando…" : "Enviar arquivo"}</button>
            {correcting && <button type="button" className="btn btn-ghost" disabled={pending}
              onClick={() => setCorrecting(null)}>Cancelar correção</button>}
          </div>
        </form>
      </section>
      <section className="card">
        <div className="card-header"><h2><BookOpen size={18} aria-hidden="true" />Documentos</h2>
          <div className="badge-row"><Badge tone="success">{usable} prontos</Badge></div></div>
        {!knowledge && <div className="skeleton-block" />}
        {knowledge && knowledge.documents.length === 0 && <EmptyState icon={<FileText size={22} />}
          title="Nenhum documento enviado.">Envie políticas, perguntas frequentes ou materiais de apoio.</EmptyState>}
        {knowledge && knowledge.documents.length > 0 && <ul className="entity-list">{knowledge.documents.map((item) => {
          const [label, tone] = statusLabels[item.latest.status] ?? [item.latest.status, "neutral"];
          return <li key={item.id} className="entity">
            <span className="entity-icon"><FileText size={18} aria-hidden="true" /></span>
            <div className="entity-body">
              <strong>{item.title}</strong>
              <span className="entity-meta">{item.latest.mediaType.toUpperCase()} · {formatSize(item.latest.sizeBytes)}
                {item.latest.chunkCount ? ` · ${item.latest.chunkCount} trechos indexados` : ""}</span>
              {item.latest.errorMessage && <span className="entity-meta" role="status">{item.latest.errorMessage}</span>}
            </div>
            <Badge tone={tone}>{label}</Badge>
            <div className="entity-actions">
              <button type="button" className="btn btn-sm btn-ghost" onClick={() => void download(item)}
                aria-label={`Baixar ${item.title}`}><Download size={14} aria-hidden="true" />Baixar</button>
              {item.latest.status === "failed" && !item.usable && <button type="button" className="btn btn-sm"
                disabled={pending} onClick={() => setCorrecting(item)} aria-label={`Corrigir ${item.title}`}>
                <Upload size={14} aria-hidden="true" />Enviar correção</button>}
            </div>
          </li>;
        })}</ul>}
      </section>
    </div>
  </>;
}
