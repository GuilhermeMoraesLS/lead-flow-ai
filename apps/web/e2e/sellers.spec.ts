import { expect, test } from "@playwright/test";

test.use({ launchOptions: { channel: "msedge" } });

test("gestor cadastra e habilita vendedor, que troca a senha antes do acesso", async ({ page, browser }) => {
  const suffix = crypto.randomUUID();
  const sellerEmail = `vendedor-${suffix}@example.test`;
  await page.goto("http://127.0.0.1:3000/cadastro");
  await page.getByLabel("E-mail").fill(`gestor-${suffix}@example.test`);
  await page.getByLabel("Senha").fill(`Synthetic-${suffix}!`);
  await page.getByLabel("Nome da empresa").fill("Alfa sintética");
  await page.getByRole("button", { name: "Criar conta" }).click();
  await page.getByRole("link", { name: "Vendedores", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Vendedores" })).toBeVisible();

  await page.getByLabel("Nome do vendedor").fill("Bia");
  await page.getByLabel("E-mail do vendedor").fill(sellerEmail);
  await page.getByLabel("Telefone do vendedor").fill("+5511999990000");
  await page.getByLabel("Disponível para atendimento").check();
  await page.getByRole("button", { name: "Cadastrar vendedor" }).click();
  await expect(page.getByText("Bia", { exact: true })).toBeVisible();
  await expect(page.getByRole("status")).toContainText("Vendedor cadastrado sem acesso.");
  await page.getByRole("button", { name: "Habilitar Bia" }).click();
  const temporaryPassword = await page.getByTestId("temporary-password").textContent();
  expect(temporaryPassword).toBeTruthy();

  const sellerContext = await browser.newContext();
  const sellerPage = await sellerContext.newPage();
  await sellerPage.goto("http://127.0.0.1:3000");
  await sellerPage.getByLabel("E-mail", { exact: true }).fill(sellerEmail);
  await sellerPage.getByLabel("Senha", { exact: true }).fill(temporaryPassword!);
  await sellerPage.getByRole("button", { name: "Entrar" }).click();
  await expect(sellerPage.getByRole("heading", { name: "Trocar senha inicial" })).toBeVisible();
  await sellerPage.getByLabel("Senha inicial").fill(temporaryPassword!);
  await sellerPage.getByLabel("Nova senha").fill("NovaSenhaSintetica-2026!");
  await sellerPage.getByRole("button", { name: "Trocar senha" }).click();
  await expect(sellerPage.getByText("Elegível para atendimento")).toBeVisible();

  await page.getByRole("button", { name: "Revogar Bia" }).click();
  await sellerPage.reload();
  await expect(sellerPage.locator("p.error[role=alert]")).toContainText("Vínculo não encontrado");
  await sellerContext.close();
});
