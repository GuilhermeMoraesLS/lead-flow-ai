"use client";

import { ReactNode, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Bot, FileText, Headset, LayoutDashboard, LogOut, Menu, MessageCircle, Package, Send, SlidersHorizontal, Users,
  X,
} from "lucide-react";
import { Badge, Logo, initials } from "../components/ui";
import { apiUrl, clearSession, Operation, readSession, Session, setFlash, storeSession } from "../lib/api";
import { WorkspaceContext } from "../lib/workspace";

type NavItem = { href: string; label: string; icon: typeof Bot; soon?: boolean };
const managerNav: { section: string; items: NavItem[] }[] = [
  { section: "Visão geral", items: [{ href: "/app", label: "Início", icon: LayoutDashboard }] },
  { section: "Configuração", items: [
    { href: "/app/agente", label: "Agente de IA", icon: Bot },
    { href: "/app/produtos", label: "Produtos", icon: Package },
    { href: "/app/conhecimento", label: "Documentos", icon: FileText },
    { href: "/app/vendedores", label: "Vendedores", icon: Users },
  ] },
  { section: "Canais", items: [
    { href: "/app/canais/telegram", label: "Telegram", icon: Send },
    { href: "#", label: "WhatsApp", icon: MessageCircle, soon: true },
  ] },
  { section: "Operação", items: [
    { href: "/app/atendimento", label: "Atendimento humano", icon: Headset },
    { href: "/app/automacao", label: "Automação", icon: SlidersHorizontal },
  ] },
];
const sellerNav = [{ section: "Vendedor", items: [{ href: "/app", label: "Meu atendimento", icon: Headset }] }];

export default function AppShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [session, setSession] = useState<Session | null>(null);
  const [operation, setOperation] = useState<Operation | null>(null);
  const [loadError, setLoadError] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);

  const expire = useCallback((message: string) => {
    clearSession(); setFlash(message); router.replace("/entrar");
  }, [router]);

  const signOut = useCallback(() => { clearSession(); router.replace("/entrar"); }, [router]);

  const loadOperation = useCallback(async (current: Session) => {
    setLoadError("");
    try {
      const response = await fetch(`${apiUrl}/v1/orgs/${current.organizationId}`,
        { headers: { Authorization: "Bearer " + current.token }, cache: "no-store" });
      const body = await response.json();
      if (response.status === 401) { expire("Sessão expirada. Entre novamente para continuar."); return; }
      if (!response.ok) { expire(body.error?.message ?? "Operação não encontrada."); return; }
      setOperation(body as Operation);
      if (current.organizationName !== body.name) storeSession({ ...current, organizationName: body.name });
    } catch { setLoadError("Não foi possível conectar à API. Verifique sua conexão e tente novamente."); }
  }, [expire]);

  useEffect(() => {
    void Promise.resolve().then(async () => {
      const current = readSession();
      if (!current) { router.replace("/entrar"); return; }
      setSession(current);
      if (current.role !== "vendedor") await loadOperation(current);
    });
  }, [router, loadOperation]);

  useEffect(() => {
    if (session?.role === "vendedor" && pathname !== "/app") router.replace("/app");
  }, [session?.role, pathname, router]);

  useEffect(() => { void Promise.resolve().then(() => setMenuOpen(false)); }, [pathname]);

  if (loadError && session) return <div className="boot"><div className="boot-card">
    <strong>Não foi possível carregar sua operação</strong><p>{loadError}</p>
    <button type="button" className="btn" onClick={() => void loadOperation(session)}>Tentar novamente</button>
  </div></div>;
  const seller = session?.role === "vendedor";
  if (!session || (!seller && !operation)) return <div className="boot" aria-busy="true"><span className="spinner" /></div>;

  const navigation = seller ? sellerNav : managerNav;
  const organizationName = operation?.name ?? session.organizationName ?? "Sua empresa";
  const reloadOperation = () => loadOperation(session);

  return <WorkspaceContext.Provider value={{ session, operation, reloadOperation, expire, signOut }}>
    <div className={menuOpen ? "shell menu-open" : "shell"}>
      <aside className="sidebar" aria-label="Navegação principal">
        <div className="sidebar-top">
          <Logo inverted />
          <button type="button" className="icon-button sidebar-close" aria-label="Fechar menu"
            onClick={() => setMenuOpen(false)}><X size={20} /></button>
        </div>
        <nav>{navigation.map((group) => <div key={group.section} className="nav-group">
          <span className="nav-section">{group.section}</span>
          {group.items.map((item) => {
            const Icon = item.icon;
            if ("soon" in item && item.soon) return <span key={item.label} className="nav-link nav-link-soon"
              aria-disabled="true"><Icon size={18} aria-hidden="true" />{item.label}<em>Em breve</em></span>;
            const active = item.href === "/app" ? pathname === "/app" : pathname.startsWith(item.href);
            return <Link key={item.href} href={item.href} className={active ? "nav-link active" : "nav-link"}
              aria-current={active ? "page" : undefined}><Icon size={18} aria-hidden="true" />{item.label}</Link>;
          })}
        </div>)}</nav>
        <div className="sidebar-footer">
          <div className="org-card">
            <span className="avatar avatar-sm">{initials(organizationName)}</span>
            <div><strong>{organizationName}</strong>
              <small>{seller ? "Vendedor" : "Gestor"}{session.email ? ` · ${session.email}` : ""}</small></div>
          </div>
          <button type="button" className="nav-link sign-out" onClick={signOut}>
            <LogOut size={18} aria-hidden="true" />Sair</button>
        </div>
      </aside>
      <div className="sidebar-backdrop" onClick={() => setMenuOpen(false)} aria-hidden="true" />
      <div className="workspace">
        <header className="topbar">
          <button type="button" className="icon-button menu-toggle" aria-label="Abrir menu"
            onClick={() => setMenuOpen(true)}><Menu size={20} /></button>
          <span className="topbar-org">{organizationName}</span>
          {operation && <div className="topbar-status">
            {operation.automation_paused && <Badge tone="warning">Automação pausada</Badge>}
            {operation.simulation_enabled && <Badge tone="info">Simulação local</Badge>}
          </div>}
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  </WorkspaceContext.Provider>;
}
