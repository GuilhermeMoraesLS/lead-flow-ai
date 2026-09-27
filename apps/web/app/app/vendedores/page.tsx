"use client";

import SellerManager from "../../sellers";
import { PageHeader } from "../../components/ui";
import { useWorkspace } from "../../lib/workspace";

export default function SellersPage() {
  const { session } = useWorkspace();
  return <>
    <PageHeader eyebrow="Configuração" title="Vendedores"
      description="Sua equipe recebe os leads que pedem atendimento humano, com o histórico da conversa." />
    <SellerManager session={session} />
  </>;
}
