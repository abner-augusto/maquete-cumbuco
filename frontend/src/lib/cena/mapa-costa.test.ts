import { describe, expect, it } from 'vitest';
import { codificarDistancia, distanciaAteATerra } from './mapa-costa';

describe('distanciaAteATerra', () => {
  it('mede em metros a partir da terra, que fica em zero', () => {
    const n = 5;
    const terra = new Uint8Array(n * n);
    terra[2 * n + 0] = 1;  // uma célula de terra na borda oeste
    const d = distanciaAteATerra(terra, n, 10);
    expect(d[2 * n + 0]).toBe(0);
    expect(d[2 * n + 3]).toBeCloseTo(30);
    expect(d[3 * n + 1]).toBeCloseTo(10 * Math.SQRT2);
  });
  it('sem terra, tudo é infinito', () => {
    expect(distanciaAteATerra(new Uint8Array(9), 3, 10).every(x => x === Infinity)).toBe(true);
  });
});

describe('codificarDistancia', () => {
  it('guarda a raiz da distância em um byte: fino na praia, travado no alcance', () => {
    const b = codificarDistancia(new Float32Array([0, 750, 3000, 9000, Infinity]), 3000);
    expect([...b]).toEqual([0, 128, 255, 255, 255]);
  });
});
