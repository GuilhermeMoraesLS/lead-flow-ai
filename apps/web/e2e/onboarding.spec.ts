import { expect, test } from "@playwright/test";

test.use({ launchOptions: { channel: "msedge" } });

test("gestor salva a configuração e retoma após recarregar", async ({ page }) => {
  const suffix = crypto.randomUUID();
  await page.goto("http://127.0.0.1:3000/cadastro");
  await page.getByLabel("E-mail").fill(`sl02-${suffix}@example.test`);
  await page.getByLabel("Senha").fill(`Synthetic-${suffix}!`);
  await page.getByLabel("Nome da empresa").fill("Alfa sintética");
  await page.getByRole("button", { name: "Criar conta" }).click();
  await page.getByRole("link", { name: "Agente de IA", exact: true }).click();

  await expect(page.getByRole("heading", { name: "Identidade do agente" })).toBeVisible();
  await page.getByLabel("Nome", { exact: true }).fill("Lia");
  await page.getByLabel("Identidade", { exact: true }).fill("Assistente comercial da Alfa");
  await page.getByLabel("Instruções").fill("Atenda em português e esclareça dúvidas.");
  await page.getByRole("button", { name: "Salvar configuração" }).click();
  await expect(page.getByRole("status")).toContainText("O agente continua inativo");

  await page.reload();
  await expect(page.getByLabel("Nome", { exact: true })).toHaveValue("Lia");
  await expect(page.getByLabel("Instruções")).toHaveValue("Atenda em português e esclareça dúvidas.");
  await expect(page.getByText("Fonte comercial utilizável: pendente")).toBeVisible();
  await page.getByRole("button", { name: "Verificar ativação" }).click();
  await expect(page.getByRole("status")).toContainText("Ativação recusada");
  await expect(page.getByText("Agente: inativo")).toBeVisible();
});
