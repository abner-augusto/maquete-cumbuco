import { describe, expect, test } from 'vitest';
import type { Lote } from './dados';
import { buscar, loteDaUrl, precosVisiveis, rotuloCurto, rotuloLongo } from './lotes';

const lote = (quadra: string, n: string): Lote => ({ id: `Q${quadra}L${n}`, quadra, lote: n, tipo: 'residencial', area_m2: 300,
  lados_m: [10, 30, 10, 30], frente_m: 10, poligono: [[0, 0], [10, 0], [10, 30], [0, 30]] });
const LOTES = [lote('07', '04'), lote('07', '05'), lote('17', '04'), lote('H', '01'), lote('M', '03')];
const ids = (r: Lote[]) => r.map(l => l.id);

describe('busca', () => {
  test.each(['7 4', 'Q7L4', 'q07 l04', '07-04', 'Q07L04', ' 7  4 '])('"%s" acha o Q07L04', termo =>
    expect(ids(buscar(LOTES, termo))).toEqual(['Q07L04']));
  test('quadra alfabética', () => expect(ids(buscar(LOTES, 'h 1'))).toEqual(['QHL01']));
  test('só a quadra lista os lotes dela, em ordem', () => expect(ids(buscar(LOTES, '7'))).toEqual(['Q07L04', 'Q07L05']));
  test('nada encontrado e termo vazio', () => {
    expect(buscar(LOTES, '9 9')).toEqual([]);
    expect(buscar(LOTES, '  ')).toEqual([]);
  });
});

test('?lote= abre só id exato; inválido é null', () => {
  expect(loteDaUrl(LOTES, '?lote=Q07L04')?.id).toBe('Q07L04');
  expect(loteDaUrl(LOTES, '?lote=q07l04')?.id).toBe('Q07L04');
  expect(loteDaUrl(LOTES, '?lote=Q99L99')).toBeNull();
  expect(loteDaUrl(LOTES, '?lote=xyz')).toBeNull();
  expect(loteDaUrl(LOTES, '')).toBeNull();
});

test('regra dos preços (spec §6)', () => {
  expect(precosVisiveis({ mostrarPrecos: false }, '')).toBe(false);
  expect(precosVisiveis({ mostrarPrecos: false }, '?precos=1')).toBe(false);
  expect(precosVisiveis({ mostrarPrecos: true }, '')).toBe(true);
  expect(precosVisiveis({ mostrarPrecos: true }, '?precos=0')).toBe(false);
});

test('rótulos', () => {
  expect(rotuloCurto(LOTES[0]!)).toBe('Q07 · L04');
  expect(rotuloCurto(LOTES[3]!)).toBe('QH · L01');
  expect(rotuloLongo(LOTES[0]!)).toBe('Quadra 07 · Lote 04');
});
