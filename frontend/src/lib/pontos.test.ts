import { expect, test } from 'vitest';
import type { PontoBruto } from './dados';
import { prepararPontos, ROTULO_CATEGORIA, rotuloKm } from './pontos';

const p = (nome: string, km: number, faixa: 'proximo' | 'distante', categoria = 'praia'): PontoBruto => ({ nome, categoria, lat: -3.6, lon: -38.6,
  x: km * 1000, y: 0, km, minutos_carro: 5, faixa, foto: null, credito: null, licenca: null, licenca_url: null, fonte_foto: null });

test('ordena por km e marca os distantes pela faixa do JSON', () => {
  const r = prepararPontos([p('B', 9.1, 'distante'), p('A', 2.3, 'proximo')]);
  expect(r.map(x => [x.nome, x.distante])).toEqual([['A', false], ['B', true]]);
  expect(r[0]!.maps).toBe('https://www.google.com/maps/search/?api=1&query=-3.6,-38.6');
});

test('toda categoria do pontos.json tem rótulo', () => {
  for (const c of ['compras', 'hotel', 'kitesurf', 'lagoa', 'lazer', 'natureza', 'orla', 'porto', 'praia', 'restaurante', 'saude'])
    expect(ROTULO_CATEGORIA[c]).toBeTruthy();
});

test('km com vírgula', () => expect(rotuloKm(2.3)).toBe('2,3 km'));
