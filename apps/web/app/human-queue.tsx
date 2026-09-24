"use client";

import { useCallback, useEffect, useState } from "react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
type Session = { token: string; organizationId: string; role?: "gestor" | "vendedor" };
type QueueItem = {
  id: string;
  conversationId: string;
  leadName: string | null;
  reason: string;
  nextAction: string;
  summaryStatus: string;
  assignedSellerId: string | null;
  claimedBy: string | null;
};
type Conversation = {
  id: string;
  mode: string;
  controlVersion: number;
  claimedBy: string | null;
  contactBlocked: boolean;
  optOut: { reason: string; sourceEventId: string; createdAt: string } | null;
  handoffReason: string | null;
  summary: string | null;
  summaryStatus: string;
  messages: { id: string; text: string; receivedAt: string }[];
  outboundIntents: { id: string; authorId: string; text: string; status: string;
    readStatus: string; errorCode: string | null }[];
};

export default function HumanQueue({ session }: { session: Session }) {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [selected, setSelected] = useState<Conversation | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [replyText, setReplyText] = useState("");
  const [controlId, setControlId] = useState<string | null>(null);
  const [controlNotice, setControlNotice] = useState("");
  const base = `${apiUrl}/v1/orgs/${session.organizationId}`;
  const headers = { Authorization: `Bearer ${session.token}` };

  const refresh = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const response = await fetch(`${base}/human-queue`, {
        headers: { Authorization: `Bearer ${session.token}` }, cache: "no-store",
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error?.message ?? "Não foi possível consultar a fila.");
      setItems(body);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível consultar a fila.");
    } finally { setLoading(false); }
  }, [base, session.token]);

  useEffect(() => { void Promise.resolve().then(refresh); }, [refresh]);

  async function openHistory(conversationId: string) {
    setError(""); setLoading(true);
    try {
      const response = await fetch(`${base}/conversations/${conversationId}`, {
        headers, cache: "no-store",
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error?.message ?? "Não foi possível abrir o histórico.");
      setSelected(body);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível abrir o histórico.");
    } finally { setLoading(false); }
  }

  async function postAction(path: string, body?: object) {
    setError(""); setLoading(true);
    try {
      const response = await fetch(`${base}/${path}`, { method: "POST", headers: {
        ...headers, "Content-Type": "application/json",
      }, body: body ? JSON.stringify(body) : undefined });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error?.message ?? "Não foi possível concluir.");
      if (result.completion === "pending_external_attempt") {
        setControlId(result.controlId);
        setControlNotice("Controle aplicado; envio anterior em verificação.");
      } else if (path.endsWith("/resume-ai")) {
        setControlId(null);
        setControlNotice("Conversa devolvida à IA simulada após nova avaliação.");
      }
      if (selected) await openHistory(selected.id);
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível concluir.");
    } finally { setLoading(false); }
  }

  async function checkControl() {
    if (!controlId) return;
    try {
      const response = await fetch(`${base}/controls/${controlId}`, { headers, cache: "no-store" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error?.message ?? "Não foi possível consultar o controle.");
      if (result.completion === "pending_external_attempt") {
        setControlNotice("Controle aplicado; envio anterior em verificação.");
      } else {
        setControlId(null);
        setControlNotice(result.completion === "unknown"
          ? "Envio anterior incerto. Verifique o canal; esta intenção não será reenviada."
          : result.priorAccepted ? "Envio anterior aceito pelo canal antes do controle."
            : "Controle concluído sem envio anterior aceito.");
      }
      if (selected) await openHistory(selected.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível consultar o controle.");
    }
  }

  async function sendReply(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    await postAction(`conversations/${selected.id}/messages`, {
      version: selected.controlVersion, commandId: crypto.randomUUID(), text: replyText,
    });
    setReplyText("");
  }

  return <section className="operation" aria-labelledby="human-queue-title">
    <h2 id="human-queue-title">Fila de atendimento humano</h2>
    <p>Pedidos de atendimento humano e respostas pelo canal simulado.</p>
    <button type="button" onClick={() => void refresh()} disabled={loading}>Atualizar fila</button>
    {error && <p className="error" role="alert">{error}</p>}
    {controlNotice && <p role="status">{controlNotice}</p>}
    {controlId && <button type="button" onClick={() => void checkControl()}>Verificar envio anterior</button>}
    {!loading && items.length === 0 && !error && <p>Nenhum pedido pendente.</p>}
    {items.length > 0 && <ul className="human-queue-list">{items.map((item) => <li key={item.id}>
      <strong>{item.leadName || "Contato sem nome"}</strong>
      <p>Motivo: {item.reason === "opt_out" ? "pedido para parar mensagens automáticas"
        : "pedido explícito de atendimento humano"}.</p>
      <p>Próxima ação: {item.nextAction}</p>
      <p>{item.assignedSellerId ? "Vendedor atribuído" : "Sem vendedor atribuído"} ·
        {item.claimedBy ? " Atendimento assumido" : " Aguardando assunção"}</p>
      <button type="button" onClick={() => void openHistory(item.conversationId)} disabled={loading}>
        Ver histórico de {item.leadName || "contato sem nome"}
      </button>
    </li>)}</ul>}
    {selected && <div className="human-history" aria-live="polite">
      <h3>Histórico de atendimento</h3>
      <p>Modo: {selected.mode === "awaiting_human" ? "aguardando humano" : selected.mode}</p>
      <p>Resumo: {selected.summaryStatus === "ready" && selected.summary
        ? selected.summary : "indisponível; consulte as mensagens abaixo"}</p>
      {selected.optOut ? <p role="status">Opt-out ativo neste canal: pedido para parar mensagens
        automáticas. Origem: evento {selected.optOut.sourceEventId}. Recebido em
        {" "}{new Date(selected.optOut.createdAt).toLocaleString("pt-BR")}. Nova mensagem não reautoriza
        a automação; atender manualmente.</p>
        : selected.contactBlocked && <p>Contato bloqueado nesta conversa.</p>}
      <ol>{selected.messages.map((message) => <li key={message.id}>{message.text}</li>)}</ol>
      {!selected.claimedBy && <button type="button" disabled={loading}
        onClick={() => void postAction(`conversations/${selected.id}/claim`,
          { version: selected.controlVersion })}>Assumir conversa</button>}
      {selected.mode === "human" && <form onSubmit={(event) => void sendReply(event)}>
        <label>Resposta manual<textarea value={replyText} maxLength={4096} required
          onChange={(event) => setReplyText(event.target.value)} /></label>
        <button disabled={loading || !replyText.trim()}>Registrar resposta</button>
      </form>}
      {selected.mode === "human" && <button type="button"
        disabled={loading || selected.contactBlocked || selected.optOut !== null}
        onClick={() => void postAction(`conversations/${selected.id}/resume-ai`,
          { version: selected.controlVersion })}>Retomar IA simulada</button>}
      <h4>Respostas manuais</h4>
      <ol>{selected.outboundIntents.map((intent) => <li key={intent.id}>
        <p>{intent.text}</p>
        <p>Autor: {intent.authorId} · Envio: {intent.status} · Leitura: não confirmada</p>
        {intent.status === "unknown" && <p>Envio incerto. Verifique o canal antes de nova ação; esta intenção não será reenviada.</p>}
        {intent.status === "pending" && <button type="button" disabled={loading}
          onClick={() => void postAction(`test-dispatch/${intent.id}`)}>Processar envio simulado</button>}
      </li>)}</ol>
    </div>}
  </section>;
}
