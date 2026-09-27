export const authUrl = process.env.NEXT_PUBLIC_AUTH_URL ?? "http://127.0.0.1:54321";
export const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export type Role = "gestor" | "vendedor";
export type Session = { token: string; organizationId: string; role?: Role;
  organizationName?: string; email?: string };
export type Membership = { id: string; name: string; role: Role };
export type Operation = { id: string; name: string; role: string; automation_enabled: boolean;
  automation_paused: boolean; simulation_enabled: boolean; automation_epoch: number;
  agent: { active: boolean } };

const sessionKey = "leadflow-session";
const flashKey = "leadflow-flash";

export async function responseBody(response: Response) {
  const body = await response.json();
  if (!response.ok) throw new Error(body.error?.message ?? body.msg ?? "Não foi possível concluir.");
  return body;
}

export function readSession(): Session | null {
  const stored = sessionStorage.getItem(sessionKey);
  if (!stored) return null;
  try { return JSON.parse(stored) as Session; }
  catch { sessionStorage.removeItem(sessionKey); return null; }
}

export function storeSession(session: Session) {
  sessionStorage.setItem(sessionKey, JSON.stringify(session));
}

export function clearSession() { sessionStorage.removeItem(sessionKey); }

/** Message shown once on the next screen, e.g. why the session ended. */
export function setFlash(message: string) { sessionStorage.setItem(flashKey, message); }

export function takeFlash() {
  const message = sessionStorage.getItem(flashKey) ?? "";
  sessionStorage.removeItem(flashKey);
  return message;
}

export function formatPrice(price: string | null) {
  if (price === null) return "não informado";
  return Number(price).toLocaleString("pt-BR", { style: "currency", currency: "BRL",
    minimumFractionDigits: 2, maximumFractionDigits: 4 });
}
