"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Check, CircleAlert, CircleCheck, ExternalLink, Info, LoaderCircle, MessageSquare, RefreshCw, Rocket, Send, Zap,
} from "lucide-react";
import { Badge, EmptyState, Notice } from "./components/ui";
import { apiUrl } from "./lib/api";
import { deliveryLabel, deliveryTone } from "./lib/labels";

type Session = { token: string; organizationId: string };
type TelegramStatus = {
  status: "not_started" | "awaiting_owner" | "awaiting_bot" | "configuring" | "connected" | "failed";
  botUsername: string | null;
  failureCode: string | null;
  connected: boolean;
  link?: string | null;
};
type Batch = { batchId: string; conversationId: string | null; status: string;
  deliveryStatus: string | null; errorCode: string | null; createdAt: string;
  model: string | null; promptVersion: string | null;
  commercialRevision: number | null; estimatedCostUsd: string | null };
type History = { messages: { id: string; text: string }[];
  outboundIntents: { id: string; text: string; status: string }[] };

export default function TelegramOnboarding({ session }: { session: Session }) {
  const [state, setState] = useState<TelegramStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [d0Enabled, setD0Enabled] = useState(false);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [history, setHistory] = useState<History | null>(null);
  const endpoint = `${apiUrl}/v1/orgs/${session.organizationId}/telegram`;
  const headers = { Authorization: `Bearer ${session.token}` };

  const refresh = useCallback(async () => {
    const authHeaders = { Authorization: `Bearer ${session.token}` };
    const [response, activation, recent] = await Promise.all([
      fetch(endpoint, { headers: authHeaders }), fetch(endpoint + "/d0", { headers: authHeaders }),
      fetch(endpoint + "/d0/conversations", { headers: authHeaders }),
    ]);
    if (!response.ok || !activation.ok || !recent.ok)
      throw new Error("Não foi possível consultar o Telegram.");
    setState(await response.json() as TelegramStatus);
    setD0Enabled((await activation.json() as { enabled: boolean }).enabled);
    setBatches(await recent.json() as Batch[]);
  }, [endpoint, session.token]);

  useEffect(() => {
    void Promise.resolve().then(refresh).catch(() => setError("Não foi possível consultar o Telegram."));
  }, [refresh]);

  useEffect(() => {
    if (state?.status !== "awaiting_owner" && state?.status !== "awaiting_bot"
      && state?.status !== "configuring") return;
    const timer = window.setInterval(() => {
      void fetch(endpoint, { headers: { Authorization: `Bearer ${session.token}` },
        cache: "no-store" }).then(async (response) => {
        if (response.ok) setState(await response.json() as TelegramStatus);
      }).catch(() => setError("Não foi possível atualizar o estado do Telegram."));
    }, 3000);
    return () => window.clearInterval(timer);
  }, [endpoint, session.token, state?.status]);

  async function submit(resume: boolean) {
    setBusy(true); setError("");
    try {
      const response = await fetch(endpoint + (resume ? "/resume" : ""),
        { method: "POST", headers });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error?.message ?? "Não foi possível iniciar o vínculo.");
      setState(body as TelegramStatus);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível iniciar o vínculo.");
    } finally { setBusy(false); }
  }

  async function activateD0() {
    setBusy(true); setError("");
    try {
      const response = await fetch(endpoint + "/d0", { method: "POST", headers });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error?.message ?? "Não foi possível ativar D0.");
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível ativar D0.");
    } finally { setBusy(false); }
  }

  async function openHistory(conversationId: string) {
    setError("");
    try {
      const response = await fetch(`${apiUrl}/v1/orgs/${session.organizationId}/conversations/${conversationId}`,
        { headers });
      if (!response.ok) throw new Error("Não foi possível abrir o histórico.");
      setHistory(await response.json() as History);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível abrir o histórico.");
    }
  }

  const failed = state?.status === "failed";
  const current = state ? stepIndex[state.status] : -1;

  return <>
    {error && <Notice tone="error">{error}</Notice>}
    <section className="card" aria-labelledby="telegram-heading">
      <div className="card-header"><h2 id="telegram-heading"><Send size={18} aria-hidden="true" />Bot Telegram da sua empresa</h2>
        {state && <Badge tone={state.connected ? "success" : failed ? "danger" : current > 0 ? "info" : "neutral"}>
          {state.connected ? "Conectado" : failed ? "Falha na conexão" : current > 0 ? "Conectando" : "Não conectado"}</Badge>}</div>
      <p className="muted">Inicie a conexão aqui. A criação precisa ser confirmada no Telegram com a sua conta de teste.</p>
      <ol className="stepper">{connectionSteps.map((step, index) => <li key={step}
        className={state?.connected || index < current ? "done" : index === current && !failed ? "current" : ""}>
        <span className="stepper-marker">{state?.connected || index < current
          ? <Check size={14} aria-hidden="true" /> : index + 1}</span><span>{step}</span></li>)}</ol>
      <div className={failed ? "connection-status connection-failed" : state?.connected
        ? "connection-status connection-ok" : "connection-status"}>
        {state?.connected ? <CircleCheck size={18} aria-hidden="true" /> : failed
          ? <CircleAlert size={18} aria-hidden="true" /> : current > 0
            ? <LoaderCircle size={18} className="spin" aria-hidden="true" /> : <Info size={18} aria-hidden="true" />}
        <p role="status">{state?.connected ? `Conectado: @${state.botUsername}` :
          state?.status === "awaiting_owner" ? "Abra o bot gestor no Telegram e toque em Iniciar. O próximo passo aparecerá aqui automaticamente." :
          state?.status === "awaiting_bot" ? "Crie e confirme o bot no Telegram. A conexão aparecerá aqui automaticamente." :
          state?.status === "configuring" ? "Verificando o webhook." :
          state?.status === "failed" && state.failureCode === "bot_already_connected" ?
            "Este bot já está vinculado a outra empresa. Crie outro bot no Telegram para esta operação." :
          state?.status === "failed" ? "Não foi possível confirmar o bot ou o webhook. Verifique a conexão e tente retomar." :
          state ? "Bot ainda não conectado." : "Consultando o Telegram…"}</p>
      </div>
      <div className="button-row">
        {state?.link && <a className="btn" href={state.link} target="_blank" rel="noopener noreferrer">
          {state.status === "awaiting_bot" ? "Criar bot no Telegram" : "Abrir bot gestor no Telegram"}
          <ExternalLink size={14} aria-hidden="true" /></a>}
        {state?.status === "not_started" && <button type="button" className="btn" disabled={busy}
          onClick={() => void submit(false)}>Iniciar conexão</button>}
        {state?.status === "failed" && <button type="button" className="btn" disabled={busy}
          onClick={() => void submit(true)}>Retomar conexão</button>}
        {state && state.status !== "not_started" && <button type="button" className="btn btn-ghost" disabled={busy}
          onClick={() => void refresh().catch(() => setError("Não foi possível atualizar o estado."))}>
          <RefreshCw size={14} aria-hidden="true" />Verificar agora</button>}
      </div>
    </section>

    {state?.connected && <section className="card" aria-labelledby="d0-heading">
      <div className="card-header"><h2 id="d0-heading"><Rocket size={18} aria-hidden="true" />Atendimento automático</h2>
        <Badge tone={d0Enabled ? "success" : "neutral"}>{d0Enabled
          ? <><span className="dot dot-live" />No ar</> : "Desativado"}</Badge></div>
      <div className={d0Enabled ? "activation activation-on" : "activation"}>
        <div><strong>Demonstração D0</strong>
          <p>{d0Enabled ? "Ativada para esta empresa." : "A resposta automática começa após ativação explícita."}</p>
          {!d0Enabled && <small className="muted">Mensagens recebidas antes da ativação não recebem resposta retroativa.</small>}</div>
        {!d0Enabled && <button type="button" className="btn btn-success" disabled={busy} onClick={() => void activateD0()}>
          <Zap size={16} aria-hidden="true" />Ativar atendimento D0</button>}
      </div>
      <div className="card-header card-header-sub"><h3>Conversas recentes</h3>
        <button type="button" className="btn btn-sm btn-ghost" disabled={busy} onClick={() => void refresh()}>
          <RefreshCw size={14} aria-hidden="true" />Atualizar conversas</button></div>
      {batches.length === 0 ? <EmptyState icon={<MessageSquare size={22} />} title="Nenhuma conversa ainda.">
        Envie uma mensagem ao seu bot pelo Telegram e atualize esta lista.</EmptyState>
        : <div className="table-wrap"><table className="table">
          <thead><tr><th>Recebida em</th><th>Entrega</th><th>Modelo</th><th>Catálogo</th><th>Custo estimado</th><th /></tr></thead>
          <tbody>{batches.map((batch) => <tr key={batch.batchId}>
            <td>{new Date(batch.createdAt).toLocaleString("pt-BR")}</td>
            <td><Badge tone={deliveryTone(batch.deliveryStatus ?? batch.status)}>
              {deliveryLabel(batch.deliveryStatus ?? batch.status)}</Badge></td>
            <td>{batch.model ?? "—"}</td>
            <td>{batch.commercialRevision !== null && batch.commercialRevision !== undefined
              ? `rev. ${batch.commercialRevision}` : "—"}</td>
            <td>{batch.estimatedCostUsd ? `US$ ${batch.estimatedCostUsd}` : "—"}</td>
            <td className="cell-action">{batch.conversationId && <button type="button" className="btn btn-sm btn-ghost"
              onClick={() => void openHistory(batch.conversationId!)}>Ver histórico</button>}</td>
          </tr>)}</tbody>
        </table></div>}
      {history && <div className="chat" aria-live="polite"><h3>Histórico de atendimento</h3>
        <ul className="chat-list">{history.messages.map((message) => <li key={message.id} className="bubble bubble-in">
          <span className="bubble-author">Lead</span>{message.text}</li>)}
          {history.outboundIntents.map((intent) => <li key={intent.id} className="bubble bubble-out">
            <span className="bubble-author">Agente · {deliveryLabel(intent.status)}</span>{intent.text}</li>)}</ul></div>}
    </section>}
  </>;
}

const connectionSteps = ["Iniciar conexão", "Abrir o bot gestor", "Criar e confirmar o bot", "Validar webhook"];
const stepIndex: Record<TelegramStatus["status"], number> = {
  not_started: 0, awaiting_owner: 1, awaiting_bot: 2, configuring: 3, connected: 4, failed: 0,
};
