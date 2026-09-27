"use client";

import { FormEvent, useEffect, useState } from "react";
import { Ban, Check, Copy, KeyRound, Lock, UserPlus, Users } from "lucide-react";
import { Badge, EmptyState, Notice, initials } from "./components/ui";
import { apiUrl } from "./lib/api";

type Seller = { id: string; name: string; email: string | null; phone: string | null; active: boolean; available: boolean; access: string };
type Session = { token: string; organizationId: string };

export default function SellerManager({ session }: { session: Session }) {
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [temporary, setTemporary] = useState<{ name: string; password: string } | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState(false);
  const base = `${apiUrl}/v1/orgs/${session.organizationId}/sellers`;
  const headers = { Authorization: "Bearer " + session.token };

  async function request(path: string, options?: RequestInit) {
    const response = await fetch(path, { ...options, headers: { ...headers, ...options?.headers } });
    const body = await response.json();
    if (!response.ok) throw new Error(body.error?.message ?? "Não foi possível concluir.");
    return body;
  }

  async function reload() { setSellers(await request(base)); }
  useEffect(() => {
    void fetch(base, { headers: { Authorization: "Bearer " + session.token } })
      .then(async (response) => {
        const body = await response.json();
        if (!response.ok) throw new Error(body.error?.message ?? "Não foi possível consultar vendedores.");
        setSellers(body);
      })
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Não foi possível consultar vendedores."));
  }, [base, session.token]);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setNotice(""); setTemporary(null); setPending(true);
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      await request(base, { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: form.get("name"), email: form.get("email"), phone: form.get("phone"),
          available: form.get("available") === "on" }) });
      formElement.reset(); await reload();
      setNotice("Vendedor cadastrado sem acesso.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Não foi possível cadastrar."); }
    finally { setPending(false); }
  }

  async function act(action: () => Promise<void>) {
    setError(""); setNotice(""); setTemporary(null); setCopied(false); setPending(true);
    try { await action(); await reload(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Não foi possível atualizar."); }
    finally { setPending(false); }
  }

  const accessBadge = (access: string) => access === "registered" ? <Badge>Cadastrado sem acesso</Badge>
    : access === "password_change_required" ? <Badge tone="warning">Troca de senha pendente</Badge>
      : access === "revoked" ? <Badge tone="danger">Vínculo revogado</Badge>
        : <Badge tone="success">Acesso habilitado</Badge>;

  return <>
    {temporary && <div className="secret-card">
      <KeyRound size={20} aria-hidden="true" />
      <div>
        <p role="status">Senha inicial de {temporary.name}: <code data-testid="temporary-password">{temporary.password}</code></p>
        <small>Mostrada somente agora ao gestor. Entregue por um meio seguro e peça a troca no primeiro acesso.</small>
      </div>
      <button type="button" className="btn btn-sm btn-secondary"
        onClick={() => void navigator.clipboard?.writeText(temporary.password).then(() => setCopied(true))}>
        {copied ? <><Check size={14} aria-hidden="true" />Copiada</> : <><Copy size={14} aria-hidden="true" />Copiar senha</>}
      </button>
    </div>}
    {notice && <Notice tone="success">{notice}</Notice>}
    {error && <Notice tone="error">{error}</Notice>}
    <div className="grid-side">
      <section className="card form-card">
        <div className="card-header"><h2><UserPlus size={18} aria-hidden="true" />Novo vendedor</h2></div>
        <form onSubmit={create} className="form-stack">
          <label>Nome do vendedor<input name="name" required maxLength={120} placeholder="Ex.: Bia Souza" /></label>
          <label>E-mail do vendedor<input name="email" type="email" required maxLength={254} placeholder="bia@empresa.com.br" /></label>
          <label>Telefone do vendedor<input name="phone" type="tel" required pattern="\+[1-9][0-9]{1,14}"
            placeholder="+5511999990000" aria-describedby="phone-hint" /></label>
          <small id="phone-hint" className="field-hint">Formato internacional, com + e DDI.</small>
          <label className="switch"><input name="available" type="checkbox" />Disponível para atendimento</label>
          <button className="btn" disabled={pending}>Cadastrar vendedor</button>
        </form>
        <p className="muted small form-note"><Lock size={14} aria-hidden="true" />Cadastro e disponibilidade não concedem
          acesso. Habilite somente a pessoa cadastrada.</p>
      </section>
      <section className="card">
        <div className="card-header"><h2><Users size={18} aria-hidden="true" />Equipe comercial</h2>
          <Badge tone="success">{sellers.filter((seller) => seller.active && seller.available).length} disponíveis</Badge></div>
        {sellers.length === 0 && <EmptyState icon={<Users size={22} />} title="Nenhum vendedor cadastrado.">
          Adicione quem vai assumir os leads que pedirem atendimento humano.</EmptyState>}
        {sellers.length > 0 && <ul className="entity-list">{sellers.map((seller) => <li key={seller.id} className="entity entity-wrap">
          <span className="avatar">{initials(seller.name)}</span>
          <div className="entity-body">
            <strong>{seller.name}</strong>
            <span className="entity-meta">{seller.email ?? "E-mail não informado"} · {seller.phone ?? "Telefone não informado"}</span>
            <div className="badge-row">{accessBadge(seller.access)}
              <Badge tone={seller.active ? "success" : "neutral"}>{seller.active ? "Ativo" : "Inativo"}</Badge>
              <Badge tone={seller.available ? "success" : "neutral"}>{seller.available ? "Disponível" : "Indisponível"}</Badge></div>
          </div>
          <div className="entity-actions">
            {seller.access === "registered" && <button type="button" className="btn btn-sm" disabled={pending}
              aria-label={`Habilitar ${seller.name}`} onClick={() => void act(async () => {
                const result = await request(`${base}/${seller.id}/enable`, { method: "POST" });
                setTemporary({ name: seller.name, password: result.temporary_password });
              })}><KeyRound size={14} aria-hidden="true" />Habilitar acesso</button>}
            <button type="button" className="btn btn-sm btn-ghost" disabled={pending}
              aria-label={seller.available ? `Marcar ${seller.name} indisponível` : `Marcar ${seller.name} disponível`}
              onClick={() => void act(async () => {
                await request(`${base}/${seller.id}/availability`, { method: "PUT", headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ active: seller.active, available: !seller.available }) });
              })}>{seller.available ? "Marcar indisponível" : "Marcar disponível"}</button>
            <button type="button" className="btn btn-sm btn-ghost" disabled={pending}
              aria-label={seller.active ? `Desativar ${seller.name}` : `Ativar ${seller.name}`}
              onClick={() => void act(async () => {
                await request(`${base}/${seller.id}/availability`, { method: "PUT", headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ active: !seller.active, available: seller.available }) });
              })}>{seller.active ? "Desativar" : "Ativar"}</button>
            {seller.access !== "registered" && seller.access !== "revoked" && <button type="button"
              className="btn btn-sm btn-ghost btn-danger" disabled={pending} aria-label={`Revogar ${seller.name}`}
              onClick={() => void act(async () => {
                await request(`${base}/${seller.id}/revoke`, { method: "POST" });
                setTemporary(null);
              })}><Ban size={14} aria-hidden="true" />Revogar acesso</button>}
          </div>
        </li>)}</ul>}
      </section>
    </div>
  </>;
}
