import { expect, test, type Page } from '@playwright/test';

async function abrir(page: Page) {
  await page.addInitScript(() => localStorage.setItem('maquete:visitou', '1'));
  await page.goto('./');
  await page.getByRole('button', { name: 'Clube: abrir galeria' }).click();
  await page.getByRole('button', { name: /Ampliar foto 1 de/ }).click();
  const imagem = page.getByRole('dialog');
  await expect(imagem.locator('img')).toBeVisible();
  await expect.poll(() => imagem.locator('img').evaluate(el => (el as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
  const caixa = (await imagem.boundingBox())!;
  const sessao = await page.context().newCDPSession(page);
  let tempo = Date.now() / 1000;
  const ponto = (id: number, dx = 0) => ({ id, x: caixa.width * 0.4 + dx, y: caixa.height * 0.4 });
  const enviar = async (type: 'touchStart' | 'touchMove' | 'touchEnd' | 'touchCancel', touchPoints: ReturnType<typeof ponto>[], ms = 50) => {
    tempo += ms / 1000;
    await sessao.send('Input.dispatchTouchEvent', { type, touchPoints, timestamp: tempo });
  };
  return { imagem, ponto, enviar, escala: imagem.locator('.escala-rotulo') };
}

test('dois dedos próximos iniciam pinça sem disparar toque duplo', async ({ page }) => {
  const { ponto, enviar, escala } = await abrir(page);
  await enviar('touchStart', [ponto(1)]);
  await enviar('touchStart', [ponto(1), ponto(2, 20)]);
  await expect(escala).toHaveText('100%');
  await enviar('touchMove', [ponto(1, -30), ponto(2, 50)]);
  await expect(escala).not.toHaveText('100%');
  await enviar('touchEnd', []);
});

test('arrasto seguido de toque não aproxima a imagem', async ({ page }) => {
  const { ponto, enviar, escala } = await abrir(page);
  await enviar('touchStart', [ponto(1)]);
  await enviar('touchMove', [ponto(1, 60)]);
  await enviar('touchEnd', []);
  await enviar('touchStart', [ponto(2)], 80);
  await enviar('touchEnd', []);
  await expect(escala).toHaveText('100%');
});

test('dois toques válidos aproximam uma vez só e apenas após a segunda soltura', async ({ page }) => {
  const { ponto, enviar, escala } = await abrir(page);
  await enviar('touchStart', [ponto(1)]);
  await enviar('touchEnd', []);
  await enviar('touchStart', [ponto(2)], 120);
  await expect(escala).toHaveText('100%');
  await enviar('touchEnd', []);
  await expect(escala).not.toHaveText('100%');
});
