import type { ReactNode } from "react";
import { CircleAlert, CircleCheck, Info } from "lucide-react";

export function Logo({ inverted = false }: { inverted?: boolean }) {
  return <span className={inverted ? "logo logo-inverted" : "logo"}>
    <svg viewBox="0 0 32 32" width="32" height="32" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="url(#logo-gradient)" />
      <path d="M8 21.5 13.5 16l4 4L24 12.5" fill="none" stroke="#fff" strokeWidth="2.6"
        strokeLinecap="round" strokeLinejoin="round" />
      <path d="M19.5 12.5H24V17" fill="none" stroke="#fff" strokeWidth="2.6"
        strokeLinecap="round" strokeLinejoin="round" />
      <defs><linearGradient id="logo-gradient" x1="0" y1="0" x2="32" y2="32">
        <stop stopColor="#2563EB" /><stop offset="1" stopColor="#10B981" />
      </linearGradient></defs>
    </svg>
    <span className="logo-text">LeadFlow <strong>AI</strong></span>
  </span>;
}

export function PageHeader({ eyebrow, title, description, actions }: {
  eyebrow?: string; title: string; description?: ReactNode; actions?: ReactNode;
}) {
  return <header className="page-header">
    <div>
      {eyebrow && <span className="eyebrow">{eyebrow}</span>}
      <h1>{title}</h1>
      {description && <p className="page-description">{description}</p>}
    </div>
    {actions && <div className="page-actions">{actions}</div>}
  </header>;
}

export type Tone = "neutral" | "success" | "warning" | "danger" | "info";

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

/** Inline feedback. Success/info use role=status; errors use role=alert. */
export function Notice({ tone, children, className = "" }: {
  tone: "success" | "info" | "error"; children: ReactNode; className?: string;
}) {
  const Icon = tone === "error" ? CircleAlert : tone === "success" ? CircleCheck : Info;
  return <div className={`notice notice-${tone}`}>
    <Icon size={18} aria-hidden="true" />
    <p className={`${tone === "error" ? "error" : ""} ${className}`.trim()}
      role={tone === "error" ? "alert" : "status"}>{children}</p>
  </div>;
}

export function EmptyState({ icon, title, children }: { icon: ReactNode; title: string; children?: ReactNode }) {
  return <div className="empty-state">
    <span className="empty-icon" aria-hidden="true">{icon}</span>
    <strong>{title}</strong>
    {children && <p>{children}</p>}
  </div>;
}

export function initials(name: string) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]!.toUpperCase()).join("");
}
