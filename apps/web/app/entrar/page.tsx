"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Building } from "lucide-react";
import { AuthLayout } from "../components/auth-layout";
import { Badge, Notice } from "../components/ui";
import { apiUrl, authUrl, Membership, readSession, responseBody, storeSession, takeFlash } from "../lib/api";

export default function SignIn() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [choice, setChoice] = useState<{ token: string; email: string; memberships: Membership[] } | null>(null);

  useEffect(() => {
    void Promise.resolve().then(() => {
      if (readSession()) { router.replace("/app"); return; }
      const flash = takeFlash();
      if (flash) setError(flash);
    });
  }, [router]);

  function enter(token: string, email: string, membership: Membership) {
    storeSession({ token, email, organizationId: membership.id, organizationName: membership.name,
      role: membership.role });
    router.push("/app");
  }

  async function authenticate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setPending(true);
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "");
    try {
      const auth = await responseBody(await fetch(authUrl + "/token?grant_type=password", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password: form.get("password") }) }));
      const memberships = await responseBody(await fetch(apiUrl + "/v1/me/organizations",
        { headers: { Authorization: "Bearer " + auth.access_token } })) as Membership[];
      if (memberships.length === 0)
        throw new Error("Vínculo não encontrado. Este acesso não participa de nenhuma empresa ativa.");
      if (memberships.length === 1) enter(auth.access_token, email, memberships[0]!);
      else setChoice({ token: auth.access_token, email, memberships });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível entrar.");
    } finally { setPending(false); }
  }

  if (choice) return <AuthLayout title="Escolha a empresa" subtitle="Seu acesso participa de mais de uma operação."
    footer={<button type="button" className="btn-link" onClick={() => setChoice(null)}>Usar outro acesso</button>}>
    <ul className="org-choices">{choice.memberships.map((membership) => <li key={membership.id}>
      <button type="button" className="org-choice" onClick={() => enter(choice.token, choice.email, membership)}
        aria-label={`Entrar em ${membership.name}`}>
        <span className="org-choice-icon"><Building size={18} aria-hidden="true" /></span>
        <span className="org-choice-name">{membership.name}</span>
        <Badge tone={membership.role === "gestor" ? "info" : "neutral"}>
          {membership.role === "gestor" ? "Gestor" : "Vendedor"}</Badge>
        <ArrowRight size={16} aria-hidden="true" />
      </button></li>)}</ul>
  </AuthLayout>;

  return <AuthLayout title="Entrar na sua conta" subtitle="Gestores e vendedores usam o mesmo acesso."
    footer={<>Ainda não tem uma conta? <Link href="/cadastro">Criar conta</Link></>}>
    <form onSubmit={authenticate} className="form-stack">
      <label>E-mail<input name="email" type="email" autoComplete="email" required placeholder="voce@empresa.com.br" /></label>
      <label>Senha<input name="password" type="password" autoComplete="current-password" minLength={8} required /></label>
      <button className="btn btn-block btn-lg" disabled={pending}>{pending ? "Entrando…" : "Entrar"}</button>
    </form>
    {error && <Notice tone="error">{error}</Notice>}
  </AuthLayout>;
}
