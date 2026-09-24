"use client";

import { FormEvent, useEffect, useState } from "react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
type Seller = { id: string; name: string; email: string | null; phone: string | null; active: boolean; available: boolean; access: string };
type Session = { token: string; organizationId: string };

export default function SellerManager({ session }: { session: Session }) {
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [temporary, setTemporary] = useState<{ name: string; password: string } | null>(null);
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
    setError(""); setNotice(""); setTemporary(null); setPending(true);
    try { await action(); await reload(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Não foi possível atualizar."); }
    finally { setPending(false); }
  }

  return <section className="operation"><h2>Vendedores</h2>
    <p>Cadastro e disponibilidade não concedem acesso. Habilite somente a pessoa cadastrada.</p>
    <form onSubmit={create} className="inline-form">
      <label>Nome do vendedor<input name="name" required maxLength={120} /></label>
      <label>E-mail do vendedor<input name="email" type="email" required maxLength={254} /></label>
      <label>Telefone do vendedor<input name="phone" type="tel" required pattern="\+[1-9][0-9]{1,14}" placeholder="+5511999990000" /></label>
      <label className="checkbox"><input name="available" type="checkbox" />Disponível para atendimento</label>
      <button disabled={pending}>Cadastrar vendedor</button>
    </form>
    {sellers.length > 0 && <ul className="seller-list">{sellers.map((seller) => <li key={seller.id}>
      <strong>{seller.name}</strong> · {seller.email ?? "E-mail não informado"} · {seller.phone ?? "Telefone não informado"}<br />
      {seller.access === "registered" ? "Cadastrado sem acesso" :
        seller.access === "password_change_required" ? "Troca de senha pendente" :
        seller.access === "revoked" ? "Vínculo revogado" : "Acesso habilitado"}
      {" · "}{seller.active ? "Ativo" : "Inativo"}{" · "}{seller.available ? "Disponível" : "Indisponível"}<br />
      {seller.access === "registered" && <button type="button" disabled={pending}
        onClick={() => void act(async () => {
          const result = await request(`${base}/${seller.id}/enable`, { method: "POST" });
          setTemporary({ name: seller.name, password: result.temporary_password });
        })}>Habilitar {seller.name}</button>}
      {seller.access !== "registered" && seller.access !== "revoked" && <button type="button" disabled={pending}
        onClick={() => void act(async () => {
          await request(`${base}/${seller.id}/revoke`, { method: "POST" });
          setTemporary(null);
        })}>Revogar {seller.name}</button>}
      <button type="button" disabled={pending} onClick={() => void act(async () => {
        await request(`${base}/${seller.id}/availability`, { method: "PUT", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ active: seller.active, available: !seller.available }) });
      })}>{seller.available ? `Marcar ${seller.name} indisponível` : `Marcar ${seller.name} disponível`}</button>
      <button type="button" disabled={pending} onClick={() => void act(async () => {
        await request(`${base}/${seller.id}/availability`, { method: "PUT", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ active: !seller.active, available: seller.available }) });
      })}>{seller.active ? `Desativar ${seller.name}` : `Ativar ${seller.name}`}</button>
    </li>)}</ul>}
    {temporary && <p role="status">Senha inicial de {temporary.name}: <code data-testid="temporary-password">{temporary.password}</code>. Mostrada somente agora ao gestor; entregue por um meio seguro e peça a troca no primeiro acesso.</p>}
    {notice && <p role="status">{notice}</p>}
    {error && <p className="error" role="alert">{error}</p>}
  </section>;
}
