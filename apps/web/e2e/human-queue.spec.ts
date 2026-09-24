import { expect, test } from "@playwright/test";

test.use({ launchOptions: { channel: "msedge" } });

test("gestor vê pedido humano e histórico sem resumo", async ({ page }) => {
  const suffix = crypto.randomUUID();
  await page.goto("http://127.0.0.1:3000");
  await page.getByLabel("E-mail").fill(`queue-${suffix}@example.test`);
  await page.getByLabel("Senha").fill(`Synthetic-${suffix}!`);
  await page.getByLabel("Nome da empresa").fill("Alfa fila sintética");
  await page.getByRole("button", { name: "Criar operação", exact: true }).last().click();
  await expect(page.getByRole("heading", { name: "Fila de atendimento humano" })).toBeVisible();

  await page.evaluate(async () => {
    const session = JSON.parse(sessionStorage.getItem("leadflow-session")!);
    const base = `http://127.0.0.1:8000/v1/orgs/${session.organizationId}`;
    const channelResponse = await fetch(`${base}/test-channels`, {
      method: "POST",
      headers: { Authorization: `Bearer ${session.token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ kind: "telegram" }),
    });
    if (!channelResponse.ok) throw new Error("Canal de teste não criado");
    const channel = await channelResponse.json();
    const eventResponse = await fetch(`http://127.0.0.1:8000/v1/test-channels/${channel.id}/events`, {
      method: "POST",
      headers: { "X-Test-Channel-Token": channel.token, "Content-Type": "application/json" },
      body: JSON.stringify({
        schemaVersion: 1, eventType: "message", externalEventId: crypto.randomUUID(),
        externalMessageId: crypto.randomUUID(), externalChatId: "chat-ui",
        externalUserId: "lead-ui", occurredAt: new Date().toISOString(),
        providerSequence: null, contactName: "Ana", content: {
          kind: "text", text: "Quero falar com uma pessoa",
        },
      }),
    });
    if (!eventResponse.ok) throw new Error("Pedido humano não registrado");
  });

  await page.getByRole("button", { name: "Atualizar fila" }).click();
  await expect(page.getByText("Sem vendedor atribuído")).toBeVisible();
  await expect(page.getByText("Atribuir manualmente a vendedor elegível.")).toBeVisible();
  await page.getByRole("button", { name: "Ver histórico de Ana" }).click();
  await expect(page.getByText("Quero falar com uma pessoa")).toBeVisible();
  await expect(page.getByText("indisponível; consulte as mensagens abaixo")).toBeVisible();
  await page.getByRole("button", { name: "Assumir conversa" }).click();
  await expect(page.getByText("Modo: human")).toBeVisible();
  await page.getByLabel("Resposta manual").fill("Olá, vou ajudar.");
  await page.getByRole("button", { name: "Registrar resposta" }).click();
  await expect(page.getByText("Envio: pending")).toBeVisible();
  await page.getByRole("button", { name: "Processar envio simulado" }).click();
  await expect(page.getByText("Envio: accepted")).toBeVisible();
  await expect(page.getByText("Leitura: não confirmada")).toBeVisible();
});
