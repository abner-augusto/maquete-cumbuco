import { expect, test } from '@playwright/test';

test('o pacote abre sem internet: cena, ficha e galeria', async ({ page }) => {
  const fora: string[] = [];
  // Tudo que não é o servidor local é cortado: o teste prova que nada depende da rede.
  await page.route('**/*', r => {
    const u = new URL(r.request().url());
    if (u.hostname === '127.0.0.1') return r.continue();
    fora.push(u.href);
    return r.abort();
  });
  await page.addInitScript(() => localStorage.setItem('maquete:visitou', '1'));
  await page.goto('/?lote=Q07L04');
  await expect(page.getByRole('img', { name: /Maquete 3D/ })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Ficha do lote Q07 · L04' })).toBeVisible();
  await page.getByRole('region', { name: /Ficha do lote/ }).getByRole('button', { name: 'Fechar ficha' }).click();
  await page.getByRole('button', { name: 'Clube: abrir galeria' }).click();
  await expect(page.getByRole('region', { name: 'Galeria: Clube' }).getByRole('img').first()).toBeVisible();
  expect(fora).toEqual([]);
});
