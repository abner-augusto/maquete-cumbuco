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

test('o servidor segue de pé depois de uma requisição interrompida ou inválida', async ({ baseURL }) => {
  const http = await import('node:http');
  // Download cortado no meio, como um F5 com o GLB carregando.
  await new Promise<void>(ok => {
    const req = http.get(`${baseURL}/modelos/loteamento.glb`, r => r.once('data', () => (req.destroy(), ok())));
    req.on('error', () => ok());
  });
  await new Promise(ok => setTimeout(ok, 500));
  expect((await fetch(`${baseURL}/`)).status).toBe(200);
  // Caminho que o .NET recusa ao montar o arquivo.
  expect((await fetch(`${baseURL}/a:b`)).status).toBe(404);
  expect((await fetch(`${baseURL}/`)).status).toBe(200);
});

test('no pacote offline a ficha não oferece Compartilhar (o link seria 127.0.0.1)', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('maquete:visitou', '1'));
  await page.goto('/?lote=Q07L04');
  const ficha = page.getByRole('region', { name: 'Ficha do lote Q07 · L04' });
  await expect(ficha.getByRole('heading', { name: 'Quadra 07 · Lote 04' })).toBeVisible();
  await expect(ficha.getByRole('button', { name: 'Compartilhar' })).toHaveCount(0);
});
