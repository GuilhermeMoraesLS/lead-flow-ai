"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthLayout } from "../components/auth-layout";
import { Notice } from "../components/ui";
import { apiUrl, authUrl, Operation, readSession, responseBody, storeSession } from "../lib/api";

export default function SignUp() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  useEffect(() => {
    void Promise.resolve().then(() => { if (readSession()) router.replace("/app"); });
  }, [router]);

  async function register(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setPending(true);
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "");
    const credentials = JSON.stringify({ email, password: form.get("password") });
    try {
      let auth = await fetch(authUrl + "/signup", { method: "POST",
        headers: { "Content-Type": "application/json" }, body: credentials });
      if (auth.status === 422) {
        const signupError = await auth.clone().json();
        if (signupError.error_code === "user_already_exists") {
          auth = await fetch(authUrl + "/token?grant_type=password", { method: "POST",
            headers: { "Content-Type": "application/json" }, body: credentials });
        }
      }
      const authBody = await responseBody(auth);
      const created = await fetch(apiUrl + "/v1/organizations", { method: "POST",
        headers: { "Content-Type": "application/json", Authorization: "Bearer " + authBody.access_token,
          "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify({ name: form.get("organization") }) });
      const operation = await responseBody(created) as Operation;
      storeSession({ token: authBody.access_token, email, organizationId: operation.id,
        organizationName: operation.name, role: "gestor" });
      router.push("/app");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível concluir.");
    } finally { setPending(false); }
  }

  return <AuthLayout title="Crie sua operação comercial" subtitle="Leva um minuto. Depois, uma jornada guiada ajuda a colocar seu agente no ar."
    footer={<>Já tem uma conta? <Link href="/entrar">Entrar</Link></>}>
    <form onSubmit={register} className="form-stack">
      <label>Nome da empresa<input name="organization" required maxLength={120} autoComplete="organization"
        placeholder="Ex.: Clínica Alfa" /></label>
      <label>E-mail<input name="email" type="email" autoComplete="email" required placeholder="voce@empresa.com.br" /></label>
      <label>Senha<input name="password" type="password" autoComplete="new-password" minLength={8} required
        aria-describedby="password-hint" /></label>
      <small id="password-hint" className="field-hint">Mínimo de 8 caracteres.</small>
      <button className="btn btn-block btn-lg" disabled={pending}>{pending ? "Criando sua operação…" : "Criar conta"}</button>
    </form>
    {error && <Notice tone="error">{error}</Notice>}
  </AuthLayout>;
}
