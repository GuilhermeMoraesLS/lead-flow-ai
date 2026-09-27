import { expect, test } from "@playwright/test";

test.use({ launchOptions: { channel: "msedge" } });

test("gestor ativa D0 e abre histórico Telegram", async ({ page, request }) => {
  const suffix = crypto.randomUUID();
  const email = `telegram-d0-${suffix}@example.test`;
  const password = `Synthetic-${suffix}!`;
  expect((await request.post("http://127.0.0.1:54321/signup", {
    data: { email, password },
  })).ok()).toBeTruthy();
  let activated = false;
  await page.route("**/v1/orgs/*/telegram", (route) => route.fulfill({
    json: { status: "connected", botUsername: "SyntheticBot",
      failureCode: null, connected: true },
  }));
  await page.route("**/v1/orgs/*/telegram/d0", (route) => {
    if (route.request().method() === "POST") activated = true;
    return route.fulfill({ json: { enabled: activated } });
  });
  await page.route("**/v1/orgs/*/telegram/d0/conversations", (route) => route.fulfill({
    json: [{ batchId: "batch-1", conversationId: "conversation-1", status: "processed",
      deliveryStatus: "accepted", errorCode: null, createdAt: "2026-09-26T12:00:00Z" }],
  }));
  await page.route("**/v1/orgs/*/conversations/conversation-1", (route) => route.fulfill({
    json: { messages: [{ id: "in-1", text: "Quanto custa a Consulta?" }],
      outboundIntents: [{ id: "out-1", text: "R$ 0,00", status: "accepted" }] },
  }));

  await page.goto("http://127.0.0.1:3000/cadastro");
  await page.getByLabel("E-mail").fill(email);
  await page.getByLabel("Senha").fill(password);
  await page.getByLabel("Nome da empresa").fill("D0 sintética");
  await page.getByRole("button", { name: "Criar conta" }).click();
  await page.getByRole("link", { name: "Telegram", exact: true }).click();
  await expect(page.getByRole("button", { name: "Ativar atendimento D0" })).toBeVisible();
  await page.getByRole("button", { name: "Ativar atendimento D0" }).click();
  await expect(page.getByText("Ativada para esta empresa.")).toBeVisible();
  await page.getByRole("button", { name: "Ver histórico" }).click();
  const chat = page.getByRole("listitem");
  await expect(chat.filter({ hasText: "Lead" })).toContainText("Quanto custa a Consulta?");
  await expect(chat.filter({ hasText: "Agente · Entregue ao canal" })).toContainText("R$ 0,00");
});
