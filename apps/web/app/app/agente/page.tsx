"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Bot, CircleDashed, ListChecks } from "lucide-react";
import { Badge, Notice, PageHeader } from "../../components/ui";
import { apiUrl, responseBody } from "../../lib/api";
import { useWorkspace } from "../../lib/workspace";

type Configuration = { name: string; identity: string; instructions: string; version: number; active: boolean };
type Check = { code: string; label: string; status: "pending" };
type Readiness = { ready: boolean; blockers: Check[] };

export default function AgentPage() {
  const { session, expire } = useWorkspace();
  const [configuration, setConfiguration] = useState<Configuration | null>(null);
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState(false);
  const base = `${apiUrl}/v1/orgs/${session.organizationId}`;
  const headers = { Authorization: "Bearer " + session.token };

  const load = useCallback(async () => {
    const authorization = { Authorization: "Bearer " + session.token };
    const [configResponse, readinessResponse] = await Promise.all([
      fetch(base + "/agent-config", { headers: authorization, cache: "no-store" }),
      fetch(base + "/agent/readiness", { headers: authorization, cache: "no-store" }),
    ]);
    if (configResponse.status === 401 || readinessResponse.status === 401) {
      expire("Sessão expirada. Entre novamente para continuar."); return;
    }
    setConfiguration(await responseBody(configResponse));
    setReadiness(await responseBody(readinessResponse));
  }, [base, session.token, expire]);

  useEffect(() => {
    void Promise.resolve().then(load)
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Não foi possível carregar o agente."));
  }, [load]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!configuration) return;
    setError(""); setNotice(""); setPending(true);
    const form = new FormData(event.currentTarget);
    try {
      const response = await fetch(base + "/agent-config", { method: "PUT",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ version: configuration.version, name: form.get("name"),
          identity: form.get("identity"), instructions: form.get("instructions") }) });
      if (response.status === 409) {
        await load();
        setError("Outra sessão alterou a configuração. Os valores atuais foram recarregados; revise antes de salvar.");
        return;
      }
      if (response.status === 401) { expire("Sessão expirada. Entre novamente para continuar."); return; }
      setConfiguration(await responseBody(response));
      setReadiness(await responseBody(await fetch(base + "/agent/readiness", { headers })));
      setNotice("Configuração salva. O agente continua inativo.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Não foi possível salvar."); }
    finally { setPending(false); }
  }

  async function attemptActivation() {
    setError(""); setNotice(""); setPending(true);
    try {
      const response = await fetch(base + "/agent/activate", { method: "POST", headers });
      const body = await response.json();
      if (response.status === 409 && body.error?.code === "AGENT_NOT_READY") {
        setReadiness({ ready: false, blockers: body.blockers });
        setNotice("Ativação recusada. Confira as pendências abaixo; seu progresso foi mantido.");
      } else if (response.status === 401) {
        expire("Sessão expirada. Entre novamente para continuar.");
      } else throw new Error(body.error?.message ?? "Não foi possível verificar a ativação.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Não foi possível verificar."); }
    finally { setPending(false); }
  }

  return <>
    <PageHeader eyebrow="Configuração" title="Agente de IA"
      description="Defina como seu SDR se apresenta e se comporta nas conversas com os leads."
      actions={configuration && <Badge tone={configuration.active ? "success" : "neutral"}>
        Agente: {configuration.active ? "ativo" : "inativo"}</Badge>} />
    {notice && <Notice tone="success">{notice}</Notice>}
    {error && <Notice tone="error">{error}</Notice>}
    <div className="grid-main">
      <section className="card">
        <div className="card-header"><h2><Bot size={18} aria-hidden="true" />Identidade do agente</h2>
          {configuration && <span className="muted small">Revisão {configuration.version}</span>}</div>
        {!configuration ? <div className="skeleton-block" /> :
          <form onSubmit={save} key={configuration.version} className="form-stack">
            <label>Nome<input name="name" defaultValue={configuration.name} maxLength={120}
              placeholder="Ex.: Lia" aria-describedby="name-hint" /></label>
            <small id="name-hint" className="field-hint">Como o agente se apresenta ao lead.</small>
            <label>Identidade<textarea name="identity" defaultValue={configuration.identity} maxLength={500} rows={3}
              placeholder="Ex.: Assistente comercial da Clínica Alfa" aria-describedby="identity-hint" /></label>
            <small id="identity-hint" className="field-hint">Quem o agente representa e qual é o seu papel. Até 500 caracteres.</small>
            <label>Instruções<textarea name="instructions" defaultValue={configuration.instructions} maxLength={10000} rows={8}
              placeholder="Ex.: Atenda em português, seja cordial e objetivo, e encaminhe para um vendedor quando o lead pedir."
              aria-describedby="instructions-hint" /></label>
            <small id="instructions-hint" className="field-hint">Tom de voz, regras e limites do atendimento.</small>
            <div className="form-footer">
              <span className="muted small">Salvar não ativa o agente.</span>
              <button className="btn" disabled={pending}>{pending ? "Salvando…" : "Salvar configuração"}</button>
            </div>
          </form>}
      </section>
      <section className="card">
        <div className="card-header"><h2><ListChecks size={18} aria-hidden="true" />Prontidão</h2></div>
        <p className="muted">Os itens pendentes impedem a ativação completa do agente.</p>
        <ul className="checklist">{readiness?.blockers.map((check) => <li key={check.code}>
          <CircleDashed size={16} aria-hidden="true" /><span>{check.label}: pendente</span></li>)}</ul>
        <button type="button" className="btn btn-secondary btn-block" onClick={() => void attemptActivation()}
          disabled={pending}>Verificar ativação</button>
      </section>
    </div>
  </>;
}
