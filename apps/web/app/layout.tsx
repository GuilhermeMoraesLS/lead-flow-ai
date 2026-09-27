import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "LeadFlow AI", description: "Agente SDR com IA para sua operação comercial" };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="pt-BR"><body>{children}</body></html>;
}
