import type { ReactNode } from "react";
import { MessageSquare, PackageCheck, ShieldCheck, UserCheck } from "lucide-react";
import { Logo } from "./ui";

const highlights = [
  { icon: MessageSquare, title: "Primeiro atendimento sem espera",
    text: "Seu agente SDR responde os leads no Telegram com a identidade da sua empresa." },
  { icon: PackageCheck, title: "Respostas apoiadas no seu catálogo",
    text: "Preço e disponibilidade vêm dos produtos cadastrados. O que não está no catálogo não é inventado." },
  { icon: UserCheck, title: "Seu time assume quando importa",
    text: "Pedidos de atendimento humano chegam à fila com o histórico da conversa." },
];

export function AuthLayout({ title, subtitle, children, footer }: {
  title: string; subtitle: string; children: ReactNode; footer: ReactNode;
}) {
  return <div className="auth">
    <aside className="auth-brand">
      <Logo inverted />
      <div className="auth-pitch">
        <span className="eyebrow eyebrow-inverted">Agente SDR com IA</span>
        <h2>Transforme cada conversa em uma oportunidade de venda.</h2>
        <ul className="auth-highlights">{highlights.map(({ icon: Icon, title: heading, text }) =>
          <li key={heading}><span className="auth-highlight-icon"><Icon size={18} aria-hidden="true" /></span>
            <div><strong>{heading}</strong><p>{text}</p></div></li>)}</ul>
      </div>
      <p className="auth-trust"><ShieldCheck size={16} aria-hidden="true" />
        Dados, produtos e conversas separados por empresa.</p>
    </aside>
    <main className="auth-panel">
      <div className="auth-card">
        <div className="auth-mobile-logo"><Logo /></div>
        <h1>{title}</h1>
        <p className="auth-subtitle">{subtitle}</p>
        {children}
        <div className="auth-footer">{footer}</div>
      </div>
    </main>
  </div>;
}
