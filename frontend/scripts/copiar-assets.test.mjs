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

test('a compressão guarda a cota do terreno a centímetros: a terra a 20 cm da água não cai no plano dela', async () => {
  const { Document, NodeIO } = await import('@gltf-transform/core');
  const { ALL_EXTENSIONS } = await import('@gltf-transform/extensions');
  const { MeshoptEncoder, MeshoptDecoder } = await import('meshoptimizer');
  await Promise.all([MeshoptEncoder.ready, MeshoptDecoder.ready]);
  const doc = new Document();
  const buffer = doc.createBuffer();
  // Um "terreno" de 4 km de lado (como cada janela do entorno), com cotas espalhadas entre a água
  // (−0,74) e 60 cm acima dela, fora de qualquer grade regular.
  const xyz = [];
  for (let i = 0; i < 100; i++) xyz.push((i % 10) * 400, -0.74 + ((i * 37) % 100) * 0.006, Math.floor(i / 10) * 400);
  const pos = doc.createAccessor().setType('VEC3').setArray(new Float32Array(xyz)).setBuffer(buffer);
  const tri = [];
  for (let i = 0; i < 9; i++) for (let j = 0; j < 9; j++) { const k = j * 10 + i; tri.push(k, k + 1, k + 11, k, k + 11, k + 10); }
  const idx = doc.createAccessor().setType('SCALAR').setArray(new Uint16Array(tri)).setBuffer(buffer);
  const prim = doc.createPrimitive().setAttribute('POSITION', pos).setIndices(idx);
  doc.createScene().addChild(doc.createNode('Entorno_00').setMesh(doc.createMesh().addPrimitive(prim)));
  const { comprimirDocumento } = await import('./copiar-assets.mjs');
  await comprimirDocumento(doc);
  const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.encoder': MeshoptEncoder, 'meshopt.decoder': MeshoptDecoder });
  const lido = await io.readBinary(await io.writeBinary(doc));
  const no = lido.getRoot().listNodes()[0];
  const s = no.getWorldScale(), t = no.getWorldTranslation();
  const p = no.getMesh().listPrimitives()[0].getAttribute('POSITION');
  // A compressão reordena os vértices: compara as cotas como conjunto ordenado.
  const v = [0, 0, 0];
  const lidas = [];
  for (let i = 0; i < p.getCount(); i++) { p.getElement(i, v); lidas.push(v[1] * s[1] + t[1]); }
  const originais = xyz.filter((_, i) => i % 3 === 1).sort((a, b) => a - b);
  lidas.sort((a, b) => a - b);
  assert.equal(lidas.length, originais.length);
  const erro = Math.max(...lidas.map((y, i) => Math.abs(y - originais[i])));
  assert.ok(erro < 0.05, `erro de cota de ${erro.toFixed(3)} m`);
});
