"use client";

import { FormEvent, useEffect, useState } from "react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
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

  return <section className="operation"><h2>Produtos</h2>
    <p>Cadastre produtos da empresa. Deixe o preço vazio quando for desconhecido.</p>
    <form onSubmit={save} className="inline-form" key={editing ? `${editing.id}-${editing.version}` : "new"}>
      <label>Nome do produto<input name="name" defaultValue={editing?.name ?? ""} required maxLength={120} /></label>
      <label>Preço decimal<input name="price" defaultValue={editing?.price ?? ""} inputMode="decimal"
        pattern="(0|[1-9][0-9]{0,15})(\.[0-9]{1,4})?" title="Use ponto decimal e até quatro casas." /></label>
      <label className="checkbox"><input name="available" type="checkbox"
        defaultChecked={editing?.available ?? true} />Disponível</label>
      {editing && <p>Editando revisão {editing.version} de {editing.name}.</p>}
      <button disabled={pending}>{pending ? "Salvando…" : editing ? "Salvar correção" : "Cadastrar produto"}</button>
      {editing && <button type="button" disabled={pending} onClick={() => setEditing(null)}>Cancelar edição</button>}
    </form>
    <p>Revisão comercial {catalog?.commercialRevision ?? "…"}</p>
    {catalog && catalog.products.length === 0 && <p>Nenhum produto cadastrado.</p>}
    {catalog && catalog.products.length > 0 && <ul className="seller-list">{catalog.products.map((product) =>
      <li key={product.id}><strong>{product.name}</strong> · Preço: {product.price ?? "desconhecido"}
        {" · "}{product.available ? "Disponível" : "Indisponível"}
        {" · "}Versão {product.version}
        <br /><button type="button" disabled={pending} onClick={() => setEditing(product)}>
          Corrigir {product.name}</button>
        <button type="button" disabled={pending} onClick={() => void revoke(product)}>
          Remover {product.name}</button>
      </li>)}</ul>}
    {notice && <p role="status">{notice}</p>}
    {error && <p className="error" role="alert">{error}</p>}
  </section>;
}
