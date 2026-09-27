"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight, Bot, Building, CircleCheck, Headset, Package, Rocket, Send, ShieldCheck, Trophy, Users, Zap,
} from "lucide-react";
import { Badge, PageHeader } from "./ui";
import { apiUrl } from "../lib/api";
import { useWorkspace } from "../lib/workspace";

type Snapshot = {
  agentConfigured: boolean | null;
  availableProducts: number | null;
  sellers: number | null;
  availableSellers: number | null;
  telegramConnected: boolean | null;
  telegramBot: string | null;
  d0Enabled: boolean | null;
  queue: number | null;
  blockers: number | null;
};

const emptySnapshot: Snapshot = { agentConfigured: null, availableProducts: null, sellers: null,
  availableSellers: null, telegramConnected: null, telegramBot: null, d0Enabled: null, queue: null, blockers: null };

export default function Dashboard() {
  const { session, operation, expire } = useWorkspace();
  const [snapshot, setSnapshot] = useState<Snapshot>(emptySnapshot);
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async () => {
    const base = `${apiUrl}/v1/orgs/${session.organizationId}`;
    const get = async (path: string) => {
      const response = await fetch(base + path, { headers: { Authorization: "Bearer " + session.token }, cache: "no-store" });
      if (response.status === 401) throw new Error("expired");
      if (!response.ok) throw new Error("failed");
      return response.json();
    };
    const [config, catalog, sellers, telegram, d0, queue, readiness] = await Promise.allSettled([
      get("/agent-config"), get("/products"), get("/sellers"), get("/telegram"), get("/telegram/d0"),
      get("/human-queue"), get("/agent/readiness"),
    ]);
    if ([config, catalog, sellers, telegram, d0, queue, readiness]
      .some((result) => result.status === "rejected" && result.reason?.message === "expired")) {
      expire("Sessão expirada. Entre novamente para continuar."); return;
    }
    const value = <T,>(result: PromiseSettledResult<T>) => result.status === "fulfilled" ? result.value : null;
    const configValue = value(config); const catalogValue = value(catalog); const sellerList = value(sellers);
    const telegramValue = value(telegram); const queueValue = value(queue);
    setSnapshot({
      agentConfigured: configValue ? Boolean(configValue.name && configValue.identity && configValue.instructions) : null,
      availableProducts: catalogValue ? catalogValue.products.filter((product: { available: boolean }) => product.available).length : null,
      sellers: sellerList ? sellerList.length : null,
      availableSellers: sellerList ? sellerList.filter((seller: { active: boolean; available: boolean }) =>
        seller.active && seller.available).length : null,
      telegramConnected: telegramValue ? Boolean(telegramValue.connected) : null,
      telegramBot: telegramValue?.botUsername ?? null,
      d0Enabled: value(d0)?.enabled ?? null,
      queue: queueValue ? queueValue.length : null,
      blockers: value(readiness)?.blockers.length ?? null,
    });
    setLoaded(true);
  }, [session.organizationId, session.token, expire]);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  const steps = [
    { title: "Crie sua conta e empresa", text: "Sua operação comercial foi criada.", done: true,
      href: "/app", icon: Building, cta: "" },
    { title: "Dê identidade ao seu agente", text: "Nome, apresentação e instruções de atendimento.",
      done: snapshot.agentConfigured === true, href: "/app/agente", icon: Bot, cta: "Configurar agente" },
    { title: "Cadastre seus produtos", text: "O catálogo é a fonte de preço e disponibilidade das respostas.",
      done: (snapshot.availableProducts ?? 0) > 0, href: "/app/produtos", icon: Package, cta: "Cadastrar produtos" },
    { title: "Monte sua equipe de vendas", text: "Vendedores recebem os leads que pedem atendimento humano.",
      done: (snapshot.sellers ?? 0) > 0, href: "/app/vendedores", icon: Users, cta: "Adicionar vendedores" },
    { title: "Conecte o Telegram", text: "Crie e vincule o bot que vai atender seus leads.",
      done: snapshot.telegramConnected === true, href: "/app/canais/telegram", icon: Send, cta: "Conectar Telegram" },
    { title: "Coloque o agente para atender", text: "Ative o atendimento automático no bot conectado.",
      done: snapshot.d0Enabled === true, href: "/app/canais/telegram", icon: Rocket, cta: "Ativar atendimento" },
  ];
  const completed = steps.filter((step) => step.done).length;
  const percent = Math.round((completed / steps.length) * 100);
  const next = steps.find((step) => !step.done);
  const count = (value: number | null) => loaded ? value ?? "—" : "…";

  return <>
    <PageHeader eyebrow="Visão geral" title={`Olá, ${operation?.name ?? "sua operação"}`}
      description="Acompanhe a configuração do seu agente SDR e o que está acontecendo na operação." />

    <section className="card journey" aria-labelledby="journey-title">
      <div className="journey-summary">
        <div className="progress-ring" style={{ "--progress": `${percent * 3.6}deg` } as React.CSSProperties}
          role="img" aria-label={`${percent}% da jornada concluída`}>
          <span>{loaded ? `${percent}%` : "…"}</span>
        </div>
        <div>
          <span className="eyebrow">Jornada de ativação</span>
          <h2 id="journey-title">{!loaded ? "Carregando sua jornada…" : next
            ? `${completed} de ${steps.length} etapas concluídas` : "Sua operação está no ar"}</h2>
          <p>{!loaded ? "" : next ? <>Próximo passo: <strong>{next.title.toLowerCase()}</strong>.</>
            : "Seu agente está pronto para atender no Telegram. Acompanhe as conversas e a fila humana."}</p>
          {loaded && next && next.cta && <Link href={next.href} className="btn">{next.cta}<ArrowRight size={16} aria-hidden="true" /></Link>}
        </div>
      </div>
      {loaded && !next && <div className="celebration"><Trophy size={20} aria-hidden="true" />
        Jornada concluída! Todas as etapas de ativação foram cumpridas.</div>}
      <ol className="journey-steps">{steps.map((step, index) => {
        const Icon = step.icon;
        const current = step === next;
        return <li key={step.title} className={step.done ? "step done" : current ? "step current" : "step"}>
          <span className="step-marker" aria-hidden="true">
            {step.done ? <CircleCheck size={20} /> : <Icon size={18} />}</span>
          <div className="step-body">
            <strong>{index + 1}. {step.title}</strong>
            <span>{step.text}</span>
          </div>
          {step.done ? <Badge tone="success">Concluído</Badge>
            : current ? <Link href={step.href} className="btn btn-sm">{step.cta}</Link>
              : <Link href={step.href} className="btn btn-sm btn-ghost">Abrir</Link>}
        </li>;
      })}</ol>
    </section>

    <div className="kpi-grid">
      <Link href="/app/produtos" className="kpi">
        <span className="kpi-icon kpi-blue"><Package size={20} aria-hidden="true" /></span>
        <span className="kpi-label">Produtos disponíveis</span>
        <strong className="kpi-value">{count(snapshot.availableProducts)}</strong>
      </Link>
      <Link href="/app/vendedores" className="kpi">
        <span className="kpi-icon kpi-green"><Users size={20} aria-hidden="true" /></span>
        <span className="kpi-label">Vendedores disponíveis</span>
        <strong className="kpi-value">{count(snapshot.availableSellers)}
          {snapshot.sellers !== null && <small> de {snapshot.sellers}</small>}</strong>
      </Link>
      <Link href="/app/atendimento" className="kpi">
        <span className="kpi-icon kpi-amber"><Headset size={20} aria-hidden="true" /></span>
        <span className="kpi-label">Pedidos na fila humana</span>
        <strong className="kpi-value">{count(snapshot.queue)}</strong>
      </Link>
      <Link href="/app/canais/telegram" className="kpi">
        <span className="kpi-icon kpi-violet"><Send size={20} aria-hidden="true" /></span>
        <span className="kpi-label">Canal Telegram</span>
        <strong className="kpi-value kpi-text">{!loaded ? "…" : snapshot.telegramConnected
          ? `@${snapshot.telegramBot}` : "Não conectado"}</strong>
      </Link>
    </div>

    <div className="grid-2">
      <section className="card">
        <div className="card-header"><h2><Zap size={18} aria-hidden="true" />Atendimento automático</h2></div>
        <dl className="status-list">
          <div><dt>Atendimento no Telegram</dt><dd>{snapshot.d0Enabled
            ? <Badge tone="success"><span className="dot dot-live" />Ativo</Badge> : <Badge>Desativado</Badge>}</dd></div>
          <div><dt>Automação global</dt><dd>{operation?.automation_paused
            ? <Badge tone="warning">Pausada</Badge> : <Badge tone="success">Liberada</Badge>}</dd></div>
          <div><dt>Simulação local</dt><dd>{operation?.simulation_enabled
            ? <Badge tone="info">Habilitada</Badge> : <Badge>Desabilitada</Badge>}</dd></div>
        </dl>
        <Link href="/app/automacao" className="card-link">Gerenciar automação<ArrowRight size={14} aria-hidden="true" /></Link>
      </section>
      <section className="card">
        <div className="card-header"><h2><ShieldCheck size={18} aria-hidden="true" />Ativação completa do agente</h2></div>
        <p className="muted">A demonstração no Telegram é liberada pela jornada acima. A ativação completa do agente
          depende de requisitos adicionais, acompanhados na prontidão.</p>
        <dl className="status-list">
          <div><dt>Agente</dt><dd>{operation?.agent.active ? <Badge tone="success">Ativo</Badge> : <Badge>Inativo</Badge>}</dd></div>
          <div><dt>Pendências de prontidão</dt><dd>{snapshot.blockers === null ? "—"
            : <Badge tone={snapshot.blockers ? "warning" : "success"}>{snapshot.blockers}</Badge>}</dd></div>
        </dl>
        <Link href="/app/agente" className="card-link">Ver prontidão<ArrowRight size={14} aria-hidden="true" /></Link>
      </section>
    </div>
  </>;
}
