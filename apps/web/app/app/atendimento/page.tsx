"use client";

import HumanQueue from "../../human-queue";
import { PageHeader } from "../../components/ui";
import { useWorkspace } from "../../lib/workspace";

export default function QueuePage() {
  const { session } = useWorkspace();
  return <>
    <PageHeader eyebrow="Operação" title="Atendimento humano"
      description="Leads que pediram para falar com uma pessoa ou para interromper mensagens automáticas." />
    <HumanQueue session={session} />
  </>;
}
