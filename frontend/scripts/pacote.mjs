// Pacote offline: o dist/ com o servidor PowerShell local e o iniciar.cmd. Roda depois do build.
import { copyFile, cp, readFile, rm, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { verificar } from './verificar-dist.mjs';

const FRONT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DIST = path.join(FRONT, 'dist');
const PACOTE = path.join(FRONT, 'pacote');

if (!existsSync(path.join(DIST, 'index.html'))) throw Error('dist/ ausente: rode npm run build antes');
await rm(PACOTE, { recursive: true, force: true });
await cp(DIST, PACOTE, { recursive: true });
// Marca o index do pacote: a ficha esconde o "Compartilhar", que daria um link 127.0.0.1.
const index = path.join(PACOTE, 'index.html');
await writeFile(index, (await readFile(index, 'utf8')).replace('<head>', '<head><meta name="maquete-offline" content="1">'));
for (const n of ['iniciar.cmd', 'servidor.ps1']) await copyFile(path.join(FRONT, 'offline', n), path.join(PACOTE, n));
await writeFile(
  path.join(PACOTE, 'LEIA-ME.txt'),
  'Dê dois cliques em iniciar.cmd. A maquete abre no navegador, sem internet. Para fechar, feche a janela preta.\r\n',
  'utf8',
);

const { erros, total } = verificar(PACOTE);
for (const e of erros) console.error(`ERRO ${e}`);
if (erros.length) process.exit(1);
console.log(`pacote/ montado: ${(total / 1048576).toFixed(1)} MB`);
