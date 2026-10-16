import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';

const LOTES = JSON.parse(readFileSync(new URL('../public/dados/lotes.json', import.meta.url), 'utf8')).lotes as
  { id: string; quadra: string; lote: string; area_m2: number; inscricao_iptu?: string }[];
const area = (n: number) => `${n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} m²`;
const L = LOTES.find(l => l.id === 'Q07L04')!;

async function jaVisitou(page: Page) {
  await page.addInitScript(() => localStorage.setItem('maquete:visitou', '1'));
}
const ficha = (page: Page, id = 'Q07 · L04') => page.getByRole('region', { name: `Ficha do lote ${id}` });

test('1. a maquete abre com a marca, a legenda e sem o nome guardado', async ({ page }) => {
  await jaVisitou(page);
  await page.goto('./');
  await expect(page.getByRole('img', { name: /Maquete 3D/ })).toBeVisible();
  await expect(page.getByRole('img', { name: /Cidade das Américas/ })).toBeVisible();
  await expect(page.getByLabel('Legenda')).toContainText('Residencial');
  expect((await page.content()).toLowerCase()).not.toContain('alternativa');
});

test('2. a primeira visita mostra como explorar, uma vez só', async ({ page }) => {
  await page.goto('./');
  await expect(page.getByRole('region', { name: 'Como explorar' })).toBeVisible();
  await page.getByRole('button', { name: 'Começar' }).click();
  await page.reload();
  await expect(page.getByRole('region', { name: 'Como explorar' })).toHaveCount(0);
});

test('3. a busca "7 4" abre a ficha do Q07L04 com área e IPTU do JSON', async ({ page }) => {
  await jaVisitou(page);
  await page.goto('./');
  await page.getByRole('button', { name: 'Buscar lote' }).click();
  await page.getByRole('textbox', { name: 'Quadra e lote' }).fill('7 4');
  await page.getByRole('button', { name: /Q07 · L04/ }).click();
  await expect(ficha(page).getByRole('heading', { name: 'Quadra 07 · Lote 04' })).toBeVisible();
  await expect(ficha(page)).toContainText(area(L.area_m2));
  if (L.inscricao_iptu) await expect(ficha(page)).toContainText(L.inscricao_iptu);
  await expect(page).toHaveURL(/\?lote=Q07L04$/);
});

test('4. ?lote= abre direto na ficha; id inválido abre a vista inicial sem ficha', async ({ page }) => {
  await jaVisitou(page);
  await page.goto('./?lote=Q07L04');
  await expect(ficha(page)).toBeVisible();
  await page.goto('./?lote=Q99L99');
  await expect(page.getByRole('img', { name: /Maquete 3D/ })).toBeVisible();
  await expect(page.getByRole('region', { name: /Ficha do lote/ })).toHaveCount(0);
});

test('5. o clique no lote enquadrado abre a ficha dele', async ({ page }) => {
  await jaVisitou(page);
  await page.goto('./?lote=Q07L04');
  await ficha(page).getByRole('button', { name: 'Fechar ficha' }).click();
  await expect(ficha(page)).toHaveCount(0);
  // Enquadrar põe o pivô do lote no centro da tela.
  const tela = await page.getByRole('img', { name: /Maquete 3D/ }).boundingBox();
  await page.mouse.click(tela!.x + tela!.width / 2, tela!.y + tela!.height / 2);
  await expect(ficha(page)).toBeVisible();
});

// Regra dos preços (spec §6), com config e lote interceptados.
for (const [mostrar, busca, visivel] of [[false, '', false], [true, '', true], [true, '&precos=0', false]] as const) {
  test(`6. preços: mostrarPrecos=${mostrar}${busca || ' sem parâmetro'} → ${visivel ? 'visíveis' : 'escondidos'}`, async ({ page }) => {
    await jaVisitou(page);
    await page.route('**/dados/config.json', async r => {
      const c = await (await r.fetch()).json();
      await r.fulfill({ json: { ...c, mostrarPrecos: mostrar } });
    });
    await page.route('**/dados/lotes.json', async r => {
      const d = await (await r.fetch()).json();
      d.lotes = d.lotes.map((l: { id: string }) => (l.id === 'Q07L04' ? { ...l, preco_total: 250000, preco_m2: 500 } : l));
      await r.fulfill({ json: d });
    });
    await page.goto(`./?lote=Q07L04${busca}`);
    await expect(ficha(page)).toBeVisible();
    await expect(ficha(page).getByRole('region', { name: 'Preço' })).toHaveCount(visivel ? 1 : 0);
    if (visivel) await expect(ficha(page)).toContainText(/Tabela .+ · ref\./);
  });
}

test('7. lote sem IPTU não mostra o campo', async ({ page }) => {
  const sem = LOTES.find(l => !l.inscricao_iptu)!;
  await jaVisitou(page);
  await page.goto(`./?lote=${sem.id}`);
  await expect(page.getByRole('region', { name: /Ficha do lote/ })).toBeVisible();
  await expect(page.getByRole('region', { name: /Ficha do lote/ })).not.toContainText('Inscrição IPTU');
});

test('8. o estande abre a galeria com a planta e o "Como chegar" na coordenada do KMZ', async ({ page }) => {
  const { marcos } = JSON.parse(readFileSync(new URL('../public/dados/marcos.json', import.meta.url), 'utf8'));
  const estande = marcos.find((m: { id: string }) => m.id === 'estande');
  await jaVisitou(page);
  await page.goto('./');
  await page.getByRole('button', { name: 'Estande de vendas: abrir galeria' }).click();
  const galeria = page.getByRole('region', { name: 'Galeria: Estande de vendas' });
  await expect(galeria.getByRole('link', { name: 'Como chegar' })).toHaveAttribute('href', new RegExp(`query=${estande.lat},${estande.lon}`));
  await galeria.getByRole('button', { name: 'Ampliar a planta humanizada' }).click();
  await expect(page.getByRole('dialog', { name: /Planta humanizada/ })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
});

test('9. o clube abre a galeria com todas as fotos do JSON', async ({ page }) => {
  const { marcos } = JSON.parse(readFileSync(new URL('../public/dados/marcos.json', import.meta.url), 'utf8'));
  const clube = marcos.find((m: { id: string }) => m.id === 'clube');
  await jaVisitou(page);
  await page.goto('./');
  await page.getByRole('button', { name: 'Clube: abrir galeria' }).click();
  await expect(page.getByRole('region', { name: 'Galeria: Clube' }).getByRole('button', { name: /Ampliar foto/ })).toHaveCount(clube.galeria.length);
});

test('10. o entorno lista os pontos do JSON e abre a ficha do ponto', async ({ page }) => {
  const { pontos } = JSON.parse(readFileSync(new URL('../public/dados/pontos.json', import.meta.url), 'utf8'));
  const primeiro = [...pontos].sort((a: { km: number }, b: { km: number }) => a.km - b.km)[0];
  await jaVisitou(page);
  await page.goto('./');
  await page.getByRole('button', { name: 'Entorno e pontos de referência' }).click();
  const lista = page.getByRole('region', { name: 'Pontos de referência' });
  await expect(lista.getByRole('listitem')).toHaveCount(pontos.length);
  await lista.getByRole('button', { name: new RegExp(primeiro.nome) }).click();
  const ficha = page.getByRole('region', { name: `Ponto: ${primeiro.nome}` });
  await expect(ficha).toContainText(`${primeiro.minutos_carro} min`);
  await expect(ficha.getByRole('link', { name: 'Abrir no Google Maps' })).toHaveAttribute('href', /google\.com\/maps/);
});
