import { describe, expect, test } from 'vitest';
import { quadroDaAgua } from './agua';

describe('quadroDaAgua', () => {
  const base = { entorno: true, reduzido: false, agora: 1000, ultimo: 0 };
  test('anima no entorno, a ~24 quadros por segundo', () => {
    expect(quadroDaAgua(base)).toBe(true);
    expect(quadroDaAgua({ ...base, ultimo: 990 })).toBe(false); // 10 ms depois: espera
  });
  test('parada sem o entorno ou com movimento reduzido', () => {
    expect(quadroDaAgua({ ...base, entorno: false })).toBe(false);
    expect(quadroDaAgua({ ...base, reduzido: true })).toBe(false);
  });
});
