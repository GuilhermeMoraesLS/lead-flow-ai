"use client";

import { useState } from "react";
import { FlaskConical, Pause, Play, Power, ShieldCheck } from "lucide-react";
import { Badge, Notice, PageHeader } from "../../components/ui";
import { apiUrl, responseBody } from "../../lib/api";
import { useWorkspace } from "../../lib/workspace";

export default function AutomationPage() {
  const { session, operation, reloadOperation } = useWorkspace();
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState(false);
  const [controlId, setControlId] = useState<string | null>(null);
  const base = `${apiUrl}/v1/orgs/${session.organizationId}`;
  const headers = { Authorization: "Bearer " + session.token };

  async function changeAutomation(action: "pause" | "resume" | "test-automation/enable") {
    setError(""); setNotice(""); setPending(true);
    try {
      const response = await fetch(`${base}/${action === "test-automation/enable" ? action : `automation/${action}`}`,
        { method: "POST", headers });
      const body = await responseBody(response);
      await reloadOperation();
      if (body.completion === "pending_external_attempt") {
        setControlId(body.controlId);
        setNotice("Controle aplicado; envio anterior em verificação.");
      } else {
        setControlId(null);
        setNotice(action === "pause" ? "Pausa aplicada. Novos envios automáticos bloqueados."
          : action === "resume" ? "Controle global reativado; conversas humanas continuam sob controle humano."
            : "Simulação local habilitada; a ativação real continua pendente.");
      }
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Não foi possível alterar o controle."); }
    finally { setPending(false); }
  }

  async function checkControl() {
    if (!controlId) return;
    try {
      const body = await responseBody(await fetch(`${base}/controls/${controlId}`, { headers, cache: "no-store" }));
      if (body.completion === "pending_external_attempt") {
        setNotice("Controle aplicado; envio anterior em verificação.");
      } else {
        setControlId(null);
        setNotice(body.completion === "unknown"
          ? "Controle aplicado; resultado anterior incerto. Verifique o canal antes de nova ação."
          : body.priorAccepted ? "Controle concluído; um envio anterior já foi aceito pelo canal."
            : "Controle concluído; nenhum envio anterior foi aceito.");
      }
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Não foi possível consultar o controle."); }
  }

  if (!operation) return null;
  const paused = operation.automation_paused;

  return <>
    <PageHeader eyebrow="Operação" title="Automação"
      description="Controles de segurança para interromper ou retomar os envios automáticos a qualquer momento." />
    {notice && <Notice tone="info">{notice}</Notice>}
    {error && <Notice tone="error">{error}</Notice>}
    <div className="grid-2">
      <section className={paused ? "card control-card control-paused" : "card control-card"}>
        <div className="card-header"><h2>{paused ? <Pause size={18} aria-hidden="true" /> : <Power size={18} aria-hidden="true" />}
          Controle global</h2>
          <Badge tone={paused ? "warning" : "success"}>{paused ? "Pausa aplicada" : "Envios liberados"}</Badge></div>
        <p className="muted">{paused
          ? "Novos envios automáticos estão bloqueados. Conversas em atendimento humano continuam sob controle humano."
          : "Use a pausa para bloquear imediatamente novos envios automáticos em todos os canais."}</p>
        <p className="kv">Pausa global: <strong>{paused ? "aplicada" : "não aplicada"}</strong></p>
        <div className="button-row">
          <button type="button" className="btn btn-warning" disabled={pending}
            onClick={() => void changeAutomation("pause")}><Pause size={16} aria-hidden="true" />Pausar automação</button>
          {paused && <button type="button" className="btn btn-secondary" disabled={pending}
            onClick={() => void changeAutomation("resume")}><Play size={16} aria-hidden="true" />Reativar controle global</button>}
          {controlId && <button type="button" className="btn btn-ghost"
            onClick={() => void checkControl()}>Verificar envio anterior</button>}
        </div>
      </section>
      <section className="card">
        <div className="card-header"><h2><FlaskConical size={18} aria-hidden="true" />Ambiente de testes</h2>
          <Badge tone={operation.simulation_enabled ? "info" : "neutral"}>
            {operation.simulation_enabled ? "Habilitada" : "Desabilitada"}</Badge></div>
        <p className="muted">A simulação local permite testar o fluxo de respostas sem enviar mensagens reais.</p>
        <p className="kv">Agente real: <strong>{operation.agent.active ? "ativo" : "inativo"}</strong></p>
        <p className="kv">Simulação local: <strong>{operation.simulation_enabled ? "habilitada" : "desabilitada"}</strong></p>
        {!operation.simulation_enabled && <button type="button" className="btn btn-secondary" disabled={pending}
          onClick={() => void changeAutomation("test-automation/enable")}>Habilitar simulação local</button>}
      </section>
    </div>
    <p className="muted small footnote"><ShieldCheck size={14} aria-hidden="true" />Cada controle é registrado; envios
      já em andamento são verificados antes de qualquer nova ação.</p>
  </>;
}
