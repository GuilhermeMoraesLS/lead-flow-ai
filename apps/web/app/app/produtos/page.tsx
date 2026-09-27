"use client";

import Products from "../../products";
import { PageHeader } from "../../components/ui";
import { useWorkspace } from "../../lib/workspace";

export default function ProductsPage() {
  const { session } = useWorkspace();
  return <>
    <PageHeader eyebrow="Configuração" title="Produtos"
      description="O catálogo é a fonte de verdade do agente: preço e disponibilidade vêm daqui." />
    <Products session={session} />
  </>;
}
