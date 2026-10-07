"use client";

import KnowledgeBase from "../../knowledge";
import { PageHeader } from "../../components/ui";
import { useWorkspace } from "../../lib/workspace";

export default function KnowledgePage() {
  const { session } = useWorkspace();
  return <>
    <PageHeader eyebrow="Configuração" title="Documentos"
      description="Materiais de apoio do agente. Só documentos prontos podem ser usados como fonte." />
    <KnowledgeBase session={session} />
  </>;
}
