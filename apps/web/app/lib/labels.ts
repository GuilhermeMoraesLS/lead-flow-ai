import type { Tone } from "../components/ui";

const delivery: Record<string, string> = {
  accepted: "Entregue ao canal", pending: "Pendente", dispatching: "Enviando", unknown: "Envio incerto",
  rejected: "Recusado pelo canal", cancelled: "Cancelado", failed: "Falhou", ready: "Aguardando processamento",
  processing: "Processando", processed: "Processado", running: "Processando", handoff: "Encaminhado a humano",
};

export function deliveryLabel(status: string) { return delivery[status] ?? status; }

export function deliveryTone(status: string): Tone {
  return status === "accepted" || status === "processed" ? "success"
    : status === "failed" || status === "rejected" ? "danger"
      : status === "unknown" || status === "handoff" ? "warning" : "neutral";
}

const modes: Record<string, string> = { automatic: "IA", awaiting_human: "Aguardando humano", human: "Humano" };

export function modeLabel(mode: string) { return modes[mode] ?? mode; }
