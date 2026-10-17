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
    const m = materialDaAgua({ zenite: cor(), faixa: cor(), horizonte: cor(), chao: cor(), horizonteQuente: cor(), sol: new THREE.Vector3(0, 1, 0) });
    expect(m.polygonOffset).toBe(true);
    expect(m.polygonOffsetUnits).toBeGreaterThan(0);
    // Sem o termo pela inclinação: na água rasante de longe ele cresce sem limite e some com o mar.
    expect(m.polygonOffsetFactor).toBe(0);
  });
});

describe('alcance da água', () => {
  test('a água leva a cor do solo do céu: de longe desbota para o que o céu mostra naquela direção', async () => {
    const THREE = await import('three');
    const { materialDaAgua, alcanceDaAgua } = await import('./agua');
    const cor = () => new THREE.Color();
    const m = materialDaAgua({ zenite: cor(), faixa: cor(), horizonte: cor(), chao: cor(), horizonteQuente: cor(), sol: new THREE.Vector3(0, 1, 0) });
    expect(m.uniforms.uChao).toBeDefined();
    // E o horizonte quente do lado do sol, como no céu: sem isso o fim do mar desenhava uma aresta contra ele.
    expect(m.uniforms.uHorizonteQuente).toBeDefined();
    expect(m.fragmentShader).toContain('uHorizonteQuente');
    expect(m.fragmentShader).toContain('uChao');
    // O alcance vem da malha do mar, não de um número no front: raio em volta do centro dos lotes,
    // no mundo (o GLB quantizado guarda a posição normalizada e a escala no nó).
    const g = new THREE.BufferGeometry().setAttribute('position', new THREE.Float32BufferAttribute([0, 0, 0, 0.3, 0, 0, 0, 0, -0.4], 3));
    const malha = new THREE.Mesh(g);
    malha.scale.setScalar(1000);
    malha.updateMatrixWorld(true);
    expect(alcanceDaAgua(malha, new THREE.Vector3(0, 0, 0))).toBeCloseTo(400);
  });
});

describe('desbotarDaAgua', () => {
  test('a água desbota para o céu a partir do fim da terra do entorno, não do fim do plano (que vai ao horizonte)', async () => {
    const { desbotarDaAgua } = await import('./agua');
    const d = desbotarDaAgua(4000);
    expect(d.x).toBeGreaterThan(4000 * 0.5);  // o mar perto da terra do entorno continua nítido
    expect(d.y).toBeGreaterThan(d.x);
    expect(d.y).toBeLessThanOrEqual(4000 * 2);  // a aresta reta do polígono do mar, logo depois da terra, já sumiu no céu
  });
});

describe('PARAMETROS_AGUA', () => {
  test('cada parâmetro do painel é uniform do material e está declarado no shader', async () => {
    const THREE = await import('three');
    const { materialDaAgua, PARAMETROS_AGUA } = await import('./agua');
    const cor = () => new THREE.Color();
    const m = materialDaAgua({ zenite: cor(), faixa: cor(), horizonte: cor(), chao: cor(), horizonteQuente: cor(), sol: new THREE.Vector3(0, 1, 0) });
    for (const p of PARAMETROS_AGUA) {
      expect(m.uniforms[p.uniforme]?.value, p.uniforme).toBe(p.valor);
      expect(m.fragmentShader).toContain(`uniform float ${p.uniforme};`);
      expect(p.valor).toBeGreaterThanOrEqual(p.min);
      expect(p.valor).toBeLessThanOrEqual(p.max);
    }
  });
  test('o turquesa nunca passa do alcance do mapa da costa: senão o mar aberto todo ficaria raso', async () => {
    const { PARAMETROS_AGUA } = await import('./agua');
    const { ALCANCE_COSTA } = await import('./mapa-costa');
    const max = (u: string) => PARAMETROS_AGUA.find(p => p.uniforme === u)!.max;
    expect(max('uRaso') + max('uMistura')).toBeLessThan(ALCANCE_COSTA);
  });
});
