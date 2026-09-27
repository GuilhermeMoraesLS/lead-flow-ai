import { expect, test } from "@playwright/test";

test.use({ launchOptions: { channel: "msedge" } });

test("conta já cadastrada conclui a organização e inicia o Telegram", async ({ page, request }) => {
  const suffix = crypto.randomUUID();
  const email = `telegram-recovery-${suffix}@example.test`;
  const password = `Synthetic-${suffix}!`;
  const signup = await request.post("http://127.0.0.1:54321/signup", {
    data: { email, password },
  });
  expect(signup.ok()).toBeTruthy();

  await page.goto("http://127.0.0.1:3000/cadastro");
  await page.getByLabel("E-mail").fill(email);
  await page.getByLabel("Senha").fill(password);
  await page.getByLabel("Nome da empresa").fill("Telegram sintética");
  await page.getByRole("button", { name: "Criar conta" }).click();
  await page.getByRole("link", { name: "Telegram", exact: true }).click();

  await expect(page.getByRole("heading", { name: "Bot Telegram da sua empresa" })).toBeVisible();
  await page.getByRole("button", { name: "Iniciar conexão" }).click();
  await expect(page.getByText(/Abra o bot gestor no Telegram e toque em Iniciar/)).toBeVisible();
  await expect(page.getByRole("link", { name: "Abrir bot gestor no Telegram" }))
    .toHaveAttribute("href", /t\.me\/LeadFlowAI_gestor_bot\?start=/);
  await page.reload();
  await expect(page.getByRole("link", { name: "Abrir bot gestor no Telegram" }))
    .toHaveAttribute("href", /t\.me\/LeadFlowAI_gestor_bot\?start=/);
});
