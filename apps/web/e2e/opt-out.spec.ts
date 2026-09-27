import { expect, test } from "@playwright/test";

test.use({ launchOptions: { channel: "msedge" } });

test("gestor vê motivo e origem do opt-out sem reativar automação", async ({ page }) => {
  const suffix = crypto.randomUUID();
  await page.goto("http://127.0.0.1:3000/cadastro");
  await page.getByLabel("E-mail").fill(`opt-out-${suffix}@example.test`);
  await page.getByLabel("Senha").fill(`Synthetic-${suffix}!`);
  await page.getByLabel("Nome da empresa").fill("Alfa opt-out sintético");
  await page.getByRole("button", { name: "Criar conta" }).click();
  await page.getByRole("link", { name: "Atendimento humano", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Fila de atendimento humano" })).toBeVisible();

  await page.evaluate(async () => {
    const session = JSON.parse(sessionStorage.getItem("leadflow-session")!);
    const base = `http://127.0.0.1:8000/v1/orgs/${session.organizationId}`;
    const channelResponse = await fetch(`${base}/test-channels`, {
      method: "POST", headers: {
        Authorization: `Bearer ${session.token}`, "Content-Type": "application/json",
      }, body: JSON.stringify({ kind: "telegram" }),
    });
    if (!channelResponse.ok) throw new Error("Canal de teste não criado");
    const channel = await channelResponse.json();
    const eventResponse = await fetch(`http://127.0.0.1:8000/v1/test-channels/${channel.id}/events`, {
      method: "POST", headers: {
        "X-Test-Channel-Token": channel.token, "Content-Type": "application/json",
      }, body: JSON.stringify({
        schemaVersion: 1, eventType: "message", externalEventId: crypto.randomUUID(),
        externalMessageId: crypto.randomUUID(), externalChatId: "chat-ui",
        externalUserId: "lead-ui", occurredAt: new Date().toISOString(),
        providerSequence: null, contactName: "Ana",
        content: { kind: "text", text: "Pare de me enviar mensagens" },
      }),
    });
    if (!eventResponse.ok) throw new Error("Opt-out não registrado");
  });

  await page.getByRole("button", { name: "Atualizar fila" }).click();
  await expect(page.getByText("Motivo: pedido para parar mensagens automáticas.")).toBeVisible();
  await page.getByRole("button", { name: "Ver histórico de Ana" }).click();
  await expect(page.getByText("Opt-out ativo neste canal", { exact: false })).toBeVisible();
  await expect(page.getByText("Pare de me enviar mensagens")).toBeVisible();
  await page.getByRole("button", { name: "Assumir conversa" }).click();
  await expect(page.getByRole("button", { name: "Retomar IA simulada" })).toBeDisabled();
});
