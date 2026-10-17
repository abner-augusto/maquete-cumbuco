import { describe, expect, it } from 'vitest';
import { RAIOS_ANEIS } from './entorno';

describe('RAIOS_ANEIS', () => {
  it('anéis de 1, 2 e 4 km', () => {
    expect(RAIOS_ANEIS).toEqual([1000, 2000, 4000]);
  });
});

import { rotulosQueCabem } from './entorno';

describe('rotulosQueCabem', () => {
  it('o anel de fora fica; esconde o rótulo que encosta num que ficou', () => {
    const aneis = [1000, 2000, 4000].map((raio, i) => ({ raio, tela: { x: 100 + i * 30, y: 50 } }));
    expect(rotulosQueCabem(aneis, 50).map(a => a.raio)).toEqual([1000, 4000]);
  });
  it('anel fora da tela não conta', () => {
    expect(rotulosQueCabem([{ raio: 1000, tela: null }, { raio: 2000, tela: { x: 10, y: 0 } }], 50).map(a => a.raio)).toEqual([2000]);
  });
});
