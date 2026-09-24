import { expect, test } from "@playwright/test";

test.use({ launchOptions: { channel: "msedge" } });

test("gestor vê controle aplicado enquanto envio simulado termina", async ({ page, request }) => {
  const suffix = crypto.randomUUID();
  await page.goto("http://127.0.0.1:3000");
  await page.getByLabel("E-mail").fill(`control-${suffix}@example.test`);
  await page.getByLabel("Senha").fill(`Synthetic-${suffix}!`);
  await page.getByLabel("Nome da empresa").fill("Alfa controle sintético");
  await page.getByRole("button", { name: "Criar operação", exact: true }).last().click();
  await page.getByRole("button", { name: "Habilitar simulação local" }).click();
  await expect(page.getByText("Simulação local: habilitada", { exact: false })).toBeVisible();

  const session = await page.evaluate(() => JSON.parse(sessionStorage.getItem("leadflow-session")!));
  const base = `http://127.0.0.1:8000/v1/orgs/${session.organizationId}`;
  const auth = { Authorization: `Bearer ${session.token}` };
  const channelResponse = await request.post(`${base}/test-channels`, {
    headers: auth, data: { kind: "telegram" },
  });
  expect(channelResponse.status()).toBe(201);
  const channel = await channelResponse.json();
  const inbound = await request.post(`http://127.0.0.1:8000/v1/test-channels/${channel.id}/events`, {
    headers: { "X-Test-Channel-Token": channel.token }, data: {
      schemaVersion: 1, eventType: "message", externalEventId: crypto.randomUUID(),
      externalMessageId: crypto.randomUUID(), externalChatId: "chat-ui",
      externalUserId: "lead-ui", occurredAt: new Date().toISOString(),
      providerSequence: null, contactName: "Ana", content: { kind: "text", text: "Olá" },
    },
  });
  expect(inbound.status()).toBe(200);
  const conversation = (await inbound.json()).conversationId;
  const prepared = await request.post(`${base}/conversations/${conversation}/test-auto-intents`, {
    headers: auth, data: { commandId: crypto.randomUUID(), text: "Resposta sintética" },
  });
  expect(prepared.status()).toBe(202);
  const intent = (await prepared.json()).intentId;

  const sending = request.post(`${base}/test-dispatch/${intent}`, {
    headers: { ...auth, "X-Test-Dispatch-Delay-Ms": "1000" },
  });
  await expect.poll(async () => {
    const history = await request.get(`${base}/conversations/${conversation}`, { headers: auth });
    return (await history.json()).outboundIntents[0].status;
  }).toBe("dispatching");
  await page.getByRole("button", { name: "Pausar automação" }).click();
  await expect(page.getByText("Controle aplicado; envio anterior em verificação.")).toBeVisible();
  expect((await sending).status()).toBe(200);
  await page.getByRole("button", { name: "Verificar envio anterior" }).click();
  await expect(page.getByText("Controle concluído; um envio anterior já foi aceito pelo canal.")).toBeVisible();
});
