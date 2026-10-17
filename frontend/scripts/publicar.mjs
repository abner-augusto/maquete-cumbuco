// Publica o dist/ como Worker de assets no Cloudflare. O domínio vem de DOMINIO (.env da raiz ou
// ambiente): nada da máquina de quem publica fica no repositório. Roda depois do build.
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

/** O wrangler.jsonc com a rota do domínio; sem domínio, vale o workers.dev. */
export function configurar(base, dominio) {
  const config = JSON.parse(base.replace(/^\s*\/\/.*$/gm, ''));
  delete config.$schema;
  if (dominio) config.routes = [{ pattern: dominio, custom_domain: true }];
  else config.workers_dev = true;
  return config;
}

if (process.argv[1] && path.resolve(process.argv[1]) ===fileURLToPath(import.meta.url)) {
  const dominio = process.env.DOMINIO ?? lerEnv(path.join(RAIZ, '.env')).DOMINIO ?? '';
  if (!existsSync(path.join(FRONT, 'dist', 'index.html'))) throw Error('dist/ ausente: rode npm run build antes');
  const config = path.join(FRONT, 'wrangler.publicar.json');
  writeFileSync(config, JSON.stringify(configurar(readFileSync(path.join(FRONT, 'wrangler.jsonc'), 'utf8'), dominio), null, 2));
  try {
    console.log(dominio ? `publicando em ${dominio}` : 'DOMINIO vazio: publicando no workers.dev');
    const r = spawnSync('npx', ['wrangler', 'deploy', '--config', config], { cwd: FRONT, stdio: 'inherit', shell: true });
    process.exitCode = r.status ?? 1;
  } finally {
    rmSync(config, { force: true });
  }
}
