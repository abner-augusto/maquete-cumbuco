import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ativa, fotosCitadas } from './copiar-assets.mjs';

test('fotos citadas: galerias, plantas e fotos de pontos, sem nulos nem repetidas', () => {
  const marcos = { marcos: [
    { galeria: [{ foto: 'marcos/clube/01.jpg' }, { foto: 'marcos/clube/01.jpg' }], planta: null },
    { galeria: [], planta: 'marcos/estande/planta.jpg' },
  ] };
  const pontos = { pontos: [{ foto: null }, { foto: 'pontos/icarai.jpg' }] };
  assert.deepEqual(fotosCitadas(marcos, pontos), ['marcos/clube/01.jpg', 'marcos/estande/planta.jpg', 'pontos/icarai.jpg']);
});

test('só a família ativa da marca sai para o public', () => {
  assert.equal(ativa('marca/svg/americas/simbolo-positivo.svg'), true);
  assert.equal(ativa('marca/svg/alternativa/simbolo-positivo.svg'), false);
});
