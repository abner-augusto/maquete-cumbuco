import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('maquete:visitou', '1'));
});

const lote = /Ficha do lote/;

test('voltar restaura a ficha cheia após galeria e cinema, preservando a URL', async ({ page }) => {
  await page.goto('./?lote=Q07L04&precos=0');
  await expect(page.getByRole('region', { name: lote })).toBeVisible();
  // A ficha pode cobrir o ícone projetado; o teclado também deve permitir a troca.
  await page.getByRole('button', { name: 'Clube: abrir galeria' }).press('Enter');
  await expect(page.getByRole('region', { name: 'Galeria: Clube' })).toBeVisible();
  await expect(page).toHaveURL(/precos=0/);
  await page.goBack();
  await expect(page.getByRole('region', { name: lote })).toContainText('Quadra 07');
  await expect(page).toHaveURL(/lote=Q07L04/);
  await page.keyboard.press('c');
  await expect(page.getByRole('button', { name: 'Buscar lote' })).toHaveCount(0);
  await page.goBack();
  await expect(page.getByRole('region', { name: lote })).toBeVisible();
  await page.goForward();
  await expect(page.getByRole('button', { name: 'Buscar lote' })).toHaveCount(0);
  await page.keyboard.press('Escape');
  await expect(page.getByRole('region', { name: lote })).toBeVisible();
  await page.getByRole('button', { name: 'Fechar ficha' }).click();
  await expect(page.getByRole('region', { name: lote })).toHaveCount(0);
});

test('expandir, voltar, avançar e fechar respeitam as camadas da folha', async ({ page }, info) => {
  test.skip(info.project.name !== 'celular-retrato', 'batentes móveis');
  await page.goto('./?lote=Q07L04');
  const ficha = page.getByRole('region', { name: lote });
  await ficha.getByRole('button', { name: 'Expandir a folha' }).click();
  await expect(ficha.getByRole('button', { name: 'Recolher a folha' })).toBeVisible();
  await page.goBack();
  await expect(ficha.getByRole('button', { name: 'Expandir a folha' })).toBeVisible();
  await page.goForward();
  await expect(ficha.getByRole('button', { name: 'Recolher a folha' })).toBeVisible();
  await ficha.getByRole('button', { name: 'Fechar ficha' }).click();
  await expect(ficha).toHaveCount(0);
});

test('voltar recupera consulta e recarregar não empilha outra ficha', async ({ page }) => {
  await page.goto('./?precos=0');
  await page.getByRole('button', { name: 'Buscar lote' }).click();
  await page.getByRole('textbox', { name: 'Quadra e lote' }).fill('7 4');
  await page.getByRole('button', { name: /Q07.*L04/ }).click();
  await expect(page.getByRole('region', { name: lote })).toBeVisible();
  const tamanho = await page.evaluate(() => history.length);
  await page.reload();
  await expect(page.getByRole('region', { name: lote })).toBeVisible();
  expect(await page.evaluate(() => history.length)).toBe(tamanho);
  await page.goBack();
  await expect(page.getByRole('textbox', { name: 'Quadra e lote' })).toHaveValue('7 4');
  await expect(page).toHaveURL(/precos=0/);
});

for (const fechamento of ['voltar', 'escape', 'botão'] as const) {
  test(`imagem: ${fechamento} fecha só o visualizador e avançar reabre a mídia`, async ({ page }) => {
    await page.goto('./');
    await page.getByRole('button', { name: 'Clube: abrir galeria' }).click();
    const galeria = page.getByRole('region', { name: 'Galeria: Clube' });
    await galeria.getByRole('button', { name: /Ampliar foto 1 de/ }).click();
    const imagem = page.getByRole('dialog');
    await expect(imagem).toBeVisible();
    const src = await imagem.locator('img').getAttribute('src');
    if (fechamento === 'voltar') await page.goBack();
    else if (fechamento === 'escape') await page.keyboard.press('Escape');
    else await imagem.getByRole('button', { name: 'Fechar visualizador' }).click();
    await expect(imagem).toHaveCount(0);
    await expect(galeria).toBeVisible();
    await page.goForward();
    await expect(imagem).toBeVisible();
    await expect(imagem.locator('img')).toHaveAttribute('src', src!);
    await page.goBack();
    await expect(imagem).toHaveCount(0);
    await page.goBack();
    await expect(galeria).toHaveCount(0);
  });
}

test('a planta ampliada sobrevive ao reload e devolve o foco ao fechar', async ({ page }) => {
  await page.goto('./');
  await page.getByRole('button', { name: 'Estande de vendas: abrir galeria' }).click();
  const abrir = page.getByRole('button', { name: 'Ampliar a planta humanizada' });
  await abrir.click();
  await expect(page.getByRole('dialog')).toBeVisible();
  const tamanho = await page.evaluate(() => history.length);
  await page.reload();
  await expect(page.getByRole('dialog')).toBeVisible();
  expect(await page.evaluate(() => history.length)).toBe(tamanho);
  await page.keyboard.press('c');
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await abrir.click();
  await page.getByRole('button', { name: 'Fechar visualizador' }).click();
  await expect(abrir).toBeFocused();
});
