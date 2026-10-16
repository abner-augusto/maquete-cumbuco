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
