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

describe('materialDaAgua', () => {
  test('o plano da água cede a profundidade ao terreno: sob a terra baixa ele não briga nem pisca', async () => {
    const THREE = await import('three');
    const { materialDaAgua } = await import('./agua');
    const cor = () => new THREE.Color();
    const m = materialDaAgua({ zenite: cor(), faixa: cor(), horizonte: cor(), sol: new THREE.Vector3(0, 1, 0) });
    expect(m.polygonOffset).toBe(true);
    expect(m.polygonOffsetFactor).toBeGreaterThan(0);
    expect(m.polygonOffsetUnits).toBeGreaterThan(0);
  });
});
