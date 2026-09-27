"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowRight, Ban, Bot, Headset, Inbox, MessageSquare, RefreshCw, Send, UserCheck } from "lucide-react";
import { Badge, EmptyState, Notice, initials } from "./components/ui";
import { apiUrl } from "./lib/api";
import { deliveryLabel, modeLabel } from "./lib/labels";
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

  return <section className="card queue" aria-labelledby="human-queue-title">
    <div className="card-header">
      <div><h2 id="human-queue-title"><Headset size={18} aria-hidden="true" />Fila de atendimento humano</h2>
        <p className="muted small">Pedidos de atendimento humano e respostas pelo canal simulado.</p></div>
      <div className="button-row">
        {controlId && <button type="button" className="btn btn-sm btn-secondary"
          onClick={() => void checkControl()}>Verificar envio anterior</button>}
        <button type="button" className="btn btn-sm btn-ghost" onClick={() => void refresh()} disabled={loading}>
          <RefreshCw size={14} aria-hidden="true" className={loading ? "spin" : undefined} />Atualizar fila</button>
      </div>
    </div>
    {error && <Notice tone="error">{error}</Notice>}
    {controlNotice && <Notice tone="info">{controlNotice}</Notice>}
    <div className="queue-panes">
      <div className="queue-list">
        {!loading && items.length === 0 && !error && <EmptyState icon={<Inbox size={22} />} title="Nenhum pedido pendente.">
          Quando um lead pedir para falar com uma pessoa, ele aparece aqui.</EmptyState>}
        {items.length > 0 && <ul className="entity-list">{items.map((item) => {
          const name = item.leadName || "Contato sem nome";
          return <li key={item.id} className={selected?.id === item.conversationId ? "queue-item selected" : "queue-item"}>
            <div className="queue-item-head">
              <span className="avatar avatar-sm">{initials(name)}</span>
              <strong>{name}</strong>
              <Badge tone={item.reason === "opt_out" ? "danger" : "warning"}>
                {item.reason === "opt_out" ? "Opt-out" : "Pediu humano"}</Badge>
            </div>
            <p>Motivo: {item.reason === "opt_out" ? "pedido para parar mensagens automáticas"
              : "pedido explícito de atendimento humano"}.</p>
            <p className="queue-next"><ArrowRight size={14} aria-hidden="true" />Próxima ação: {item.nextAction}</p>
            <div className="badge-row">
              <Badge tone={item.assignedSellerId ? "success" : "neutral"}>
                {item.assignedSellerId ? "Vendedor atribuído" : "Sem vendedor atribuído"}</Badge>
              <Badge tone={item.claimedBy ? "success" : "warning"}>
                {item.claimedBy ? "Atendimento assumido" : "Aguardando assunção"}</Badge>
            </div>
            <button type="button" className="btn btn-sm btn-secondary" disabled={loading}
              onClick={() => void openHistory(item.conversationId)} aria-label={`Ver histórico de ${name}`}>
              Abrir conversa</button>
          </li>;
        })}</ul>}
      </div>
      <div className="queue-detail">
        {!selected ? <EmptyState icon={<MessageSquare size={22} />} title="Selecione uma conversa">
          O histórico, o resumo e as ações de atendimento aparecem aqui.</EmptyState>
          : <div className="human-history" aria-live="polite">
            <div className="card-header card-header-sub"><h3>Histórico de atendimento</h3>
              <Badge tone={selected.mode === "human" ? "success" : selected.mode === "awaiting_human" ? "warning" : "info"}>
                Modo: {modeLabel(selected.mode)}</Badge></div>
            <p className="summary"><strong>Resumo:</strong> {selected.summaryStatus === "ready" && selected.summary
              ? selected.summary : "indisponível; consulte as mensagens abaixo"}</p>
            {selected.optOut ? <div className="notice notice-error"><Ban size={18} aria-hidden="true" />
              <p role="status">Opt-out ativo neste canal: pedido para parar mensagens
                automáticas. Origem: evento {selected.optOut.sourceEventId}. Recebido em
                {" "}{new Date(selected.optOut.createdAt).toLocaleString("pt-BR")}. Nova mensagem não reautoriza
                a automação; atender manualmente.</p></div>
              : selected.contactBlocked && <Notice tone="info">Contato bloqueado nesta conversa.</Notice>}
            <ol className="chat-list">{selected.messages.map((message) => <li key={message.id} className="bubble bubble-in">
              <span className="bubble-author">Lead · {new Date(message.receivedAt).toLocaleString("pt-BR")}</span>
              {message.text}</li>)}
              {selected.outboundIntents.map((intent) => <li key={intent.id} className="bubble bubble-out">
                <span className="bubble-author">Resposta manual</span>
                <p>{intent.text}</p>
                <small>Autor: {intent.authorId} · Envio: {deliveryLabel(intent.status)} · Leitura: não confirmada</small>
                {intent.status === "unknown" && <small className="bubble-warning">Envio incerto. Verifique o canal antes
                  de nova ação; esta intenção não será reenviada.</small>}
                {intent.status === "pending" && <button type="button" className="btn btn-sm btn-secondary" disabled={loading}
                  onClick={() => void postAction(`test-dispatch/${intent.id}`)}>Processar envio simulado</button>}
              </li>)}</ol>
            <div className="button-row">
              {!selected.claimedBy && <button type="button" className="btn" disabled={loading}
                onClick={() => void postAction(`conversations/${selected.id}/claim`,
                  { version: selected.controlVersion })}><UserCheck size={16} aria-hidden="true" />Assumir conversa</button>}
              {selected.mode === "human" && <button type="button" className="btn btn-ghost"
                disabled={loading || selected.contactBlocked || selected.optOut !== null}
                onClick={() => void postAction(`conversations/${selected.id}/resume-ai`,
                  { version: selected.controlVersion })}><Bot size={16} aria-hidden="true" />Retomar IA simulada</button>}
            </div>
            {selected.mode === "human" && <form onSubmit={(event) => void sendReply(event)} className="reply-box">
              <label>Resposta manual<textarea value={replyText} maxLength={4096} required rows={3}
                placeholder="Escreva sua resposta ao lead…" onChange={(event) => setReplyText(event.target.value)} /></label>
              <button className="btn" disabled={loading || !replyText.trim()}>
                <Send size={16} aria-hidden="true" />Registrar resposta</button>
            </form>}
          </div>}
      </div>
    </div>
  </section>;
}
