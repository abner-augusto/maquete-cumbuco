import { describe, expect, it } from 'vitest';
import { raiosDosAneis } from './entorno';

describe('raiosDosAneis', () => {
  it('um anel a cada passo, até o alcance', () => {
    expect(raiosDosAneis(600, 3000)).toEqual([600, 1200, 1800, 2400, 3000]);
  });
  it('não passa do alcance quando o passo não divide', () => {
    expect(raiosDosAneis(700, 3000)).toEqual([700, 1400, 2100, 2800]);
  });
});

import { rotulosQueCabem } from './entorno';

describe('rotulosQueCabem', () => {
  it('o anel de fora fica; esconde o rótulo que encosta num que ficou', () => {
    const aneis = [600, 1200, 1800, 2400, 3000].map((raio, i) => ({ raio, tela: { x: 100 + i * 20, y: 50 } }));
    expect(rotulosQueCabem(aneis, 50).map(a => a.raio)).toEqual([1200, 3000]);
  });
  it('anel fora da tela não conta', () => {
    expect(rotulosQueCabem([{ raio: 600, tela: null }, { raio: 1200, tela: { x: 10, y: 0 } }], 50).map(a => a.raio)).toEqual([1200]);
  });
});
