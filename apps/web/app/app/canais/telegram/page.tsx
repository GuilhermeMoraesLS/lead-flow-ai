"use client";

import TelegramOnboarding from "../../../telegram-onboarding";
import { PageHeader } from "../../../components/ui";
import { useWorkspace } from "../../../lib/workspace";

export default function TelegramPage() {
  const { session } = useWorkspace();
  return <>
    <PageHeader eyebrow="Canais" title="Telegram"
      description="Conecte o bot da sua empresa e coloque o agente para atender os leads." />
    <TelegramOnboarding session={session} />
  </>;
}
