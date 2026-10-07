import { expect, test } from "@playwright/test";

test.use({ launchOptions: { channel: "msedge" } });

test("gestor envia documento, vê falha acionável e corrige", async ({ page }) => {
  test.setTimeout(120_000);
  const suffix = crypto.randomUUID();
  await page.goto("http://127.0.0.1:3000/cadastro");
  await page.getByLabel("E-mail").fill(`documentos-${suffix}@example.test`);
  await page.getByLabel("Senha").fill(`Synthetic-${suffix}!`);
  await page.getByLabel("Nome da empresa").fill("Alfa sintética");
  await page.getByRole("button", { name: "Criar conta" }).click();
  await page.getByRole("link", { name: "Documentos", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Documentos", level: 1 })).toBeVisible();

  await page.getByLabel("Arquivo").setInputFiles({ name: "politica.txt", mimeType: "text/plain",
    buffer: Buffer.from("%PDF-1.4 conteúdo que não é texto") });
  await page.getByRole("button", { name: "Enviar arquivo" }).click();
  await expect(page.getByText("Ele só será usado depois de ficar pronto.")).toBeVisible();
  const item = page.getByRole("listitem").filter({ hasText: "politica.txt" });
  await expect(item).toContainText("Falhou", { timeout: 60_000 });
  await expect(item).toContainText("O conteúdo não corresponde ao tipo informado.");

  await page.getByRole("button", { name: "Corrigir politica.txt" }).click();
  await page.getByLabel("Arquivo").setInputFiles({ name: "politica.txt", mimeType: "text/plain",
    buffer: Buffer.from(`Garantia de doze meses para o Plano Sol ${suffix}.`) });
  await page.getByRole("button", { name: "Enviar arquivo" }).click();
  await expect(item).toContainText("Pronto para uso", { timeout: 90_000 });
  await expect(item).toContainText("1 trechos indexados");
  await page.reload();
  await expect(page.getByRole("listitem").filter({ hasText: "politica.txt" })).toContainText("Pronto para uso");
  await expect(page.getByText("1 prontos")).toBeVisible();
});
