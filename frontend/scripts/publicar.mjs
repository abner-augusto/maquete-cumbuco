// Publica o dist/ como Worker de assets no Cloudflare. Domínio e nome do Worker vêm do .env da raiz
// (ou do ambiente): nada de quem publica fica no repositório. Roda depois do build.
import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const FRONT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const RAIZ = path.resolve(FRONT, '..');

export function lerEnv(arquivo) {
  if (!existsSync(arquivo)) return {};
  return Object.fromEntries(readFileSync(arquivo, 'utf8').split(/\r?\n/)
    .filter(l => l.trim() && !l.trim().startsWith('#') && l.includes('='))
    .map(l => { const i = l.indexOf('='); return [l.slice(0, i).trim(), l.slice(i + 1).trim().replace(/^"|"$/g, '')]; }));
}

/** `https://exemplo.com/` e `exemplo.com` dão o mesmo domínio. */
export const normalizarDominio = d => (d ?? '').trim().replace(/^https?:\/\//i, '').replace(/\/+$/, '');

/**
 * O wrangler.jsonc com a rota do domínio e, se pedido, outro nome de Worker. Sem domínio vale o
 * workers.dev.
 */
export function configurar(base, { dominio = '', nome = '' } = {}) {
  const config = JSON.parse(base.replace(/^\s*\/\/.*$/gm, ''));
  delete config.$schema;
  const host = normalizarDominio(dominio);
  if (nome.trim()) config.name = nome.trim();
  if (host) config.routes = [{ pattern: host, custom_domain: true }];
  else config.workers_dev = true;
  return config;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const env = { ...lerEnv(path.join(RAIZ, '.env')), ...process.env };
  const dominio = normalizarDominio(env.DOMINIO);
  const config = path.join(FRONT, 'wrangler.publicar.json');
  if (!existsSync(path.join(FRONT, 'dist', 'index.html'))) throw Error('dist/ ausente: rode npm run build antes');
  const final = configurar(readFileSync(path.join(FRONT, 'wrangler.jsonc'), 'utf8'), { dominio, nome: env.WORKER_NOME ?? '' });
  writeFileSync(config, JSON.stringify(final, null, 2));
  try {
    console.log(`Worker ${final.name}: ${dominio ? `publicando em ${dominio}` : 'DOMINIO vazio, publicando no workers.dev'}`);
    const r = spawnSync('npx', ['wrangler', 'deploy', '--config', config], { cwd: FRONT, stdio: 'inherit', shell: true });
    process.exitCode = r.status ?? 1;
  } finally {
    rmSync(config, { force: true });
  }
}
