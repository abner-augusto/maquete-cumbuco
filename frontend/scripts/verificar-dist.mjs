// Orçamento (15 MB por arquivo, o teto do Cloudflare: decisão de 16/10/2026) e proteção do nome
// guardado (AGENTS.md): nada publicado pode citá-lo, nem no conteúdo nem no caminho.
import { readFileSync, readdirSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const LIMITE = 15 * 1024 * 1024;
const PROIBIDO = /alternativa/i;
// Carregam depois, só no modo entorno.
const DEPOIS = /(^|\/)(modelos\/(entorno|vegetacao)\.(glb|json))$/;

function arquivos(raiz, rel = '') {
  return readdirSync(path.join(raiz, rel), { withFileTypes: true }).flatMap(e =>
    e.isDirectory() ? arquivos(raiz, path.posix.join(rel, e.name)) : [path.posix.join(rel, e.name)]);
}

export function verificar(raiz) {
  const erros = [];
  let total = 0;
  let primeiro = 0;
  for (const rel of arquivos(raiz)) {
    const bytes = statSync(path.join(raiz, rel)).size;
    total += bytes;
    if (!DEPOIS.test(rel)) primeiro += bytes;
    if (bytes > LIMITE) erros.push(`${rel}: ${(bytes / 1048576).toFixed(1)} MB, acima de 15 MB por arquivo (quebre em partes)`);
    if (PROIBIDO.test(rel)) erros.push(`${rel}: o caminho cita o nome guardado`);
    else if (readFileSync(path.join(raiz, rel)).toString('latin1').match(PROIBIDO)) erros.push(`${rel}: o conteúdo cita o nome guardado`);
  }
  return { erros, total, primeiro };
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const dist = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', process.argv[2] ?? 'dist');
  const { erros, total, primeiro } = verificar(dist);
  const mb = n => `${(n / 1048576).toFixed(1)} MB`;
  console.log(`dist: ${mb(total)} no total · primeiro carregamento (sem o entorno) ${mb(primeiro)}`);
  for (const e of erros) console.error(`ERRO ${e}`);
  process.exit(erros.length ? 1 : 0);
}
