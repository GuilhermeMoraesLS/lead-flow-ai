"use client";

import { FormEvent, useEffect, useState } from "react";
import SellerManager from "./sellers";
import Products from "./products";
import HumanQueue from "./human-queue";

const authUrl = process.env.NEXT_PUBLIC_AUTH_URL ?? "http://127.0.0.1:54321";
const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
type Operation = { id: string; name: string; role: string; automation_enabled: boolean;
  automation_paused: boolean; simulation_enabled: boolean; automation_epoch: number;
  agent: { active: boolean } };
type Configuration = { name: string; identity: string; instructions: string; version: number; active: boolean };
type Check = { code: string; label: string; status: "pending" };
type Readiness = { ready: boolean; blockers: Check[] };
type Session = { token: string; organizationId: string; role?: "gestor" | "vendedor" };
type SellerEligibility = { eligible: boolean; active: boolean; available: boolean };

async function responseBody(response: Response) {
  const body = await response.json();
  if (!response.ok) throw new Error(body.error?.message ?? body.msg ?? "Não foi possível concluir.");
  return body;
}

export default function Home() {
  const [session, setSession] = useState<Session | null>(null);
  const [operation, setOperation] = useState<Operation | null>(null);
  const [configuration, setConfiguration] = useState<Configuration | null>(null);
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [sellerEligibility, setSellerEligibility] = useState<SellerEligibility | null>(null);
  const [sellerPasswordRequired, setSellerPasswordRequired] = useState(false);
  const [mode, setMode] = useState<"create" | "resume" | "seller">("create");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState(false);
  const [controlId, setControlId] = useState<string | null>(null);

  async function load(current: Session) {
    const headers = { Authorization: "Bearer " + current.token };
    const base = `${apiUrl}/v1/orgs/${current.organizationId}`;
    if (current.role === "vendedor") {
      const response = await fetch(base + "/sellers/me/eligibility", { headers });
      const body = await response.json();
      if (response.status === 403 && body.error?.code === "PASSWORD_CHANGE_REQUIRED") {
        setSellerPasswordRequired(true); setSellerEligibility(null);
      } else if (response.ok) {
        setSellerPasswordRequired(false); setSellerEligibility(body);
      } else {
        sessionStorage.removeItem("leadflow-session"); setSession(null);
        throw new Error(body.error?.message ?? "Vínculo não encontrado.");
      }
      setSession(current);
      sessionStorage.setItem("leadflow-session", JSON.stringify(current));
      return;
    }
    const [orgResponse, configResponse, readinessResponse] = await Promise.all([
      fetch(base, { headers }), fetch(base + "/agent-config", { headers }),
      fetch(base + "/agent/readiness", { headers }),
    ]);
    if (orgResponse.status === 401 || configResponse.status === 401) {
      sessionStorage.removeItem("leadflow-session");
      setSession(null); setOperation(null);
      throw new Error("Sessão expirada. Entre novamente para continuar.");
    }
    setOperation(await responseBody(orgResponse));
    setConfiguration(await responseBody(configResponse));
    setReadiness(await responseBody(readinessResponse));
    setSession(current);
    sessionStorage.setItem("leadflow-session", JSON.stringify(current));
  }

  useEffect(() => {
    const stored = sessionStorage.getItem("leadflow-session");
    if (!stored) return;
    try {
      const current = JSON.parse(stored) as Session;
      void Promise.resolve().then(() => load(current))
        .catch((cause) => setError(cause instanceof Error ? cause.message : "Não foi possível retomar."));
    } catch { sessionStorage.removeItem("leadflow-session"); }
  }, []);

  async function authenticate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setPending(true);
    const form = new FormData(event.currentTarget);
    try {
      const email = form.get("email");
      const password = form.get("password");
      const auth = mode === "create"
        ? await fetch(authUrl + "/signup", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) })
        : await fetch(authUrl + "/token?grant_type=password", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) });
      const authBody = await responseBody(auth);
      let organizationId = String(form.get("organizationId") ?? "").trim();
      if (mode === "create") {
        const create = await fetch(apiUrl + "/v1/organizations", { method: "POST",
          headers: { "Content-Type": "application/json", Authorization: "Bearer " + authBody.access_token, "Idempotency-Key": crypto.randomUUID() },
          body: JSON.stringify({ name: form.get("organization") }) });
        organizationId = (await responseBody(create) as Operation).id;
      }
      await load({ token: authBody.access_token, organizationId,
        role: mode === "seller" ? "vendedor" : "gestor" });
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Não foi possível concluir."); }
    finally { setPending(false); }
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session || !configuration) return;
    setError(""); setNotice(""); setPending(true);
    const form = new FormData(event.currentTarget);
    const path = `${apiUrl}/v1/orgs/${session.organizationId}/agent-config`;
    try {
      const response = await fetch(path, { method: "PUT", headers: { "Content-Type": "application/json", Authorization: "Bearer " + session.token },
        body: JSON.stringify({ version: configuration.version, name: form.get("name"), identity: form.get("identity"), instructions: form.get("instructions") }) });
      if (response.status === 409) {
        await load(session);
        setError("Outra sessão alterou a configuração. Os valores atuais foram recarregados; revise antes de salvar.");
        return;
      }
      if (response.status === 401) {
        sessionStorage.removeItem("leadflow-session"); setSession(null); setOperation(null);
        throw new Error("Sessão expirada. Entre novamente para continuar.");
      }
      setConfiguration(await responseBody(response));
      const checkResponse = await fetch(`${apiUrl}/v1/orgs/${session.organizationId}/agent/readiness`,
        { headers: { Authorization: "Bearer " + session.token } });
      setReadiness(await responseBody(checkResponse));
      setNotice("Configuração salva. O agente continua inativo.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Não foi possível salvar."); }
    finally { setPending(false); }
  }

  async function attemptActivation() {
    if (!session) return;
    setError(""); setNotice(""); setPending(true);
    try {
      const response = await fetch(`${apiUrl}/v1/orgs/${session.organizationId}/agent/activate`,
        { method: "POST", headers: { Authorization: "Bearer " + session.token } });
      const body = await response.json();
      if (response.status === 409 && body.error?.code === "AGENT_NOT_READY") {
        setReadiness({ ready: false, blockers: body.blockers });
        setNotice("Ativação recusada. Confira as pendências abaixo; seu progresso foi mantido.");
      } else if (response.status === 401) {
        sessionStorage.removeItem("leadflow-session"); setSession(null); setOperation(null);
        throw new Error("Sessão expirada. Entre novamente para continuar.");
      } else throw new Error(body.error?.message ?? "Não foi possível verificar a ativação.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Não foi possível verificar."); }
    finally { setPending(false); }
  }

  async function changeAutomation(action: "pause" | "resume" | "test-automation/enable") {
    if (!session) return;
    setError(""); setNotice(""); setPending(true);
    try {
      const response = await fetch(`${apiUrl}/v1/orgs/${session.organizationId}/${
        action === "test-automation/enable" ? action : `automation/${action}`}`,
      { method: "POST", headers: { Authorization: "Bearer " + session.token } });
      const body = await responseBody(response);
      await load(session);
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
    if (!session || !controlId) return;
    try {
      const response = await fetch(`${apiUrl}/v1/orgs/${session.organizationId}/controls/${controlId}`,
        { headers: { Authorization: "Bearer " + session.token }, cache: "no-store" });
      const body = await responseBody(response);
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

  async function changeSellerPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session) return;
    setError(""); setPending(true);
    const form = new FormData(event.currentTarget);
    try {
      const response = await fetch(`${apiUrl}/v1/orgs/${session.organizationId}/sellers/me/password`,
        { method: "POST", headers: { "Content-Type": "application/json", Authorization: "Bearer " + session.token },
          body: JSON.stringify({ current_password: form.get("currentPassword"), new_password: form.get("newPassword") }) });
      await responseBody(response);
      await load(session);
      setNotice("Senha alterada.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Não foi possível trocar a senha."); }
    finally { setPending(false); }
  }

  function signOut() {
    sessionStorage.removeItem("leadflow-session");
    setSession(null); setOperation(null); setConfiguration(null); setReadiness(null);
    setSellerEligibility(null); setSellerPasswordRequired(false); setNotice(""); setError("");
    setControlId(null);
    setMode("resume");
  }

  return <main><span className="eyebrow">LeadFlow.IA</span><h1>Configure sua operação comercial.</h1>
    <p>Salve o progresso do agente e acompanhe o que ainda impede a ativação.</p>
    {session && <button type="button" className="sign-out" onClick={signOut}>Sair</button>}
    {session?.role === "vendedor" ? <section className="operation">
      {sellerPasswordRequired ? <><h2>Trocar senha inicial</h2>
        <p>Troque a senha inicial antes de acessar a operação.</p>
        <form onSubmit={changeSellerPassword} className="inline-form">
          <label>Senha inicial<input name="currentPassword" type="password" autoComplete="current-password" required /></label>
          <label>Nova senha<input name="newPassword" type="password" autoComplete="new-password" minLength={12} required /></label>
          <button disabled={pending}>Trocar senha</button>
        </form></> : sellerEligibility ? <><h2>Acesso do vendedor</h2>
        <p>{sellerEligibility.eligible ? "Elegível para atendimento" : "Indisponível para atendimento"}</p>
        <p>Vínculo ativo: {sellerEligibility.active ? "sim" : "não"} · Disponível: {sellerEligibility.available ? "sim" : "não"}</p>
        {session && <HumanQueue session={session} />}</> : null}
      {notice && <p role="status">{notice}</p>}
    </section> : operation && configuration ? <>
      <section className="operation" aria-live="polite"><p><strong>{operation.name}</strong> · {operation.role}</p>
        <p>Agente: {configuration.active ? "ativo" : "inativo"} · Automação: {operation.automation_enabled ? "ativa" : "inativa"}</p>
        <p>ID da organização: {operation.id}</p></section>
      <form onSubmit={save} key={configuration.version}><h2>Identidade do agente</h2>
        <label>Nome<input name="name" defaultValue={configuration.name} maxLength={120} /></label>
        <label>Identidade<textarea name="identity" defaultValue={configuration.identity} maxLength={500} rows={3} /></label>
        <label>Instruções<textarea name="instructions" defaultValue={configuration.instructions} maxLength={10000} rows={7} /></label>
        <p>Revisão {configuration.version}. Salvar não ativa o agente.</p>
        <button disabled={pending}>{pending ? "Salvando…" : "Salvar configuração"}</button>
      </form>
      <section className="operation"><h2>Prontidão</h2><p>Os itens pendentes impedem a ativação.</p>
        <ul>{readiness?.blockers.map((check) => <li key={check.code}>{check.label}: pendente</li>)}</ul>
        <button type="button" onClick={attemptActivation} disabled={pending}>Verificar ativação</button>
      </section>
      <section className="operation"><h2>Controle da automação</h2>
        <p>Agente real: {operation.agent.active ? "ativo" : "inativo"}. Simulação local: {
          operation.simulation_enabled ? "habilitada" : "desabilitada"}. Pausa global: {
          operation.automation_paused ? "aplicada" : "não aplicada"}.</p>
        {!operation.simulation_enabled && <button type="button" disabled={pending}
          onClick={() => void changeAutomation("test-automation/enable")}>Habilitar simulação local</button>}
        <button type="button" disabled={pending} onClick={() => void changeAutomation("pause")}>Pausar automação</button>
        {operation.automation_paused && <button type="button" disabled={pending}
          onClick={() => void changeAutomation("resume")}>Reativar controle global</button>}
        {controlId && <button type="button" onClick={() => void checkControl()}>Verificar envio anterior</button>}
      </section>
      {session && <SellerManager session={session} />}
      {session && <Products session={session} />}
      {session && <HumanQueue session={session} />}
      {notice && <p role="status">{notice}</p>}
    </> : <>
      <div className="mode-buttons"><button type="button" onClick={() => { setMode("create"); setError(""); }} aria-pressed={mode === "create"}>Criar operação</button>
        <button type="button" onClick={() => { setMode("resume"); setError(""); }} aria-pressed={mode === "resume"}>Retomar configuração</button>
        <button type="button" onClick={() => { setMode("seller"); setError(""); }} aria-pressed={mode === "seller"}>Acesso do vendedor</button></div>
      <form onSubmit={authenticate}><h2>{mode === "create" ? "Criar operação" : mode === "seller" ? "Entrar como vendedor" : "Entrar novamente"}</h2>
        <label>E-mail<input name="email" type="email" autoComplete="email" required /></label>
        <label>Senha<input name="password" type="password" autoComplete={mode === "create" ? "new-password" : "current-password"} minLength={8} required /></label>
        {mode === "create" ? <label>Nome da empresa<input name="organization" required maxLength={120} /></label>
          : <label>ID da organização<input name="organizationId" required /></label>}
        <button disabled={pending}>{pending ? "Aguarde…" : mode === "create" ? "Criar operação" : mode === "seller" ? "Entrar como vendedor" : "Retomar"}</button>
      </form>
    </>}
    {error && <p className="error" role="alert">{error}</p>}
  </main>;
}
