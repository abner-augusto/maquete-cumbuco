import { test } from 'node:test';
import assert from 'node:assert/strict';
import { configurar, normalizarDominio } from './publicar.mjs';

const BASE = `{
  "$schema": "node_modules/wrangler/config-schema.json",
  // comentário
  "name": "padrao",
  "workers_dev": false,
  "assets": { "directory": "./dist" }
}`;

test('com domínio vira rota de domínio próprio e o Worker não vai ao workers.dev', () => {
  const c = configurar(BASE, { dominio: 'https://maquete.exemplo.com/' });
  assert.deepEqual(c.routes, [{ pattern: 'maquete.exemplo.com', custom_domain: true }]);
  assert.equal(c.workers_dev, false);
  assert.equal(c.name, 'padrao');
  assert.equal(c.$schema, undefined);
});

test('sem domínio publica no workers.dev', () => {
  const c = configurar(BASE, {});
  assert.equal(c.routes, undefined);
  assert.equal(c.workers_dev, true);
});

test('o nome do Worker pode vir do ambiente', () => {
  assert.equal(configurar(BASE, { nome: ' outro ' }).name, 'outro');
});

test('normalizarDominio tira esquema e barra final', () => {
  assert.equal(normalizarDominio('HTTP://a.b.c//'), 'a.b.c');
  assert.equal(normalizarDominio(undefined), '');
});
