import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { verificar } from './verificar-dist.mjs';

function pasta(arquivos) {
  const raiz = mkdtempSync(path.join(tmpdir(), 'dist-'));
  for (const [nome, conteudo] of Object.entries(arquivos)) {
    mkdirSync(path.dirname(path.join(raiz, nome)), { recursive: true });
    writeFileSync(path.join(raiz, nome), conteudo);
  }
  return raiz;
}

test('arquivo acima de 15 MB é erro', () => {
  const r = verificar(pasta({ 'modelos/grande.glb': Buffer.alloc(15 * 1024 * 1024 + 1) }));
  assert.match(r.erros.join('\n'), /grande\.glb.*15 MB/);
});

test('o nome guardado no conteúdo ou no caminho é erro, sem diferenciar maiúsculas', () => {
  const r = verificar(pasta({ 'index.html': '<title>ALTERNATIVA</title>', 'marca/alternativa/x.svg': '<svg/>' }));
  assert.equal(r.erros.length, 2);
});

test('pasta limpa passa e soma o primeiro carregamento sem o entorno', () => {
  const r = verificar(pasta({ 'index.html': 'ok', 'modelos/loteamento.glb': Buffer.alloc(10), 'modelos/entorno.glb': Buffer.alloc(5) }));
  assert.deepEqual(r.erros, []);
  assert.equal(r.total, 17);
  assert.equal(r.primeiro, 12);
});
