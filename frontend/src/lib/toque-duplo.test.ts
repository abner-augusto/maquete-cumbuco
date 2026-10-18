import { describe, expect, it } from 'vitest';
import { criarToqueDuplo } from './toque-duplo';

const e = (pointerId: number, timeStamp: number, clientX = 100, clientY = 100, pointerType = 'touch') =>
  ({ pointerId, timeStamp, clientX, clientY, pointerType });

function toque(r: ReturnType<typeof criarToqueDuplo>, inicio: number, duracao = 70, id = 1, x = 100) {
  r.baixar(e(id, inicio, x));
  return r.subir(e(id, inicio + duracao, x));
}

describe('toque duplo confirmado na soltura', () => {
  it.each([[30, 60, 30], [70, 180, 70], [200, 300, 150]])(
    'aceita contatos de %i ms, intervalo de %i ms e segundo contato de %i ms', (primeiro, intervalo, segundo) => {
      const r = criarToqueDuplo();
      expect(toque(r, 1000, primeiro)).toBe(false);
      expect(toque(r, 1000 + primeiro + intervalo, segundo, 2)).toBe(true);
    });
  it('não confirma antes de terminar o segundo contato', () => {
    const r = criarToqueDuplo();
    toque(r, 1000);
    r.baixar(e(2, 1200));
    r.mover(e(2, 1230, 102));
    expect(r.subir(e(2, 1270, 102))).toBe(true);
  });
  it.each([0, 15, 39, 351, 600])('rejeita intervalo de %i ms', intervalo => {
    const r = criarToqueDuplo();
    toque(r, 1000);
    expect(toque(r, 1070 + intervalo, 70, 2)).toBe(false);
  });
  it.each([1, 2])('rejeita contato longo na posição %i', qual => {
    const r = criarToqueDuplo();
    toque(r, 1000, qual === 1 ? 300 : 70);
    expect(toque(r, 1400, qual === 2 ? 300 : 70, 2)).toBe(false);
  });
  it('limita a duração total do par', () => {
    const r = criarToqueDuplo();
    toque(r, 1000, 250);
    expect(toque(r, 1600, 250, 2)).toBe(false);
  });
  it('rejeita contatos distantes', () => {
    const r = criarToqueDuplo();
    toque(r, 1000);
    expect(toque(r, 1200, 70, 2, 140)).toBe(false);
  });
  it.each([1, 2])('invalida arrasto que retorna ao ponto de origem no contato %i', qual => {
    const r = criarToqueDuplo();
    if (qual === 2) toque(r, 1000);
    const t = qual === 1 ? 1000 : 1200;
    r.baixar(e(qual, t));
    r.mover(e(qual, t + 20, 150));
    r.mover(e(qual, t + 40, 100));
    expect(r.subir(e(qual, t + 70))).toBe(false);
    if (qual === 1) expect(toque(r, 1200, 70, 2)).toBe(false);
  });
  it('verifica deslocamento também na soltura, mesmo sem pointermove', () => {
    const r = criarToqueDuplo();
    r.baixar(e(1, 1000));
    r.subir(e(1, 1070, 140));
    expect(toque(r, 1200, 70, 2)).toBe(false);
  });
  it('não confunde dois dedos próximos com toque duplo nem arma o dedo restante', () => {
    const r = criarToqueDuplo();
    r.baixar(e(1, 1000));
    r.baixar(e(2, 1050, 120));
    expect(r.subir(e(2, 1100, 120))).toBe(false);
    expect(r.subir(e(1, 1120))).toBe(false);
    expect(toque(r, 1200, 70, 3)).toBe(false);
    expect(toque(r, 1400, 70, 4)).toBe(true);
  });
  it('cancela o par quando uma pinça começa depois de um primeiro toque válido', () => {
    const r = criarToqueDuplo();
    toque(r, 1000);
    r.baixar(e(2, 1200));
    r.baixar(e(3, 1210, 120));
    expect(r.subir(e(2, 1250))).toBe(false);
    expect(r.subir(e(3, 1260, 120))).toBe(false);
  });
  it.each(['cancelar', 'limpar'] as const)('invalida contatos interrompidos por %s', acao => {
    const r = criarToqueDuplo();
    toque(r, 1000);
    r.baixar(e(2, 1200));
    if (acao === 'cancelar') r.cancelar(2);
    else r.limpar();
    expect(r.subir(e(2, 1250))).toBe(false);
    expect(toque(r, 1350, 70, 3)).toBe(false);
  });
  it('perder captura depois da soltura normal não apaga o primeiro toque', () => {
    const r = criarToqueDuplo();
    toque(r, 1000);
    r.cancelar(1);
    expect(toque(r, 1200, 70, 2)).toBe(true);
  });
  it('um terceiro toque isolado não desfaz o zoom do par anterior', () => {
    const r = criarToqueDuplo();
    toque(r, 1000);
    expect(toque(r, 1200, 70, 2)).toBe(true);
    expect(toque(r, 1400, 70, 3)).toBe(false);
  });
  it('não aceita mouse, caneta ou tempo regressivo como toque duplo', () => {
    for (const tipo of ['mouse', 'pen']) {
      const r = criarToqueDuplo();
      r.baixar(e(1, 1000, 100, 100, tipo));
      r.subir(e(1, 1070, 100, 100, tipo));
      expect(toque(r, 1200, 70, 2)).toBe(false);
    }
    const r = criarToqueDuplo();
    r.baixar(e(1, 1000));
    expect(r.subir(e(1, 900))).toBe(false);
    expect(toque(r, 1200, 70, 2)).toBe(false);
  });
  it('permite calibrar os limites sem mudar a lógica do componente', () => {
    const r = criarToqueDuplo({ intervaloMaximo: 500 });
    toque(r, 1000);
    expect(toque(r, 1500, 70, 2)).toBe(true);
  });
});
