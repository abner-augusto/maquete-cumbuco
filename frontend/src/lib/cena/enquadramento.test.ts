import { describe, expect, test } from 'vitest';
import * as THREE from 'three';
import { vistaDeFrente } from './enquadramento';

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
