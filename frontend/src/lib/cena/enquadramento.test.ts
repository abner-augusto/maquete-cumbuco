import { describe, expect, test } from 'vitest';
import * as THREE from 'three';
import { duracaoDoVoo, poseDoVoo, vistaDeFrente } from './enquadramento';

describe('vistaDeFrente', () => {
  const alvo = new THREE.Vector3(10, 5, -20);
  test('a câmera fica do lado da rua, olhando o lote de frente', () => {
    // Rua ao sul do lote (rumo 180): no glTF o sul é +z.
    const p = vistaDeFrente(alvo, 180, 100, 30);
    expect(p.x).toBeCloseTo(10);
    expect(p.z).toBeGreaterThan(alvo.z);
    expect(p.y).toBeGreaterThan(alvo.y);
  });
  test('rua a leste põe a câmera a leste', () => {
    const p = vistaDeFrente(alvo, 90, 100, 30);
    expect(p.x).toBeGreaterThan(alvo.x);
    expect(p.z).toBeCloseTo(alvo.z);
  });
  test('distância e elevação fixas', () => {
    const p = vistaDeFrente(alvo, 45, 100, 30);
    expect(p.distanceTo(alvo)).toBeCloseTo(100);
    expect(p.y - alvo.y).toBeCloseTo(50);
  });
});

describe('poseDoVoo', () => {
  const de = { posicao: new THREE.Vector3(0, 100, 100), alvo: new THREE.Vector3(0, 0, 0) };
  const para = { posicao: new THREE.Vector3(300, 60, 200), alvo: new THREE.Vector3(200, 10, 200) };
  test('começa na pose de partida e termina na de chegada', () => {
    const a = poseDoVoo(de, para, 0);
    expect(a.posicao.distanceTo(de.posicao)).toBeCloseTo(0);
    expect(a.alvo.distanceTo(de.alvo)).toBeCloseTo(0);
    const b = poseDoVoo(de, para, 1);
    expect(b.posicao.distanceTo(para.posicao)).toBeCloseTo(0);
    expect(b.alvo.distanceTo(para.alvo)).toBeCloseTo(0);
  });
  test('gira em volta do alvo pelo arco menor: de 350° a 10° passa pelo norte, não pelo sul', () => {
    const alvo = new THREE.Vector3(0, 0, 0);
    const a = { posicao: vistaDeFrente(alvo, 350, 100, 30), alvo };
    const b = { posicao: vistaDeFrente(alvo, 10, 100, 30), alvo };
    const meio = poseDoVoo(a, b, 0.5).posicao;
    expect(meio.distanceTo(vistaDeFrente(alvo, 0, 100, 30))).toBeLessThan(1);
  });
  test('no meio do caminho a câmera continua à mesma distância do alvo quando as duas poses têm a mesma', () => {
    const alvo = new THREE.Vector3(0, 0, 0);
    const a = { posicao: vistaDeFrente(alvo, 0, 100, 30), alvo };
    const b = { posicao: vistaDeFrente(alvo, 180, 100, 30), alvo };
    const meio = poseDoVoo(a, b, 0.5);
    expect(meio.posicao.distanceTo(meio.alvo)).toBeCloseTo(100);
  });
  test('o avanço é suave: parte e chega devagar', () => {
    const quase = poseDoVoo(de, para, 0.05).posicao.distanceTo(de.posicao);
    const meio = poseDoVoo(de, para, 0.5).posicao.distanceTo(poseDoVoo(de, para, 0.45).posicao);
    expect(quase).toBeLessThan(meio);
  });
});

describe('duracaoDoVoo', () => {
  test('voo curto é rápido, voo longo demora mais, com piso e teto', () => {
    const alvo = new THREE.Vector3(0, 0, 0);
    const a = { posicao: vistaDeFrente(alvo, 0, 100, 30), alvo };
    const perto = { posicao: vistaDeFrente(alvo, 10, 100, 30), alvo };
    const longe = { posicao: vistaDeFrente(new THREE.Vector3(5000, 0, 5000), 90, 3000, 50), alvo: new THREE.Vector3(5000, 0, 5000) };
    expect(duracaoDoVoo(a, a)).toBe(600);
    expect(duracaoDoVoo(a, perto)).toBeGreaterThan(600);
    expect(duracaoDoVoo(a, perto)).toBeLessThan(700);
    expect(duracaoDoVoo(a, longe)).toBe(1400);
  });
});
