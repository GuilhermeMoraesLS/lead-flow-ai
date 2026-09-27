"use client";

import { FormEvent, useEffect, useState } from "react";
import { Package, Pencil, Plus, Tag, Trash } from "lucide-react";
import { Badge, EmptyState, Notice } from "./components/ui";
import { apiUrl, formatPrice } from "./lib/api";

type Session = { token: string; organizationId: string };
type Product = { id: string; name: string; price: string | null; available: boolean;
  status: string; version: number; commercialRevision: number };
type Catalog = { commercialRevision: number; products: Product[] };

export default function Products({ session }: { session: Session }) {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [editing, setEditing] = useState<Product | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState(false);
  const base = `${apiUrl}/v1/orgs/${session.organizationId}/products`;

  async function request(path: string, options?: RequestInit) {
    const response = await fetch(path, { ...options, headers: {
      Authorization: "Bearer " + session.token, ...options?.headers,
    } });
    const body = await response.json();
    if (!response.ok) throw new Error(body.error?.message ?? "Não foi possível consultar o catálogo.");
    return body;
  }

  async function reload() { setCatalog(await request(base) as Catalog); }

  useEffect(() => {
    void fetch(base, { headers: { Authorization: "Bearer " + session.token } })
      .then(async (response) => {
        const body = await response.json();
        if (!response.ok) throw new Error(body.error?.message ?? "Não foi possível consultar o catálogo.");
        setCatalog(body as Catalog);
      })
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Não foi possível consultar o catálogo."));
  }, [base, session.token]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setNotice(""); setPending(true);
    const form = event.currentTarget;
    const values = new FormData(form);
    const price = String(values.get("price") ?? "").trim();
    const body = { name: String(values.get("name") ?? ""), price: price === "" ? null : price,
      available: values.get("available") === "on" };
    try {
      await request(editing ? `${base}/${editing.id}` : base, {
        method: editing ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editing ? { ...body, version: editing.version } : body),
      });
      await reload();
      setEditing(null); form.reset();
      setNotice("Produto salvo no catálogo.");
    } catch (cause) {
      if (cause instanceof Error && cause.message.includes("outra sessão")) {
        await reload(); setEditing(null);
        setError("Produto alterado em outra sessão. A lista foi recarregada; revise antes de salvar.");
      } else setError(cause instanceof Error ? cause.message : "Não foi possível salvar.");
    } finally { setPending(false); }
  }

  async function revoke(product: Product) {
    setError(""); setNotice(""); setPending(true);
    try {
      await request(`${base}/${product.id}/revoke`, { method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ version: product.version }),
      });
      await reload(); setEditing(null);
      setNotice("Produto removido do catálogo vigente.");
    } catch (cause) {
      await reload(); setEditing(null);
      setError(cause instanceof Error ? cause.message : "Não foi possível remover o produto.");
    } finally { setPending(false); }
  }

  const available = catalog?.products.filter((product) => product.available).length ?? 0;

  return <>
    {notice && <Notice tone="success">{notice}</Notice>}
    {error && <Notice tone="error">{error}</Notice>}
    <div className="grid-side">
      <section className="card form-card">
        <div className="card-header"><h2>{editing ? <><Pencil size={18} aria-hidden="true" />Editar produto</>
          : <><Plus size={18} aria-hidden="true" />Novo produto</>}</h2></div>
        <form onSubmit={save} className="form-stack" key={editing ? `${editing.id}-${editing.version}` : "new"}>
          <label>Nome do produto<input name="name" defaultValue={editing?.name ?? ""} required maxLength={120}
            placeholder="Ex.: Consulta inicial" /></label>
          <label>Preço (R$)<input name="price" defaultValue={editing?.price ?? ""} inputMode="decimal"
            placeholder="Ex.: 149.90" aria-describedby="price-hint"
            pattern="(0|[1-9][0-9]{0,15})(\.[0-9]{1,4})?" title="Use ponto decimal e até quatro casas." /></label>
          <small id="price-hint" className="field-hint">Use ponto como separador decimal. Deixe vazio se o preço não
            for informado; o agente não inventa valores.</small>
          <label className="switch"><input name="available" type="checkbox"
            defaultChecked={editing?.available ?? true} />Disponível</label>
          {editing && <p className="muted small">Editando revisão {editing.version} de {editing.name}.</p>}
          <div className="button-row">
            <button className="btn" disabled={pending}>{pending ? "Salvando…" : editing ? "Salvar correção" : "Cadastrar produto"}</button>
            {editing && <button type="button" className="btn btn-ghost" disabled={pending}
              onClick={() => setEditing(null)}>Cancelar edição</button>}
          </div>
        </form>
      </section>
      <section className="card">
        <div className="card-header"><h2><Package size={18} aria-hidden="true" />Catálogo vigente</h2>
          <div className="badge-row"><Badge tone="success">{available} disponíveis</Badge>
            <Badge>Revisão comercial {catalog?.commercialRevision ?? "…"}</Badge></div></div>
        {!catalog && <div className="skeleton-block" />}
        {catalog && catalog.products.length === 0 && <EmptyState icon={<Package size={22} />} title="Nenhum produto cadastrado.">
          Cadastre ao menos um produto disponível para o agente responder sobre preço e disponibilidade.</EmptyState>}
        {catalog && catalog.products.length > 0 && <ul className="entity-list">{catalog.products.map((product) =>
          <li key={product.id} className="entity">
            <span className="entity-icon"><Tag size={18} aria-hidden="true" /></span>
            <div className="entity-body">
              <strong>{product.name}</strong>
              <span className="entity-meta">Preço: {formatPrice(product.price)} · Versão {product.version}</span>
            </div>
            <Badge tone={product.available ? "success" : "neutral"}>{product.available ? "Disponível" : "Indisponível"}</Badge>
            <div className="entity-actions">
              <button type="button" className="btn btn-sm btn-ghost" disabled={pending}
                onClick={() => setEditing(product)} aria-label={`Corrigir ${product.name}`}>
                <Pencil size={14} aria-hidden="true" />Editar</button>
              <button type="button" className="btn btn-sm btn-ghost btn-danger" disabled={pending}
                onClick={() => void revoke(product)} aria-label={`Remover ${product.name}`}>
                <Trash size={14} aria-hidden="true" />Remover</button>
            </div>
          </li>)}</ul>}
      </section>
    </div>
  </>;
}
