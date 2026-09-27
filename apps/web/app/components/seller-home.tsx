"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { KeyRound, UserCheck } from "lucide-react";
import HumanQueue from "../human-queue";
import { Badge, Notice, PageHeader } from "./ui";
import { apiUrl, responseBody } from "../lib/api";
import { useWorkspace } from "../lib/workspace";

type SellerEligibility = { eligible: boolean; active: boolean; available: boolean };

export default function SellerHome() {
  const { session, expire } = useWorkspace();
  const [eligibility, setEligibility] = useState<SellerEligibility | null>(null);
  const [passwordRequired, setPasswordRequired] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState(false);
  const base = `${apiUrl}/v1/orgs/${session.organizationId}/sellers/me`;

  const load = useCallback(async () => {
    const response = await fetch(base + "/eligibility",
      { headers: { Authorization: "Bearer " + session.token }, cache: "no-store" });
    const body = await response.json();
    if (response.status === 403 && body.error?.code === "PASSWORD_CHANGE_REQUIRED") {
      setPasswordRequired(true); setEligibility(null);
    } else if (response.ok) {
      setPasswordRequired(false); setEligibility(body);
    } else expire(body.error?.message ?? "Vínculo não encontrado.");
  }, [base, session.token, expire]);

  useEffect(() => {
    void Promise.resolve().then(load).catch(() => setError("Não foi possível consultar seu acesso."));
  }, [load]);

  async function changePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setPending(true);
    const form = new FormData(event.currentTarget);
    try {
      await responseBody(await fetch(base + "/password", { method: "POST",
        headers: { "Content-Type": "application/json", Authorization: "Bearer " + session.token },
        body: JSON.stringify({ current_password: form.get("currentPassword"), new_password: form.get("newPassword") }) }));
      await load();
      setNotice("Senha alterada.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Não foi possível trocar a senha."); }
    finally { setPending(false); }
  }

  if (passwordRequired) return <>
    <PageHeader eyebrow="Primeiro acesso" title="Proteja sua conta"
      description="A senha inicial foi gerada pelo seu gestor. Defina uma senha pessoal para continuar." />
    <section className="card card-narrow">
      <div className="card-header"><h2><KeyRound size={18} aria-hidden="true" />Trocar senha inicial</h2></div>
      <form onSubmit={changePassword} className="form-stack">
        <label>Senha inicial<input name="currentPassword" type="password" autoComplete="current-password" required /></label>
        <label>Nova senha<input name="newPassword" type="password" autoComplete="new-password" minLength={12} required
          aria-describedby="new-password-hint" /></label>
        <small id="new-password-hint" className="field-hint">Mínimo de 12 caracteres, diferente da senha inicial.</small>
        <button className="btn" disabled={pending}>{pending ? "Salvando…" : "Trocar senha"}</button>
      </form>
      {error && <Notice tone="error">{error}</Notice>}
    </section>
  </>;

  return <>
    <PageHeader eyebrow="Área do vendedor" title="Meu atendimento"
      description="Acompanhe os leads que pediram atendimento humano e responda pelo canal." />
    {eligibility && <section className="card seller-status">
      <span className="kpi-icon kpi-green"><UserCheck size={20} aria-hidden="true" /></span>
      <div><strong>{eligibility.eligible ? "Elegível para atendimento" : "Indisponível para atendimento"}</strong>
        <p className="muted">Sua disponibilidade é definida pelo gestor da operação.</p></div>
      <div className="badge-row">
        <Badge tone={eligibility.active ? "success" : "neutral"}>{eligibility.active ? "Vínculo ativo" : "Vínculo inativo"}</Badge>
        <Badge tone={eligibility.available ? "success" : "warning"}>{eligibility.available ? "Disponível" : "Indisponível"}</Badge>
      </div>
    </section>}
    {notice && <Notice tone="success">{notice}</Notice>}
    {error && <Notice tone="error">{error}</Notice>}
    {eligibility && <HumanQueue session={session} />}
  </>;
}
