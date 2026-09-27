import { expect, test } from "@playwright/test";

test.use({ launchOptions: { channel: "msedge" } });

test("gestor cadastra e corrige produto no app", async ({ page }) => {
  const suffix = crypto.randomUUID();
  await page.goto("http://127.0.0.1:3000/cadastro");
  await page.getByLabel("E-mail").fill(`catalogo-${suffix}@example.test`);
  await page.getByLabel("Senha").fill(`Synthetic-${suffix}!`);
  await page.getByLabel("Nome da empresa").fill("Alfa sintética");
  await page.getByRole("button", { name: "Criar conta" }).click();
  await page.getByRole("link", { name: "Produtos", exact: true }).click();

  await expect(page.getByRole("heading", { name: "Produtos" })).toBeVisible();
  await page.getByLabel("Nome do produto").fill("Consulta");
  await page.getByLabel("Preço (R$)").fill("0.0000");
  await page.getByRole("button", { name: "Cadastrar produto" }).click();
  await expect(page.getByText("Preço: R$ 0,00")).toBeVisible();
  await page.getByRole("button", { name: "Corrigir Consulta" }).click();
  await page.getByLabel("Preço (R$)").fill("");
  await page.getByLabel("Disponível", { exact: true }).uncheck();
  await page.getByRole("button", { name: "Salvar correção" }).click();
  await expect(page.getByText("Preço: não informado")).toBeVisible();
  await expect(page.getByRole("listitem").filter({ hasText: "Consulta" })).toContainText("Indisponível");
  await page.reload();
  await expect(page.getByText("Preço: não informado")).toBeVisible();
  await expect(page.getByText("Revisão comercial 3")).toBeVisible();
});
