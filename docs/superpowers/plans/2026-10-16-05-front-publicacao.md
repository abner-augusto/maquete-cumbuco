# Front e publicação — Plano 5

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Um site em Svelte 5 + Three.js que mostra a maquete da Fase 1 (lotes clicáveis com Ficha, marcos com galeria, entorno com pontos), roda online como Worker de assets estáticos e offline pelo `iniciar.cmd`, sem o nome guardado em nenhum arquivo publicado.

**Architecture:** `frontend/` derivado do `$REPOS_DIR/cv_espelho_vendas/frontend` (Cena atrás de uma interface pequena, Folha de três batentes, tema por tokens), sem backend nem CRM. Um script Node (`copiar-assets.mjs`) monta o `public/` a partir das fontes de verdade (`dados/`, `marca/`, GLBs em `10-MAQUETE INTERATIVA/`), comprime os GLBs com meshopt e converte as fotos para WebP. A lógica pura (busca, preços, mídia, pontos) tem testes de unidade em Vitest; as jornadas, Playwright sobre o build.

**Tech Stack:** Node 26, Vite 8, Svelte 5, TypeScript 6, three 0.186.1, @gltf-transform 4.2.1, meshoptimizer 0.25.0, draco3dgltf 1.5.7, sharp, @fontsource (Cinzel, Jost), Vitest, Playwright 1.63, Wrangler; PowerShell 5+ para o servidor offline.

**Spec:** `docs/superpowers/specs/2026-10-14-maquete-cumbuco-design.md` (§5 Cena e interação, §6 Dados e Ficha, §7.4 Export, §9 Testes, §10 Riscos).

## Global Constraints

- Interface, docs e commits em português do Brasil.
- **Nenhum número digitado à mão no front:** área, lados, preço, posição, cota e minutos vêm de `dados/*.json` ou do GLB. Ajustes de apresentação editados à mão (vista inicial, altura do volume do estande) ficam em `dados/config.json`, que a spec já define como editado à mão.
- **O nome guardado não aparece em nada publicado:** `dist/`, `pacote/`, `package.json` (`name`), `wrangler.jsonc` (`name`), `<title>`, `manifest.json`. Um script falha se achar `alternativa` (sem diferenciar maiúsculas) em qualquer nome ou conteúdo de arquivo do `dist/`. O tema é `data-tema="americas"`.
- **Orçamento (decisão do usuário em 16/10/2026, substitui a §7.4 da spec):** o limite é **15 MB por arquivo** publicado (o teto do Cloudflare que ele usa); arquivo maior pode ser quebrado em partes. O total do primeiro carregamento é medido e reportado, não bloqueia.
- **Offline sem rede:** nenhuma requisição fora do próprio servidor. Fontes empacotadas pelo Vite (`@fontsource`), decoders (meshopt em JS, Draco em `public/draco/`) servidos localmente. Links externos (Google Maps, crédito das fotos) são `<a>`, não carregam nada.
- **Não publicar URL pública indexável sem o ok explícito do usuário (⛔).** O plano prepara o Worker e para antes do `wrangler deploy`.
- Coordenadas: local `(x = leste, y = norte, z = cota)` em metros (origem `dados/georref.json`); no Three.js, `(x, z, −y)`. Os GLBs já estão em Y para cima.
- Preços: `config.mostrarPrecos` falso esconde sempre; verdadeiro mostra, salvo `?precos=0` (spec §6).
- WCAG AA: foco visível, alvos de 44 px, teclado na Folha e na galeria, `prefers-reduced-motion`.
- Rodar tudo do front de dentro de `frontend/` (`npm …`); o pipeline Python continua com `uv run` na raiz.

## Review Focus

1. **Rede bloqueada no pacote offline:** com toda requisição que não seja `127.0.0.1` abortada, a cena, a Ficha e a galeria abrem (Task 10 bloqueia a rede no teste).
2. **Nome guardado num asset gerado:** um SVG, um JSON ou um nome de pasta copiado de `marca/` ou `dados/` com "alternativa" chega ao `dist/` (Task 8 varre nomes e conteúdo; Task 2 copia só `marca/svg/americas/`).
3. **`?lote=` inválido ou de outra quadra** (`?lote=Q99L99`, `?lote=xyz`): a cena abre na vista inicial, sem Ficha e sem erro (teste na Task 5).
4. **Busca com formatos que o corretor digita** ("7 4", "Q7L4", "q07 l04", "h 1", "07-04"): todos acham o lote certo; "7" sozinho lista os lotes da quadra (testes da Task 3).
5. **Lote sem inscrição de IPTU ou sem preço com os preços ligados:** a Ficha some com o campo sem deixar buraco (teste da Task 5 com `lotes.json` interceptado).

---

## Mapa de arquivos

```
frontend/
  package.json, vite.config.ts, svelte.config.js, tsconfig.json, vitest.config.ts, playwright.config.ts, index.html
  .gitignore                      public/ gerado, dist/, pacote/, test-results/
  wrangler.jsonc                  Worker só de assets (Task 9)
  scripts/
    copiar-assets.mjs             fontes de verdade → public/ (Task 2)
    verificar-dist.mjs            orçamento por arquivo + nome guardado (Task 8)
    pacote.mjs                    dist/ + iniciar.cmd + servidor.ps1 → pacote/ (Task 10)
  offline/
    iniciar.cmd, servidor.ps1     servidor local sem dependências (Task 10)
  public/_headers                 noindex (versionado; o resto do public/ é gerado)
  src/
    main.ts, App.svelte
    estilos/base.css              tokens fixos (status, raio, movimento), do espelho
    lib/
      dados.ts                    tipos e carga dos JSON (Task 3)
      lotes.ts                    busca, rótulos, regra dos preços (Task 3)
      midia.ts                    caminhos das fotos WebP (Task 3)
      pontos.ts                   pontos do entorno: rótulo, distância, Maps (Task 7)
      dispositivo.ts              localStorage tolerante (primeira visita, cor) (Task 5)
      cena/cena.ts                renderer, câmera, luz, lotes, marcos (Task 4, 6)
      cena/ceu.ts                 céu em gradiente, do espelho (Task 4)
      cena/entorno.ts             entorno.glb + vegetação instanciada (Task 7)
    componentes/
      Folha.svelte, Icone.svelte, PlantaAmpliada.svelte (do espelho)
      Marca.svelte, Controles.svelte, Bussola.svelte, Legenda.svelte, BoasVindas.svelte
      Busca.svelte, Ficha.svelte, Contorno.svelte (Task 5)
      Marcos.svelte, Galeria.svelte (Task 6)
      PontosEntorno.svelte, ListaEntorno.svelte, FichaPonto.svelte, IconePonto.svelte (Task 7)
  src/lib/*.test.ts               Vitest
  e2e/jornadas.spec.ts, e2e/offline.spec.ts
```

Saídas fora do repo: nenhuma. O `pacote/` fica em `frontend/pacote/` (ignorado); copiá-lo para a pasta do terreno é decisão do usuário.

---

### Task 1: Esqueleto do front

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/svelte.config.js`, `frontend/tsconfig.json`, `frontend/vitest.config.ts`, `frontend/index.html`, `frontend/.gitignore`, `frontend/src/main.ts`, `frontend/src/App.svelte`, `frontend/src/estilos/base.css`, `frontend/public/_headers`, `frontend/src/lib/sanidade.test.ts`

**Interfaces:**
- Produces: `npm run dev|build|preview|test:unidade|check`; `App.svelte` monta em `#app`; `base.css` com os tokens fixos do espelho (`--status-*`, `--raio-*`, `--dur-*`, `--toque`).

- [ ] **Step 1: `package.json`**

```json
{
  "name": "cidade-americas-maquete",
  "private": true,
  "type": "module",
  "scripts": {
    "assets": "node scripts/copiar-assets.mjs",
    "dev": "npm run assets && vite",
    "build": "npm run assets && vite build",
    "preview": "vite preview",
    "check": "svelte-check --tsconfig ./tsconfig.json",
    "test:unidade": "vitest run",
    "test": "playwright test",
    "verificar": "node scripts/verificar-dist.mjs",
    "pacote": "node scripts/pacote.mjs"
  },
  "dependencies": {
    "@fontsource/cinzel": "5.2.8",
    "@fontsource/jost": "5.2.8",
    "three": "0.186.1"
  },
  "devDependencies": {
    "@gltf-transform/core": "4.2.1",
    "@gltf-transform/extensions": "4.2.1",
    "@gltf-transform/functions": "4.2.1",
    "@playwright/test": "1.63.0",
    "@sveltejs/vite-plugin-svelte": "7.3.1",
    "@tsconfig/svelte": "5.0.8",
    "@types/node": "22.20.5",
    "@types/three": "0.186.0",
    "draco3dgltf": "1.5.7",
    "meshoptimizer": "0.25.0",
    "sharp": "0.34.5",
    "svelte": "5.57.2",
    "svelte-check": "4.7.6",
    "typescript": "6.0.3",
    "vite": "8.3.3",
    "vitest": "4.0.8",
    "wrangler": "4.45.0"
  }
}
```

Se `npm install` recusar uma versão exata (pacote ainda não publicado nessa versão), usar a mais nova publicada há pelo menos duas semanas e registrar como Ruling.

- [ ] **Step 2: configs** — copiar `svelte.config.js` e `tsconfig.json` do espelho sem mudança (o `include` já cobre `e2e/` e os configs; acrescentar `"vitest.config.ts"` ao `include`). `vite.config.ts`:

```ts
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

// Base relativa: o mesmo dist/ serve no Worker (raiz) e no pacote offline (qualquer pasta).
export default defineConfig({
  base: './',
  plugins: [svelte()],
  server: { host: '127.0.0.1', port: 5173, strictPort: true },
  preview: { host: '127.0.0.1', port: 4173, strictPort: true },
  build: { target: 'es2022', chunkSizeWarningLimit: 900 },
});
```

`vitest.config.ts`:

```ts
import { defineConfig } from 'vitest/config';

export default defineConfig({ test: { include: ['src/**/*.test.ts'], environment: 'node' } });
```

`.gitignore`:

```
node_modules/
dist/
pacote/
test-results/
playwright-report/
public/*
!public/_headers
src/estilos/temas/
```

`public/_headers` (Worker): `X-Robots-Tag: noindex, nofollow, noarchive`, `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff` em `/*`; `Cache-Control: public, max-age=31536000, immutable` em `/assets/*` (texto igual ao do espelho).

- [ ] **Step 3: `index.html`, `main.ts`, `base.css`, `App.svelte` mínimo**

`index.html`: o do espelho, com `<title>Residencial Cumbuco</title>`, sem os `<link>` do Google Fonts, com `<link rel="icon" href="./marca/favicon.svg" type="image/svg+xml">` e `<script type="module" src="/src/main.ts">`. Mantém `robots noindex` e `referrer no-referrer`.

`main.ts`:

```ts
import '@fontsource/cinzel/500.css';
import '@fontsource/cinzel/600.css';
import '@fontsource/jost/400.css';
import '@fontsource/jost/500.css';
import '@fontsource/jost/600.css';
import './estilos/base.css';
import './estilos/temas/americas.css';
import { mount } from 'svelte';
import App from './App.svelte';

mount(App, { target: document.getElementById('app')! });
```

`base.css`: cópia do `src/estilos/base.css` do espelho, trocando os status por `--status-disponivel`, `--status-reservado`, `--status-vendido` (mesmas cores do espelho: `#2E9E5B`, `#E2B021`, `#B0625A`) e mantendo raio, movimento, `--toque` e a transição de cor.

`App.svelte` provisório: `<div class="maquete" data-tema="americas" data-cor="claro"><p>Carregando a maquete…</p></div>`.

- [ ] **Step 4: Teste de sanidade do Vitest**

`src/lib/sanidade.test.ts`:

```ts
import { expect, test } from 'vitest';

test('o vitest roda', () => expect(1 + 1).toBe(2));
```

Run: `cd frontend && npm install && npm run test:unidade`
Expected: `1 passed`. (O `src/estilos/temas/americas.css` ainda não existe: o `build` só passa depois da Task 2.)

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/svelte.config.js frontend/tsconfig.json frontend/vitest.config.ts frontend/index.html frontend/.gitignore frontend/public/_headers frontend/src
git commit -m "feat(front): esqueleto Svelte 5 + Three.js derivado do espelho, fontes empacotadas"
```

---

### Task 2: Assets: das fontes de verdade ao `public/`

**Files:**
- Create: `frontend/scripts/copiar-assets.mjs`, `frontend/scripts/copiar-assets.test.mjs`

**Interfaces:**
- Consumes: `../.env` (`TERRENO_DIR`), `../dados/{lotes,marcos,pontos,config}.json`, `../dados/marcos/**`, `../dados/pontos/**` (fotos, quando houver), `../marca/tokens.css`, `../marca/svg/americas/*.svg`, `$TERRENO_DIR/6-PROJETOS/10-MAQUETE INTERATIVA/{loteamento,entorno,marcos,vegetacao}.glb` e `vegetacao.json`, `node_modules/three/examples/jsm/libs/draco/gltf/*`.
- Produces (layout do `public/`, consumido por todas as tasks seguintes):
  - `dados/lotes.json`, `dados/marcos.json`, `dados/pontos.json`, `dados/config.json` (cópias exatas);
  - `dados/<foto sem extensão>-mini.webp` (480 px de largura) e `dados/<foto sem extensão>.webp` (1920 px) para cada `foto`/`planta` citada em `marcos.json` e `pontos.json`;
  - `modelos/loteamento.glb`, `modelos/entorno.glb`, `modelos/vegetacao.glb` com meshopt; `modelos/marcos.glb` copiado como está (Draco); `modelos/vegetacao.json`;
  - `draco/` com o decoder do three;
  - `marca/*.svg` (só a família ativa);
  - `src/estilos/temas/americas.css` (cópia do `marca/tokens.css`).
- Exporta `fotosCitadas(marcos, pontos): string[]` e `ativa(caminho): boolean` para teste.

Ruling já tomado: os marcos ficam em Draco (meshopt deixa o arquivo com 6,6 MB, contra 2,5 MB), e o front registra os dois decoders. O contrato do plano-mestre ("o front carrega com o `DRACOLoader`") continua valendo.

- [ ] **Step 1: Teste das funções puras**

`scripts/copiar-assets.test.mjs` (roda com `node --test`):

```js
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
```

Run: `cd frontend && node --test scripts/copiar-assets.test.mjs`
Expected: FAIL (`Cannot find module` / export ausente).

- [ ] **Step 2: Implementação**

```js
// Monta o public/ a partir das fontes de verdade (spec §3): dados/, marca/ e os GLBs da pasta do
// terreno. Nada daqui é editado à mão; rode de novo depois de regerar o pipeline Python.
import { copyFile, cp, mkdir, readdir, rm, writeFile } from 'node:fs/promises';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const FRONT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const RAIZ = path.resolve(FRONT, '..');
const PUBLIC = path.join(FRONT, 'public');
const LARGURAS = { '-mini': 480, '': 1920 };

export function fotosCitadas(marcos, pontos) {
  const todas = [
    ...marcos.marcos.flatMap(m => [...m.galeria.map(g => g.foto), m.planta]),
    ...pontos.pontos.map(p => p.foto),
  ];
  return [...new Set(todas.filter(Boolean))];
}

export const ativa = caminho => caminho.replaceAll('\\', '/').includes('/svg/americas/');

function terrenoDir() {
  const env = readFileSyncTexto(path.join(RAIZ, '.env'));
  const linha = env.split(/\r?\n/).find(l => l.startsWith('TERRENO_DIR='));
  if (!linha) throw Error('TERRENO_DIR ausente no .env da raiz');
  return linha.slice('TERRENO_DIR='.length).trim().replace(/^"|"$/g, '');
}

const readFileSyncTexto = p => readFileSync(p, 'utf8');

async function comprimir(origem, destino) {
  const { NodeIO } = await import('@gltf-transform/core');
  const { ALL_EXTENSIONS } = await import('@gltf-transform/extensions');
  const { meshopt } = await import('@gltf-transform/functions');
  const { MeshoptEncoder, MeshoptDecoder } = await import('meshoptimizer');
  await MeshoptEncoder.ready;
  const io = new NodeIO().registerExtensions(ALL_EXTENSIONS)
    .registerDependencies({ 'meshopt.encoder': MeshoptEncoder, 'meshopt.decoder': MeshoptDecoder });
  const doc = await io.read(origem);
  await doc.transform(meshopt({ encoder: MeshoptEncoder, level: 'medium' }));
  await io.write(destino, doc);
}

async function webp(origem, base) {
  const sharp = (await import('sharp')).default;
  for (const [sufixo, largura] of Object.entries(LARGURAS))
    await sharp(origem).rotate().resize({ width: largura, withoutEnlargement: true }).webp({ quality: 80 }).toFile(`${base}${sufixo}.webp`);
}

async function main() {
  const maquete = path.join(terrenoDir(), '6-PROJETOS', '10-MAQUETE INTERATIVA');
  // Só as pastas geradas: o _headers do public/ é versionado e fica.
  for (const pasta of ['dados', 'modelos', 'draco', 'marca']) {
    await rm(path.join(PUBLIC, pasta), { recursive: true, force: true });
    await mkdir(path.join(PUBLIC, pasta), { recursive: true });
  }

  const json = n => JSON.parse(readFileSyncTexto(path.join(RAIZ, 'dados', n)));
  for (const n of ['lotes.json', 'marcos.json', 'pontos.json', 'config.json'])
    await copyFile(path.join(RAIZ, 'dados', n), path.join(PUBLIC, 'dados', n));
  for (const foto of fotosCitadas(json('marcos.json'), json('pontos.json'))) {
    const origem = path.join(RAIZ, 'dados', foto);
    if (!existsSync(origem)) throw Error(`foto citada e ausente: dados/${foto}`);
    const base = path.join(PUBLIC, 'dados', foto.replace(/\.[^.]+$/, ''));
    await mkdir(path.dirname(base), { recursive: true });
    await webp(origem, base);
  }

  for (const n of ['loteamento', 'entorno', 'vegetacao'])
    await comprimir(path.join(maquete, `${n}.glb`), path.join(PUBLIC, 'modelos', `${n}.glb`));
  await copyFile(path.join(maquete, 'marcos.glb'), path.join(PUBLIC, 'modelos', 'marcos.glb'));
  await copyFile(path.join(maquete, 'vegetacao.json'), path.join(PUBLIC, 'modelos', 'vegetacao.json'));
  await cp(path.join(FRONT, 'node_modules/three/examples/jsm/libs/draco/gltf'), path.join(PUBLIC, 'draco'), { recursive: true });

  const svgs = path.join(RAIZ, 'marca', 'svg', 'americas');
  for (const n of await readdir(svgs)) if (ativa(path.join(svgs, n))) await copyFile(path.join(svgs, n), path.join(PUBLIC, 'marca', n));
  await mkdir(path.join(FRONT, 'src', 'estilos', 'temas'), { recursive: true });
  await writeFile(path.join(FRONT, 'src', 'estilos', 'temas', 'americas.css'), readFileSyncTexto(path.join(RAIZ, 'marca', 'tokens.css')));
  console.log('public/ montado');
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) await main();
```

- [ ] **Step 3: Rodar os testes e o script**

Run: `cd frontend && node --test scripts/copiar-assets.test.mjs && npm run assets && ls -la public/modelos public/draco public/marca && ls public/dados/marcos/clube`
Expected: `2 passed`; `loteamento.glb` ≈ 3,3 MB, `entorno.glb` ≈ 3,0 MB, `vegetacao.glb` ≈ 9 KB, `marcos.glb` ≈ 2,5 MB; `draco_decoder.wasm` e `draco_wasm_wrapper.js` presentes; só SVGs sem "alternativa"; `01-mini.webp` e `01.webp` em `clube/`.

- [ ] **Step 4: Build passa**

Run: `cd frontend && npx vite build`
Expected: build sem erro (o `americas.css` agora existe).

- [ ] **Step 5: Commit**

```bash
git add frontend/scripts/copiar-assets.mjs frontend/scripts/copiar-assets.test.mjs
git commit -m "feat(front): public/ montado das fontes de verdade (GLBs em meshopt, fotos em WebP, marca ativa)"
```

---

### Task 3: Dados, busca, preços e mídia (lógica pura)

**Files:**
- Create: `frontend/src/lib/dados.ts`, `frontend/src/lib/lotes.ts`, `frontend/src/lib/midia.ts`, `frontend/src/lib/lotes.test.ts`, `frontend/src/lib/midia.test.ts`
- Delete: `frontend/src/lib/sanidade.test.ts`

**Interfaces:**
- Produces:

```ts
// dados.ts
export interface Lote { id: string; quadra: string; lote: string; tipo: 'residencial' | 'uso_misto'; area_m2: number;
  lados_m: number[]; frente_m: number | null; poligono: [number, number][]; inscricao_iptu?: string;
  preco_total?: number; preco_m2?: number; status?: 'disponivel' | 'reservado' | 'vendido' }
export interface Config { mostrarPrecos: boolean; tabelaPrecos: { nome: string; referencia: string };
  vista: Partial<Record<'retrato' | 'paisagem', Vista>>; estande: { altura_m: number } }
export interface Vista { azimute: number; elevacao: number; distancia: number }
export interface Foto { foto: string; legenda: string }
export interface Marco { id: string; nome: string; x: number; y: number; z: number; objeto: string | null;
  galeria: Foto[]; planta: string | null; lat: number; lon: number; pegada?: [number, number][] }
export interface PontoBruto { nome: string; categoria: string; lat: number; lon: number; x: number; y: number;
  km: number; minutos_carro: number; faixa: 'proximo' | 'distante'; foto: string | null; credito: string | null;
  licenca: string | null; licenca_url: string | null; fonte_foto: string | null }
export interface Dados { lotes: Lote[]; marcos: Marco[]; pontos: PontoBruto[]; fontesPontos: string; config: Config }
export async function carregarDados(base: URL): Promise<Dados>
// lotes.ts
export function buscar(lotes: Lote[], termo: string): Lote[]
export function loteDaUrl(lotes: Lote[], busca: string): Lote | null   // ?lote=
export function precosVisiveis(config: Pick<Config, 'mostrarPrecos'>, busca: string): boolean
export function rotuloCurto(l: Lote): string      // "Q07 · L04", "QH · L01"
export function rotuloLongo(l: Lote): string      // "Quadra 07 · Lote 04"
export const ROTULO_TIPO: Record<Lote['tipo'], string>   // "Residencial", "Uso misto"
export function metros(n: number, casas?: number): string // "732,01 m²" via formatarArea; "35,56 m"
export function formatarArea(n: number): string
export function reais(n: number): string
// midia.ts
export function midia(foto: string, tamanho: 'mini' | 'cheia'): string // 'dados/marcos/clube/01-mini.webp'
```

Ruling: `config.json` ganha `vista` e `estande.altura_m` (ajustes de apresentação, editados à mão; spec §6 já põe o `config.json` como editado à mão). Valores iniciais na Task 4; o ajuste fino fica para a sessão de revisão visual.

- [ ] **Step 1: Testes**

`src/lib/lotes.test.ts`:

```ts
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
```

`src/lib/midia.test.ts`:

```ts
import { expect, test } from 'vitest';
import { midia } from './midia';

test('foto do JSON vira o WebP do tamanho pedido', () => {
  expect(midia('marcos/clube/01.jpg', 'mini')).toBe('dados/marcos/clube/01-mini.webp');
  expect(midia('marcos/estande/planta.jpg', 'cheia')).toBe('dados/marcos/estande/planta.webp');
});
```

Run: `cd frontend && npm run test:unidade`
Expected: FAIL (módulos ausentes).

- [ ] **Step 2: Implementação**

`dados.ts` (tipos acima) e:

```ts
export async function carregarDados(base: URL): Promise<Dados> {
  const json = async <T>(n: string): Promise<T> => {
    const r = await fetch(new URL(`dados/${n}`, base));
    if (!r.ok) throw Error(`dados/${n}`);
    return r.json() as Promise<T>;
  };
  const [lotes, marcos, pontos, config] = await Promise.all([
    json<{ lotes: Lote[] }>('lotes.json'), json<{ marcos: Marco[] }>('marcos.json'),
    json<{ pontos: PontoBruto[]; fontes: string }>('pontos.json'), json<Config>('config.json'),
  ]);
  return { lotes: lotes.lotes, marcos: marcos.marcos, pontos: pontos.pontos, fontesPontos: pontos.fontes, config };
}
```

`lotes.ts`:

```ts
import type { Config, Lote } from './dados';

const norm = (s: string) => s.trim().toUpperCase();
/** "07" e "7" são a mesma quadra; "H" fica "H". */
const quadra = (s: string) => (/^\d+$/.test(s) ? s.padStart(2, '0') : s);

/** Quadra e lote em qualquer formato que o corretor digita: "7 4", "Q7L4", "q07 l04", "07-04". */
export function buscar(lotes: Lote[], termo: string): Lote[] {
  const m = norm(termo).match(/^Q?\s*([0-9]{1,2}|[A-Z])(?:\s*[-\s]\s*|\s*L\s*)?([0-9]{1,2})?$/);
  if (!m) return [];
  const q = quadra(m[1]!);
  const n = m[2]?.padStart(2, '0');
  return lotes.filter(l => l.quadra === q && (!n || l.lote === n)).sort((a, b) => a.id.localeCompare(b.id));
}

export function loteDaUrl(lotes: Lote[], busca: string): Lote | null {
  const id = new URLSearchParams(busca).get('lote');
  return id ? lotes.find(l => l.id === norm(id)) ?? null : null;
}

export function precosVisiveis(config: Pick<Config, 'mostrarPrecos'>, busca: string): boolean {
  return config.mostrarPrecos && new URLSearchParams(busca).get('precos') !== '0';
}

export const rotuloCurto = (l: Lote) => `Q${l.quadra} · L${l.lote}`;
export const rotuloLongo = (l: Lote) => `Quadra ${l.quadra} · Lote ${l.lote}`;
export const ROTULO_TIPO: Record<Lote['tipo'], string> = { residencial: 'Residencial', uso_misto: 'Uso misto' };

const n2 = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
export const metros = (n: number) => `${n2.format(n)} m`;
export const formatarArea = (n: number) => `${n2.format(n)} m²`;
export const reais = (n: number) => n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });
```

A regex aceita "7 4" (separador espaço), "07-04", "Q7L4" e "q07 l04"; "7" sozinho casa sem `m[2]`. Se algum caso do teste falhar, ajuste a regex, não o teste.

`midia.ts`:

```ts
/** Foto citada no JSON (relativa a dados/) → WebP gerado pelo copiar-assets. */
export const midia = (foto: string, tamanho: 'mini' | 'cheia') =>
  `dados/${foto.replace(/\.[^.]+$/, '')}${tamanho === 'mini' ? '-mini' : ''}.webp`;
```

- [ ] **Step 3: Rodar**

Run: `cd frontend && npm run test:unidade`
Expected: todos passam (busca 9, url 1, preços 1, rótulos 1, mídia 1).

- [ ] **Step 4: Commit**

```bash
git rm frontend/src/lib/sanidade.test.ts
git add frontend/src/lib
git commit -m "feat(front): busca de lote, regra dos preços, ?lote= e caminhos das fotos, com testes"
```

---

### Task 4: Cena: modelo, câmera, luz e lotes

**Files:**
- Create: `frontend/src/lib/cena/cena.ts`, `frontend/src/lib/cena/ceu.ts`
- Modify: `dados/config.json` (ganha `vista` e `estande`), `frontend/src/App.svelte` (monta a cena)

**Interfaces:**
- Consumes: `public/modelos/{loteamento,marcos}.glb`, `public/draco/`, `Dados` (Task 3).
- Produces:

```ts
export type Tela = { x: number; y: number };
export type Formato = 'retrato' | 'paisagem';
export interface Cena {
  montar(el: HTMLElement): void;
  inicio(): void;
  enquadrar(id: string): void;              // lote
  selecionar(id: string | null): void;      // realce de seleção
  aproximar(fator: number): void;
  ceu(modo: 'claro' | 'escuro'): void;
  cores(): Record<Lote['tipo'], string>;    // cor de cada tipo, lida dos materiais do GLB (legenda)
  descartar(): void;
}
export interface Opcoes {
  base: URL; dados: Dados;
  aoEscolher(id: string | null): void;            // toque/clique sem arrasto num lote, ou no vazio
  aoPassar(rotulo: { id: string; tela: Tela } | null): void; // hover no desktop
  aoMoverEtiqueta(tela: Tela | null): void;       // topo do lote selecionado
  aoGirar(graus: number): void;                   // rumo da câmera, para a bússola
}
export async function criarCena(o: Opcoes): Promise<Cena>
```

Lotes são as malhas do GLB cujo nome casa `/^Q(\d{2}|[A-Z])L\d{2}$/`; o pivô (posição do nó) é o centro do topo do lote (contrato do plano-mestre). Não há caixas instanciadas nem manifest.

- [ ] **Step 1: `config.json`** — acrescentar (valores iniciais; ajuste fino na revisão visual):

```json
  "vista": {
    "paisagem": { "azimute": 200, "elevacao": 32, "distancia": 1.0 },
    "retrato": { "azimute": 200, "elevacao": 40, "distancia": 1.25 }
  },
  "estande": { "altura_m": 4.5 }
```

`azimute` é o rumo da câmera a partir do centro dos lotes (graus do norte, horário): 200 põe a câmera ao sul-sudoeste olhando para o mar ao norte. `distancia` é múltiplo da distância que enquadra a caixa dos lotes.

Rodar `uv run pytest -q` na raiz: se algum teste do pipeline confere as chaves do `config.json`, atualizá-lo junto.

- [ ] **Step 2: `ceu.ts`** — cópia do `src/lib/cena/ceu.ts` do espelho, sem mudança de lógica. A paleta `claro.baixo` e `escuro.baixo` é a de fim de tarde que a cena usa fixa.

- [ ] **Step 3: `cena.ts`**

```ts
// A cena 3D atrás de uma interface pequena: a UI nunca entra no loop de render (ADR-0001 do espelho).
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { Dados, Lote, Vista } from '../dados';
import { Ceu } from './ceu';

const LOTE = /^Q(\d{2}|[A-Z])L\d{2}$/;
const STATUS: Record<NonNullable<Lote['status']>, string> = { disponivel: '#2E9E5B', reservado: '#E2B021', vendido: '#B0625A' };
// Luz fixa de fim de tarde (spec §5): sol baixo a oeste-noroeste, quente.
const SOL = { azimute: 285, altitude: 24 };

export function loader(base: URL): GLTFLoader {
  const draco = new DRACOLoader().setDecoderPath(new URL('draco/', base).href);
  return new GLTFLoader().setDRACOLoader(draco).setMeshoptDecoder(MeshoptDecoder);
}

/** Direção a partir de azimute (graus do norte, horário) e altura: norte = −Z, leste = +X. */
export function direcao(azimute: number, altura: number): THREE.Vector3 {
  const az = THREE.MathUtils.degToRad(azimute);
  const alt = THREE.MathUtils.degToRad(altura);
  return new THREE.Vector3(Math.sin(az) * Math.cos(alt), Math.sin(alt), -Math.cos(az) * Math.cos(alt));
}

export async function criarCena(o: Opcoes): Promise<Cena> {
  const gltf = loader(o.base);
  const [lot, mar] = await Promise.all([
    gltf.loadAsync(new URL('modelos/loteamento.glb', o.base).href),
    gltf.loadAsync(new URL('modelos/marcos.glb', o.base).href),
  ]);
  const cena = new THREE.Scene();
  cena.add(lot.scene, mar.scene);

  const lotes = new Map<string, THREE.Mesh>();
  lot.scene.traverse(x => { if ((x as THREE.Mesh).isMesh && LOTE.test(x.name)) lotes.set(x.name, x as THREE.Mesh); });
  const porId = new Map(o.dados.lotes.map(l => [l.id, l]));
  // Status, quando o JSON trouxer, pinta o lote com a cor fixa; senão fica a cor do tipo do GLB.
  for (const [id, malha] of lotes) {
    const s = porId.get(id)?.status;
    const m = (malha.material as THREE.MeshStandardMaterial).clone();
    if (s) m.color.set(STATUS[s]);
    malha.material = m;
    malha.userData.base = m;
  }

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  const el = renderer.domElement;
  el.setAttribute('role', 'img');
  el.setAttribute('aria-label', 'Maquete 3D do loteamento; arraste para girar e pince para aproximar');

  const camera = new THREE.PerspectiveCamera(40, 1, 1, 20000);
  const controles = new OrbitControls(camera, el);
  controles.enableDamping = true;
  controles.minDistance = 25;
  controles.maxDistance = 2500;
  controles.maxPolarAngle = Math.PI * 0.47;
  // Toque como no UFCIM-FRONT3D: um dedo gira, dois aproximam e arrastam.
  controles.touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN };

  const ceuLuz = new THREE.HemisphereLight(0xfff3e2, 0x6f6a5c, 1.6);
  const sol = new THREE.DirectionalLight(0xffd2a0, 2.6);
  sol.position.copy(direcao(SOL.azimute, SOL.altitude).multiplyScalar(1000));
  const ceu = new Ceu(15000);
  ceu.sol(direcao(SOL.azimute, SOL.altitude), 0.55, 0);
  cena.add(ceuLuz, sol, ceu.malha);

  // Caixa dos lotes: centro e distância justa da vista inicial.
  const caixa = new THREE.Box3();
  for (const m of lotes.values()) caixa.expandByObject(m);
  const centro = caixa.getCenter(new THREE.Vector3());
  const tamanho = caixa.getSize(new THREE.Vector3());
  const formato = (): 'retrato' | 'paisagem' => (camera.aspect < 1 ? 'retrato' : 'paisagem');
  const PADRAO: Vista = { azimute: 200, elevacao: 35, distancia: 1.1 };
  function distanciaJusta() {
    const v = THREE.MathUtils.degToRad(camera.fov) / 2;
    return Math.max(tamanho.z / (2 * Math.tan(v)), tamanho.x / (2 * Math.tan(v) * camera.aspect));
  }
  function inicio() {
    const { azimute, elevacao, distancia } = o.dados.config.vista?.[formato()] ?? PADRAO;
    controles.target.copy(centro);
    camera.position.copy(centro).addScaledVector(direcao(azimute, elevacao), distanciaJusta() * distancia);
    controles.update();
  }
  function enquadrar(id: string) {
    const m = lotes.get(id);
    if (!m) return;
    abertura = false;
    const alvo = m.getWorldPosition(new THREE.Vector3());
    const rumo = camera.position.clone().sub(controles.target).setY(0).normalize();
    const d = camera.aspect < 1 ? 140 : 100;
    controles.target.copy(alvo);
    camera.position.copy(alvo).addScaledVector(rumo, d * 0.75).setY(alvo.y + d * 0.66);
    controles.update();
  }

  // Realce: hover clareia; seleção pinta com o acento. Material próprio por estado, sem tocar o original.
  const realce = (m: THREE.Mesh, cor: number, forca: number) => {
    const novo = (m.userData.base as THREE.MeshStandardMaterial).clone();
    novo.emissive.set(cor);
    novo.emissiveIntensity = forca;
    m.material = novo;
  };
  const restaurar = (m: THREE.Mesh) => {
    if (m.material !== m.userData.base) (m.material as THREE.Material).dispose();
    m.material = m.userData.base;
  };
  let selecionado: string | null = null;
  let passando: string | null = null;
  function aplicarRealces() {
    for (const [id, m] of lotes) {
      if (id === selecionado) realce(m, 0x64461d, 0.55);
      else if (id === passando) realce(m, 0xe4c89b, 0.35);
      else restaurar(m);
    }
  }

  const raio = new THREE.Raycaster();
  const alvos = [...lotes.values()];
  function loteEm(x: number, y: number): string | null {
    const r = el.getBoundingClientRect();
    raio.setFromCamera(new THREE.Vector2(((x - r.left) / r.width) * 2 - 1, 1 - ((y - r.top) / r.height) * 2), camera);
    // Só o que está na frente vale: um marco ou o terreno à frente do lote bloqueia.
    const acerto = raio.intersectObjects([...alvos, mar.scene], true)[0];
    return acerto && LOTE.test(acerto.object.name) ? acerto.object.name : null;
  }

  // Toque sem arrasto escolhe; arrasto é câmera (como no espelho).
  let gesto: { id: number; x: number; y: number; moveu: boolean } | null = null;
  const ponteiros = new Set<number>();
  el.addEventListener('pointerdown', e => {
    ponteiros.add(e.pointerId);
    gesto = ponteiros.size === 1 ? { id: e.pointerId, x: e.clientX, y: e.clientY, moveu: false } : null;
  });
  let pendente: PointerEvent | null = null;
  el.addEventListener('pointermove', e => {
    if (gesto && Math.hypot(e.clientX - gesto.x, e.clientY - gesto.y) > 6) gesto.moveu = true;
    if (e.pointerType === 'mouse' && !ponteiros.size) pendente = e; // hover: resolvido no quadro
  });
  el.addEventListener('pointerleave', () => { pendente = null; if (passando) { passando = null; aplicarRealces(); o.aoPassar(null); } });
  el.addEventListener('pointerup', e => {
    ponteiros.delete(e.pointerId);
    const g = gesto;
    gesto = null;
    if (ponteiros.size || !g || g.id !== e.pointerId || g.moveu) return;
    o.aoEscolher(loteEm(e.clientX, e.clientY));
  });
  el.addEventListener('pointercancel', e => { ponteiros.delete(e.pointerId); gesto = null; });
  let abertura = true;
  controles.addEventListener('start', () => (abertura = false));

  let container: HTMLElement | null = null;
  const redimensionar = new ResizeObserver(() => {
    if (!container) return;
    const { clientWidth: w, clientHeight: h } = container;
    if (!w || !h) return;
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    if (abertura) inicio();
  });

  const projetar = (p: THREE.Vector3): Tela | null => {
    const v = p.clone().project(camera);
    if (v.z > 1) return null;
    return { x: ((v.x + 1) / 2) * el.clientWidth, y: ((1 - v.y) / 2) * el.clientHeight };
  };
  let ultimaEtiqueta = '';
  let ultimoRumo = NaN;
  renderer.setAnimationLoop(() => {
    if (!container) return;
    controles.update();
    // near acompanha a altura: a placa a 0,25 m do terreno não briga na profundidade de longe.
    const perto = THREE.MathUtils.clamp((camera.position.y - centro.y) * 0.2, 1, 200);
    if (Math.abs(perto - camera.near) > 0.5) { camera.near = perto; camera.updateProjectionMatrix(); }
    ceu.malha.position.copy(camera.position);
    if (pendente) {
      const e = pendente;
      pendente = null;
      const id = loteEm(e.clientX, e.clientY);
      if (id !== passando) {
        passando = id;
        aplicarRealces();
        const r = el.getBoundingClientRect();
        o.aoPassar(id ? { id, tela: { x: e.clientX - r.left, y: e.clientY - r.top } } : null);
      }
      el.style.cursor = id ? 'pointer' : '';
    }
    renderer.render(cena, camera);
    const m = selecionado ? lotes.get(selecionado) : undefined;
    const tela = m ? projetar(m.getWorldPosition(new THREE.Vector3())) : null;
    const chave = tela ? `${Math.round(tela.x)},${Math.round(tela.y)}` : '';
    if (chave !== ultimaEtiqueta) { ultimaEtiqueta = chave; o.aoMoverEtiqueta(tela); }
    const d = camera.position.clone().sub(controles.target);
    const rumo = Math.round((THREE.MathUtils.radToDeg(Math.atan2(d.x, -d.z)) + 360) % 360);
    if (rumo !== ultimoRumo) { ultimoRumo = rumo; o.aoGirar(rumo); }
  });

  const corDo = (tipo: Lote['tipo']) => {
    const exemplo = o.dados.lotes.find(l => l.tipo === tipo && !l.status);
    const m = exemplo && lotes.get(exemplo.id);
    return m ? `#${(m.userData.base as THREE.MeshStandardMaterial).color.getHexString()}` : 'transparent';
  };

  return {
    montar(e) { container = e; e.prepend(el); redimensionar.observe(e); },
    inicio() { abertura = true; inicio(); },
    enquadrar,
    selecionar(id) { selecionado = id; aplicarRealces(); },
    aproximar(f) {
      abertura = false;
      const d = camera.position.clone().sub(controles.target).multiplyScalar(f);
      camera.position.copy(controles.target).add(d.setLength(THREE.MathUtils.clamp(d.length(), controles.minDistance, controles.maxDistance)));
      controles.update();
    },
    ceu(modo) { ceu.cor(modo); },
    cores: () => ({ residencial: corDo('residencial'), uso_misto: corDo('uso_misto') }),
    descartar() {
      redimensionar.disconnect();
      renderer.setAnimationLoop(null);
      controles.dispose();
      ceu.descartar();
      renderer.dispose();
      el.remove();
    },
  };
}
```

(Os tipos `Tela`, `Cena` e `Opcoes` do bloco Interfaces vão no topo do arquivo.) A Task 6 acrescenta marcos e a Task 7, o entorno, a este mesmo módulo: mantenha `cena`, `camera`, `controles`, `projetar` e o loop num formato em que um bloco a mais se encaixe.

- [ ] **Step 4: `App.svelte` mínimo monta a cena** — `onMount`: `const base = new URL('./', location.href)`; `dados = await carregarDados(base)`; `cena = await criarCena({ base, dados, aoEscolher: () => {}, aoPassar: () => {}, aoMoverEtiqueta: () => {}, aoGirar: () => {} })`; `cena.montar(palco)`; em erro, `fase = 'erro'` com o texto "Não foi possível abrir a maquete". Estilo do `.maquete`/`.cena` igual ao `.espelho`/`.cena` do espelho, com `container: maquete / size`.

- [ ] **Step 5: Conferir no navegador (sem e2e ainda)**

Run: `cd frontend && npm run build && npx vite preview` e, em outro terminal, um script Playwright curto no scratchpad que abre `http://127.0.0.1:4173`, espera `getByRole('img', { name: /Maquete 3D/ })` e salva um screenshot.
Expected: a maquete aparece com o céu, os lotes coloridos por tipo e os marcos; nenhum erro no console. O screenshot vai para o scratchpad (não é QA visual: só confere que a cena desenha).

- [ ] **Step 6: Commit**

```bash
git add dados/config.json frontend/src
git commit -m "feat(front): cena com loteamento e marcos (meshopt + Draco), câmera de toque, luz de fim de tarde e lotes clicáveis"
```

---

### Task 5: Folha, Ficha, busca, URL e preços

**Files:**
- Create: `frontend/src/componentes/{Folha,Icone,PlantaAmpliada,Marca,Controles,Bussola,Legenda,BoasVindas,Busca,Ficha,Contorno}.svelte`, `frontend/src/lib/dispositivo.ts`, `frontend/playwright.config.ts`, `frontend/e2e/jornadas.spec.ts`
- Modify: `frontend/src/App.svelte`

**Interfaces:**
- Consumes: `Cena` (Task 4), `lotes.ts`, `dados.ts` (Task 3).
- Produces: estado do App (`conteudo: 'busca' | 'ficha' | 'boas-vindas' | 'marco' | 'entorno' | 'ponto'`, `batente`), usado pelas Tasks 6 e 7; `Folha` com `rotulo` acessível (região "Ficha do lote Q07 · L04").

Ruling: os `lados_m` do DWG não casam um a um com as arestas do polígono (os arcos viram dezenas de arestas curtas). Por isso a miniatura desenha o contorno, e as cotas saem numa lista "Lados" logo abaixo, com a frente destacada.

- [ ] **Step 1: Copiar do espelho sem mudança de lógica:** `Folha.svelte`, `Icone.svelte` (mantém `buscar`, `fechar`, `voltar`, `enquadrar`, `entorno`, `seta`, `mais`, `menos`, `ajuda`, `externo`, `link`, `lua`, `claro`; acrescenta `camera`, `mapa` e `foto`), `PlantaAmpliada.svelte`, e `dispositivo.ts` reduzido a `primeiraVisita` e `modoCor`, com chaves `maquete:visitou` e `maquete:cor`. Nas três peças, troque `@container espelho` por `@container maquete`.

Ícones novos (grade 24, traço 1,6):

```ts
camera: '<path d="M4 8.5h3l1.5-2h7l1.5 2h3v10H4z"/><circle cx="12" cy="13" r="3.2"/>',
mapa: '<path d="M9 4.5l-5 2v13l5-2 6 2 5-2v-13l-5 2z"/><path d="M9 4.5v13M15 6.5v13"/>',
foto: '<rect x="3.5" y="5" width="17" height="14" rx="1.5"/><circle cx="9" cy="10" r="1.8"/><path d="M20.5 16l-5-5-8 8"/>',
```

- [ ] **Step 2: Componentes novos**

`Marca.svelte` (canto superior esquerdo, no lugar do Carimbo do espelho): `<img src={escuro ? 'marca/produto-horizontal-negativo.svg' : 'marca/produto-horizontal-positivo.svg'} alt="Cidade das Américas — Residencial Cumbuco">`, num cartão `--tema-papel` de 58 px de altura (62 px a partir de 900 px), como o `.carimbo .marca` do espelho.

`Bussola.svelte`: botão redondo de 44 px com um "N" e uma agulha, `style:transform="rotate({-graus}deg)"` na agulha. Recebe `graus` (rumo da câmera, do `aoGirar`) e `aoClicar` (volta à vista inicial). `aria-label="Norte; voltar à vista inicial"`.

`Legenda.svelte` (`aria-label="Legenda"`): amostras dos tipos com as cores de `cena.cores()` ("Residencial", "Uso misto"), e a ressalva "Maquete ilustrativa, não é projeto executivo." (a partir de 900 px). Se algum lote tiver `status`, acrescenta as três amostras de status.

`BoasVindas.svelte`: logo vertical (`produto-vertical-positivo|negativo.svg`, 120 px de largura), título "Como explorar" e os três gestos do espelho com textos de lote: "Arraste para girar", "Pince para aproximar", "Toque num lote — a ficha abre aqui embaixo". Sem as amostras de status.

`Controles.svelte`: grupos (enquadrar, entorno), (mais, menos), (cor, ajuda), mais a `Bussola` no topo; sem os grupos de corretor. Botão "Buscar lote" (`aria-label="Buscar lote"`) no primeiro grupo, aberto a todos (aqui não há chrome de corretor).

`Busca.svelte`: o do espelho, com `aria-label="Quadra e lote"`, `placeholder="Quadra e lote, ex.: 7 4"`, `inputmode="text"`; resultados mostram `rotuloCurto`, `ROTULO_TIPO` e `formatarArea`; contagem "1 lote" / "N lotes" / "Nenhum lote encontrado".

`Contorno.svelte`: SVG 240×160 com o polígono normalizado (bbox → caixa com 12 px de margem, y invertido), traço `--tema-tinta`, preenchimento `--tema-areia`; `role="img"` e `aria-label="Contorno do lote, {área}"`.

`Ficha.svelte`:

```svelte
<script lang="ts">
  import type { Config, Lote } from '../lib/dados';
  import { formatarArea, metros, reais, ROTULO_TIPO, rotuloLongo } from '../lib/lotes';
  import Contorno from './Contorno.svelte';
  import Icone from './Icone.svelte';

  let { lote, config, precos, aoFechar }: { lote: Lote; config: Config; precos: boolean; aoFechar: () => void } = $props();
  let copiado = $state(false);
  const temPreco = $derived(precos && lote.preco_total !== undefined);
  const STATUS = { disponivel: 'Disponível', reservado: 'Reservado', vendido: 'Vendido' } as const;

  async function compartilhar() {
    const url = new URL(location.href);
    url.search = `?lote=${lote.id}`;
    const dados = { title: rotuloLongo(lote), url: url.href };
    if (navigator.share) await navigator.share(dados).catch(() => {});
    else { await navigator.clipboard?.writeText(url.href); copiado = true; setTimeout(() => (copiado = false), 2000); }
  }
</script>

<div class="barra"><span></span><button class="fechar" aria-label="Fechar ficha" onclick={aoFechar}><Icone nome="fechar" tamanho={18} /></button></div>
<h2 class="titulo">{rotuloLongo(lote)}</h2>
<p class="tipo">{ROTULO_TIPO[lote.tipo]}{#if lote.status} · <span class="status {lote.status}">{STATUS[lote.status]}</span>{/if}</p>

<dl class="campos">
  <div><dt>Área</dt><dd>{formatarArea(lote.area_m2)}</dd></div>
  {#if lote.frente_m !== null}<div><dt>Frente</dt><dd>{metros(lote.frente_m)}</dd></div>{/if}
  {#if lote.inscricao_iptu}<div><dt>Inscrição IPTU</dt><dd>{lote.inscricao_iptu}</dd></div>{/if}
</dl>

<figure class="contorno"><Contorno poligono={lote.poligono} area={formatarArea(lote.area_m2)} />
  <figcaption>Lados: {lote.lados_m.map(n => metros(n)).join(' · ')}</figcaption></figure>

{#if temPreco}
  <section class="preco" aria-label="Preço">
    <p class="total">{reais(lote.preco_total!)}</p>
    {#if lote.preco_m2 !== undefined}<p class="m2">{reais(lote.preco_m2)}/m²</p>{/if}
    <p class="carimbo">Tabela {config.tabelaPrecos.nome} · ref. {config.tabelaPrecos.referencia}</p>
  </section>
{/if}

<button class="btn" onclick={compartilhar}><Icone nome="link" tamanho={18} />{copiado ? 'Link copiado' : 'Compartilhar'}</button>
```

Estilos: os de `.campos`, `dt`, `dd`, `.barra`, `.fechar` do Ficha do espelho; `.titulo` em `--tema-fonte-display` 30 px; `.btn` como o `.btn` do App do espelho, com borda `--tema-acento`.

- [ ] **Step 3: `App.svelte` completo** — o `App.svelte` do espelho, menos API/sincronia, corretor, sol, explorar, carimbo e aviso. O fluxo:

1. `onMount`: carrega `dados`, cria a cena com `aoEscolher: id => (id ? abrirFicha(id, false) : fecharFicha())`, `aoPassar: r => (hover = r)`, `aoMoverEtiqueta: t => (etiqueta = t)`, `aoGirar: g => (rumo = g)`. Depois, `const inicial = loteDaUrl(dados.lotes, location.search)`: se houver, `abrirFicha(inicial.id, true)`; senão, na primeira visita, `conteudo = 'boas-vindas'` com `batente = 'espiar'`.
2. `precos = precosVisiveis(dados.config, location.search)`, calculado uma vez.
3. `abrirFicha(id, enquadrar)`: `selecionado = id`, `conteudo = 'ficha'`, `batente = largura ≥ 900 ? 'cheia' : 'espiar'`, `cena.selecionar(id)`, e `cena.enquadrar(id)` quando vier da busca ou da URL. Atualiza a URL com `history.replaceState(null, '', '?lote=' + id)`, preservando `precos=0` se estiver lá.
4. `fecharFicha()`: limpa a seleção e a URL (`?precos=0` fica, se estava) e volta à `busca` com `batente = 'some'`.
5. Etiqueta HTML do lote selecionado (`rotuloCurto`) no ponto do `aoMoverEtiqueta`, e rótulo de hover no `hover.tela`; os dois com `aria-hidden="true"`, no estilo `.etiqueta` do espelho.
6. `$effect` aplica `cena.ceu(cor)`; `data-cor` vem do `prefers-color-scheme` ou da escolha guardada (`modoCor`), com o botão de cor do espelho.
7. Rótulo da Folha: ficha → `Ficha do lote ${rotuloCurto(lote)}`; boas-vindas → "Como explorar"; busca → "Busca de lote".

- [ ] **Step 4: Playwright e jornadas do lote**

`playwright.config.ts`: o do espelho, com `timezoneId: 'America/Fortaleza'`, os dois projetos (celular-retrato e tablet-paisagem) e `webServer` igual (`npm run build && npm run preview`, porta 4173).

`e2e/jornadas.spec.ts`:

```ts
import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';

const LOTES = JSON.parse(readFileSync(new URL('../public/dados/lotes.json', import.meta.url), 'utf8')).lotes as
  { id: string; quadra: string; lote: string; area_m2: number; inscricao_iptu?: string }[];
const area = (n: number) => `${n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} m²`;
const L = LOTES.find(l => l.id === 'Q07L04')!;

async function jaVisitou(page: Page) {
  await page.addInitScript(() => localStorage.setItem('maquete:visitou', '1'));
}
const ficha = (page: Page, id = 'Q07 · L04') => page.getByRole('region', { name: `Ficha do lote ${id}` });

test('1. a maquete abre com a marca, a legenda e sem o nome guardado', async ({ page }) => {
  await jaVisitou(page);
  await page.goto('./');
  await expect(page.getByRole('img', { name: /Maquete 3D/ })).toBeVisible();
  await expect(page.getByRole('img', { name: /Cidade das Américas/ })).toBeVisible();
  await expect(page.getByLabel('Legenda')).toContainText('Residencial');
  expect((await page.content()).toLowerCase()).not.toContain('alternativa');
});

test('2. a primeira visita mostra como explorar, uma vez só', async ({ page }) => {
  await page.goto('./');
  await expect(page.getByRole('region', { name: 'Como explorar' })).toBeVisible();
  await page.getByRole('button', { name: 'Começar' }).click();
  await page.reload();
  await expect(page.getByRole('region', { name: 'Como explorar' })).toHaveCount(0);
});

test('3. a busca "7 4" abre a ficha do Q07L04 com área e IPTU do JSON', async ({ page }) => {
  await jaVisitou(page);
  await page.goto('./');
  await page.getByRole('button', { name: 'Buscar lote' }).click();
  await page.getByRole('textbox', { name: 'Quadra e lote' }).fill('7 4');
  await page.getByRole('button', { name: /Q07 · L04/ }).click();
  await expect(ficha(page).getByRole('heading', { name: 'Quadra 07 · Lote 04' })).toBeVisible();
  await expect(ficha(page)).toContainText(area(L.area_m2));
  if (L.inscricao_iptu) await expect(ficha(page)).toContainText(L.inscricao_iptu);
  await expect(page).toHaveURL(/\?lote=Q07L04$/);
});

test('4. ?lote= abre direto na ficha; id inválido abre a vista inicial sem ficha', async ({ page }) => {
  await jaVisitou(page);
  await page.goto('./?lote=Q07L04');
  await expect(ficha(page)).toBeVisible();
  await page.goto('./?lote=Q99L99');
  await expect(page.getByRole('img', { name: /Maquete 3D/ })).toBeVisible();
  await expect(page.getByRole('region', { name: /Ficha do lote/ })).toHaveCount(0);
});

test('5. o clique no lote enquadrado abre a ficha dele', async ({ page }) => {
  await jaVisitou(page);
  await page.goto('./?lote=Q07L04');
  await ficha(page).getByRole('button', { name: 'Fechar ficha' }).click();
  await expect(ficha(page)).toHaveCount(0);
  // Enquadrar põe o pivô do lote no centro da tela.
  const tela = await page.getByRole('img', { name: /Maquete 3D/ }).boundingBox();
  await page.mouse.click(tela!.x + tela!.width / 2, tela!.y + tela!.height / 2);
  await expect(ficha(page)).toBeVisible();
});

// Regra dos preços (spec §6), com config e lote interceptados.
for (const [mostrar, busca, visivel] of [[false, '', false], [true, '', true], [true, '&precos=0', false]] as const) {
  test(`6. preços: mostrarPrecos=${mostrar}${busca || ' sem parâmetro'} → ${visivel ? 'visíveis' : 'escondidos'}`, async ({ page }) => {
    await jaVisitou(page);
    await page.route('**/dados/config.json', async r => {
      const c = await (await r.fetch()).json();
      await r.fulfill({ json: { ...c, mostrarPrecos: mostrar } });
    });
    await page.route('**/dados/lotes.json', async r => {
      const d = await (await r.fetch()).json();
      d.lotes = d.lotes.map((l: { id: string }) => (l.id === 'Q07L04' ? { ...l, preco_total: 250000, preco_m2: 500 } : l));
      await r.fulfill({ json: d });
    });
    await page.goto(`./?lote=Q07L04${busca}`);
    await expect(ficha(page)).toBeVisible();
    await expect(ficha(page).getByRole('region', { name: 'Preço' })).toHaveCount(visivel ? 1 : 0);
    if (visivel) await expect(ficha(page)).toContainText(/Tabela .+ · ref\./);
  });
}

test('7. lote sem IPTU não mostra o campo', async ({ page }) => {
  const sem = LOTES.find(l => !l.inscricao_iptu)!;
  await jaVisitou(page);
  await page.goto(`./?lote=${sem.id}`);
  await expect(page.getByRole('region', { name: /Ficha do lote/ })).toBeVisible();
  await expect(page.getByRole('region', { name: /Ficha do lote/ })).not.toContainText('Inscrição IPTU');
});
```

O teste 5 falha se o lote ficar atrás da Folha no celular: nesse caso, `enquadrar` sobe o alvo na tela, deslocando o `target` para baixo da metade da folha espiada, e o teste clica no ponto que a cena expõe pela etiqueta (`.etiqueta`, posição do pivô). A correção vai no código, não no teste.

Run: `cd frontend && npx playwright install chromium && npm test`
Expected: os testes 1 a 7 passam nos dois projetos (celular-retrato e tablet-paisagem).

- [ ] **Step 5: `npm run check` sem erros, e commit**

```bash
git add frontend/src frontend/e2e frontend/playwright.config.ts
git commit -m "feat(front): folha, ficha do lote, busca por quadra e lote, ?lote=, regra dos preços e e2e"
```

---

### Task 6: Marcos: ícones, volume do estande e galeria

**Files:**
- Create: `frontend/src/componentes/Marcos.svelte`, `frontend/src/componentes/Galeria.svelte`
- Modify: `frontend/src/lib/cena/cena.ts`, `frontend/src/App.svelte`, `frontend/e2e/jornadas.spec.ts`

**Interfaces:**
- Consumes: `Marco` (Task 3), `midia()` (Task 3), `config.estande.altura_m`.
- Produces: em `Opcoes`, `aoMoverMarcos(telas: { id: string; tela: Tela | null }[])`; em `Cena`, `enquadrarMarco(id: string)`.

- [ ] **Step 1: Cena** — dentro de `criarCena`:

```ts
// Estande: não tem modelo; o volume simplificado é a pegada do KMZ extrudada (spec §7.1).
for (const m of o.dados.marcos) {
  if (m.objeto || !m.pegada) continue;
  const forma = new THREE.Shape(m.pegada.map(([x, y]) => new THREE.Vector2(x, y)));
  const g = new THREE.ExtrudeGeometry(forma, { depth: o.dados.config.estande.altura_m, bevelEnabled: false }).rotateX(-Math.PI / 2);
  const volume = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: 0xe9e2d6, roughness: 0.9 }));
  volume.position.y = m.z;
  volume.name = `Marco_${m.id}`;
  cena.add(volume);
}
// Ícone flutuante: 12 m acima do ponto do marco.
const ancoras = o.dados.marcos.map(m => ({ id: m.id, p: new THREE.Vector3(m.x, m.z + 12, -m.y) }));
```

O `rotateX(-π/2)` leva a forma de (leste, norte) para (x, −z) e a extrusão para +y, que é o referencial da cena. No loop, `aoMoverMarcos(ancoras.map(a => ({ id: a.id, tela: projetar(a.p) })))` só quando a chave serializada mudar (como a etiqueta). `enquadrarMarco(id)`: como `enquadrar`, com alvo em `(x, z, −y)` e distância 160.

- [ ] **Step 2: `Marcos.svelte`** — camada `pointer-events: none` sobre a cena (antes do chrome no DOM), com um botão por marco à vista: pílula de 44 px de altura, `Icone` (`camera` para clube e portaria, `mapa` para o estande) e o nome; `aria-label="{nome}: abrir galeria"`; `aoEscolher(id)`.

- [ ] **Step 3: `Galeria.svelte`** — conteúdo da Folha para `conteudo === 'marco'`:

```svelte
<script lang="ts">
  import type { Marco } from '../lib/dados';
  import { midia } from '../lib/midia';
  import Icone from './Icone.svelte';
  import PlantaAmpliada from './PlantaAmpliada.svelte';

  let { marco, aoFechar }: { marco: Marco; aoFechar: () => void } = $props();
  let ampliada = $state<{ src: string; alt: string } | null>(null);
  const maps = $derived(`https://www.google.com/maps/search/?api=1&query=${marco.lat},${marco.lon}`);
</script>

<div class="barra"><span></span><button class="fechar" aria-label="Fechar galeria" onclick={aoFechar}><Icone nome="fechar" tamanho={18} /></button></div>
<h2 class="titulo">{marco.nome}</h2>
{#if marco.id === 'estande'}
  <a class="btn" href={maps} target="_blank" rel="noopener noreferrer">Como chegar<Icone nome="externo" tamanho={18} /></a>
{/if}
<ul class="fotos">
  {#each marco.galeria as f, i (f.foto)}
    <li><button class="miniatura" aria-label="Ampliar foto {i + 1} de {marco.galeria.length}" onclick={() => (ampliada = { src: midia(f.foto, 'cheia'), alt: f.legenda || `${marco.nome}, foto ${i + 1}` })}>
      <img src={midia(f.foto, 'mini')} alt={f.legenda || `${marco.nome}, foto ${i + 1}`} loading="lazy" /></button></li>
  {/each}
</ul>
{#if marco.planta}
  <button class="miniatura planta" aria-label="Ampliar a planta humanizada" onclick={() => (ampliada = { src: midia(marco.planta!, 'cheia'), alt: `Planta humanizada do ${marco.nome.toLowerCase()}` })}>
    <img src={midia(marco.planta, 'mini')} alt="Planta humanizada do {marco.nome.toLowerCase()}" loading="lazy" /></button>
{/if}
{#if ampliada}<PlantaAmpliada src={ampliada.src} alt={ampliada.alt} aoFechar={() => (ampliada = null)} />{/if}
```

Grade `.fotos` com 2 colunas no celular e 3 a partir de 900 px; miniaturas em 4:3 com `object-fit: cover`. `PlantaAmpliada` é a ampliação em tela cheia.

- [ ] **Step 4: App** — `abrirMarco(id)`: `conteudo = 'marco'`, `batente = 'espiar'` (`'cheia'` a partir de 900 px), `cena.enquadrarMarco(id)`, sem tocar no `?lote=`. Rótulo da Folha: `Galeria: ${marco.nome}`.

- [ ] **Step 5: e2e**

```ts
test('8. o estande abre a galeria com a planta e o "Como chegar" na coordenada do KMZ', async ({ page }) => {
  const { marcos } = JSON.parse(readFileSync(new URL('../public/dados/marcos.json', import.meta.url), 'utf8'));
  const estande = marcos.find((m: { id: string }) => m.id === 'estande');
  await jaVisitou(page);
  await page.goto('./');
  await page.getByRole('button', { name: 'Estande de vendas: abrir galeria' }).click();
  const galeria = page.getByRole('region', { name: 'Galeria: Estande de vendas' });
  await expect(galeria.getByRole('link', { name: 'Como chegar' })).toHaveAttribute('href', new RegExp(`query=${estande.lat},${estande.lon}`));
  await galeria.getByRole('button', { name: 'Ampliar a planta humanizada' }).click();
  await expect(page.getByRole('dialog', { name: /Planta humanizada/ })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
});

test('9. o clube abre a galeria com todas as fotos do JSON', async ({ page }) => {
  const { marcos } = JSON.parse(readFileSync(new URL('../public/dados/marcos.json', import.meta.url), 'utf8'));
  const clube = marcos.find((m: { id: string }) => m.id === 'clube');
  await jaVisitou(page);
  await page.goto('./');
  await page.getByRole('button', { name: 'Clube: abrir galeria' }).click();
  await expect(page.getByRole('region', { name: 'Galeria: Clube' }).getByRole('button', { name: /Ampliar foto/ })).toHaveCount(clube.galeria.length);
});
```

Os botões dos marcos estão sempre na tela: um marco que sai do quadro fica preso à borda, a 12 px, como as pílulas distantes do entorno (`Marcos.svelte` recorta a posição projetada ao retângulo da tela). Assim o teste não depende da vista inicial.

Run: `cd frontend && npm test`
Expected: os testes 1 a 9 passam nos dois projetos.

- [ ] **Step 6: Commit**

```bash
git add frontend/src frontend/e2e
git commit -m "feat(front): marcos com ícone, volume do estande, galeria com ampliação e Como chegar"
```

---

### Task 7: Entorno, vegetação e pontos

**Files:**
- Create: `frontend/src/lib/cena/entorno.ts`, `frontend/src/lib/pontos.ts`, `frontend/src/lib/pontos.test.ts`, `frontend/src/componentes/{PontosEntorno,ListaEntorno,FichaPonto,IconePonto}.svelte`
- Modify: `frontend/src/lib/cena/cena.ts`, `frontend/src/App.svelte`, `frontend/e2e/jornadas.spec.ts`

**Interfaces:**
- Consumes: `public/modelos/{entorno.glb,vegetacao.glb,vegetacao.json}`, `PontoBruto` (Task 3).
- Produces: `Cena.entorno(ativo: boolean, pontos: Ponto[]): Promise<void>`; `Opcoes.aoMoverEntorno(q: QuadroEntorno | null)` (mesmo formato do espelho); `pontos.ts`:

```ts
export interface Ponto extends PontoBruto { id: number; distante: boolean; maps: string }
export function prepararPontos(p: PontoBruto[]): Ponto[]   // ordena por km, distante = faixa === 'distante'
export const ROTULO_CATEGORIA: Record<string, string>
export function rotuloKm(km: number): string             // "2,3 km"
```

Rulings:
1. **Distantes viram pílulas na borda da tela**, como o espelho faz hoje (#28), e o ponto é ancorado no lugar real quando cai dentro da tela. A spec diz "no vazio, a uma distância comprimida", mas "como no Manoa" hoje é este comportamento.
2. **A posição sai do `x, y` do `pontos.json`**, que já está no referencial local; o `prepararPontos` do espelho, que recalcula de lat/lon, não é usado.
3. **A cota de cada ponto vem de um raio vertical** lançado sobre o entorno, uma vez, ao carregar.

- [ ] **Step 1: Testes de `pontos.ts`**

```ts
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
  for (const c of ['compras', 'hotel', 'kitesurf', 'lagoa', 'lazer', 'natureza', 'orla', 'porto', 'praia', 'saude'])
    expect(ROTULO_CATEGORIA[c]).toBeTruthy();
});

test('km com vírgula', () => expect(rotuloKm(2.3)).toBe('2,3 km'));
```

Run: `npm run test:unidade` → FAIL (módulo ausente).

- [ ] **Step 2: `pontos.ts`**

```ts
import type { PontoBruto } from './dados';

export interface Ponto extends PontoBruto { id: number; distante: boolean; maps: string }

export const ROTULO_CATEGORIA: Record<string, string> = {
  compras: 'Compras', hotel: 'Hotel', kitesurf: 'Kitesurf', lagoa: 'Lagoa', lazer: 'Lazer',
  natureza: 'Natureza', orla: 'Orla', porto: 'Porto', praia: 'Praia', saude: 'Saúde',
};

export function prepararPontos(pontos: PontoBruto[]): Ponto[] {
  return [...pontos].sort((a, b) => a.km - b.km).map((p, id) => ({
    ...p, id, distante: p.faixa === 'distante', maps: `https://www.google.com/maps/search/?api=1&query=${p.lat},${p.lon}`,
  }));
}

const um = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 });
export const rotuloKm = (km: number) => `${um.format(km)} km`;
```

Run: `npm run test:unidade` → PASS.

- [ ] **Step 3: `cena/entorno.ts`** — o `Entorno` do espelho com quatro mudanças:
  - carrega `modelos/entorno.glb`, `modelos/vegetacao.glb` e `modelos/vegetacao.json` com o `loader(base)` da Task 4 (meshopt);
  - instâncias com cinco campos: `posicao.set(v[k] / 10, v[k + 2] / 100, -v[k + 1] / 10)`, escala `v[k + 3] / 100`, rotação `v[k + 4]`, com `const total = instancias.length / 5`;
  - sem véu e sem anéis próprios; os anéis de 1 e 3 km entram como no espelho (`raios = [1000, 3000]`, desenhados em `y = 0.5`);
  - `cotaEm(x: number, y: number): number` lança um raio de cima para baixo sobre `Entorno_*` e devolve a cota, ou 0 se não acertar.

A fração da vegetação segue a do aparelho, como no `dispositivo.ts` do espelho: 1 com mouse, 0,5 em tablet, 0,25 em celular, com a chave `maquete:vegetacao`.

- [ ] **Step 4: Cena** — `entorno(ativo, pontos)`: na primeira vez carrega o `Entorno` e calcula a cota de cada ponto com `cotaEm`. Ligado: mostra o grupo, `controles.maxDistance = 9000`, névoa na cor do solo do céu e câmera no alto, no rumo atual, com o anel de 3 km na largura da tela (a conta é a de `mostrarEntorno` do espelho, com 3000 no lugar de 1000). Desligado: esconde o grupo e volta à vista inicial. O loop chama `aoMoverEntorno(quadroEntorno())`, cuja função é a do espelho com `posicao = new THREE.Vector3(p.x, cota, -p.y)` e origem no centro dos lotes.

- [ ] **Step 5: Componentes** — `PontosEntorno.svelte` e `ListaEntorno.svelte` vêm do espelho, com estas mudanças:
  - `rotuloKm(ponto.km)` no lugar de `rotuloDistancia`, e `ROTULO_CATEGORIA`;
  - só os minutos de carro (o JSON não tem "a pé");
  - a atribuição usa o `fontesPontos` do JSON mais "Mapa: © OpenStreetMap contributors (ODbL), Overture Maps Foundation, Copernicus GLO-30";
  - o apoio diz "Distância em linha reta a partir do Residencial Cumbuco. Tempos de carro estimados pelo mapa viário."

`IconePonto.svelte` é o `IconeEntorno` do espelho com este mapa de categorias para os ícones Phosphor já presentes nele (o carro também vem dali):

```ts
const POR_CATEGORIA: Record<string, NomeIcone> = { compras: 'storefront', hotel: 'buildings', kitesurf: 'globe-hemisphere-west',
  lagoa: 'tree', lazer: 'tree', natureza: 'tree', orla: 'globe-hemisphere-west', porto: 'buildings', praia: 'globe-hemisphere-west', saude: 'first-aid' };
```

`FichaPonto.svelte` (Folha, `conteudo === 'ponto'`):
- nome, categoria, `rotuloKm` e os minutos de carro;
- a foto (`midia(foto, 'mini')`, que amplia com `PlantaAmpliada`), com "Foto: {credito} · {licenca}", e a licença em link para `licenca_url`, quando houver; sem foto, nenhum espaço reservado;
- o link "Abrir no Google Maps".

- [ ] **Step 6: App** — o botão de entorno do Controles (`aria-label="Entorno e pontos de referência"`, `aria-pressed`) alterna o modo. Ligado, a Folha mostra a `ListaEntorno` em `espiar`; o toque num ponto (camada ou lista) abre a `FichaPonto`, e fechar volta à lista. O estado de carregamento e de erro segue o do espelho ("Carregando o entorno…").

- [ ] **Step 7: e2e**

```ts
test('10. o entorno lista os pontos do JSON e abre a ficha do ponto', async ({ page }) => {
  const { pontos } = JSON.parse(readFileSync(new URL('../public/dados/pontos.json', import.meta.url), 'utf8'));
  const primeiro = [...pontos].sort((a: { km: number }, b: { km: number }) => a.km - b.km)[0];
  await jaVisitou(page);
  await page.goto('./');
  await page.getByRole('button', { name: 'Entorno e pontos de referência' }).click();
  const lista = page.getByRole('region', { name: 'Pontos de referência' });
  await expect(lista.getByRole('listitem')).toHaveCount(pontos.length);
  await lista.getByRole('button', { name: new RegExp(primeiro.nome) }).click();
  const ficha = page.getByRole('region', { name: `Ponto: ${primeiro.nome}` });
  await expect(ficha).toContainText(`${primeiro.minutos_carro} min`);
  await expect(ficha.getByRole('link', { name: 'Abrir no Google Maps' })).toHaveAttribute('href', /google\.com\/maps/);
});
```

Run: `cd frontend && npm test && npm run test:unidade`
Expected: os testes 1 a 10 passam nos dois projetos, e os de unidade também.

- [ ] **Step 8: Commit**

```bash
git add frontend/src frontend/e2e
git commit -m "feat(front): entorno com vegetação instanciada, pontos perto e distantes, lista e ficha do ponto"
```

---

### Task 8: Orçamento por arquivo e proteção do nome

**Files:**
- Create: `frontend/scripts/verificar-dist.mjs`, `frontend/scripts/verificar-dist.test.mjs`
- Modify: `docs/superpowers/specs/2026-10-14-maquete-cumbuco-design.md` (§7.4 e §9, a regra do orçamento)

**Interfaces:**
- Produces: `verificar(pasta): { erros: string[]; total: number; primeiro: number }`; `npm run verificar` sai com código 1 se houver erro.

- [ ] **Step 1: Teste**

```js
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
```

Run: `node --test scripts/verificar-dist.test.mjs` → FAIL (módulo ausente).

- [ ] **Step 2: Implementação**

```js
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
```

O `latin1` lê qualquer binário sem lançar erro, e um GLB com "alternativa" no nome de um nó ou material também é pego.

- [ ] **Step 3: Rodar contra o build real**

Run: `cd frontend && node --test scripts/verificar-dist.test.mjs && npm run build && npm run verificar`
Expected: `3 passed`; `dist: ~11 MB no total · primeiro carregamento (sem o entorno) ~7 MB`, sem `ERRO`. Se aparecer "nome guardado" num GLB (nome de material herdado do `.blend`, por exemplo), a correção vai no gerador Python e o GLB é regerado; não se edita o `dist/`.

- [ ] **Step 4: Spec** — na §7.4, troque a linha do orçamento por: "**Orçamento: 15 MB por arquivo publicado** (teto do Cloudflare; decisão de 16/10/2026). Arquivo maior é quebrado em partes. O total do primeiro carregamento é medido e reportado." Na §9, troque a linha do orçamento por: "um script mede o `dist/`, falha com arquivo acima de 15 MB ou com o nome guardado em qualquer caminho ou conteúdo, e reporta o primeiro carregamento."

- [ ] **Step 5: Commit**

```bash
git add frontend/scripts/verificar-dist.mjs frontend/scripts/verificar-dist.test.mjs docs/superpowers/specs/2026-10-14-maquete-cumbuco-design.md
git commit -m "feat(front): verificação do dist (15 MB por arquivo, sem o nome guardado); spec com a regra nova"
```

---

### Task 9: Worker de assets estáticos (sem publicar)

**Files:**
- Create: `frontend/wrangler.jsonc`

**Interfaces:**
- Produces: `npx wrangler deploy --dry-run` válido. O deploy de verdade é ⛔.

- [ ] **Step 1: `wrangler.jsonc`**

```jsonc
{
  "$schema": "node_modules/wrangler/config-schema.json",
  // Só assets: sem backend, sem CRM (spec §1). Nome neutro: nada publicado cita o nome guardado.
  "name": "cidade-americas-maquete",
  "compatibility_date": "2026-10-01",
  "workers_dev": false,
  "assets": { "directory": "./dist", "not_found_handling": "single-page-application" }
}
```

Sem `routes`: domínio e caminho são decisão do ⛔ (spec §10: `noindex` com caminho não óbvio ou Cloudflare Access).

- [ ] **Step 2: Conferir**

Run: `cd frontend && npm run build && npm run verificar && npx wrangler deploy --dry-run`
Expected: o dry-run lista os assets sem erro e não publica nada. O `_headers` está no `dist/`, com `X-Robots-Tag: noindex`.

- [ ] **Step 3: Commit**

```bash
git add frontend/wrangler.jsonc
git commit -m "feat(front): Worker só de assets, pronto para publicar depois do ok do nome"
```

**⛔ Antes de qualquer `wrangler deploy`:** o usuário decide a proteção (Cloudflare Access ou `noindex` com caminho não óbvio) e o domínio. O agente não publica.

---

### Task 10: Pacote offline com `iniciar.cmd`

**Files:**
- Create: `frontend/offline/servidor.ps1`, `frontend/offline/iniciar.cmd`, `frontend/scripts/pacote.mjs`, `frontend/e2e/offline.spec.ts`
- Modify: `frontend/playwright.config.ts` (projeto `offline`)

**Interfaces:**
- Produces: `npm run pacote` → `frontend/pacote/` com `index.html`, `assets/`, `dados/`, `modelos/`, `draco/`, `marca/`, `iniciar.cmd`, `servidor.ps1` e `LEIA-ME.txt`. O `iniciar.cmd` sobe `http://127.0.0.1:8137/` e abre o navegador.

Decisão: o servidor é PowerShell com `System.Net.HttpListener`, que existe em todo Windows; não pede Node, Python nem instalação. Escuta só em `127.0.0.1`, então não precisa de permissão de administrador nem de regra de firewall.

- [ ] **Step 1: `servidor.ps1`**

```powershell
# Servidor local da maquete: serve a pasta onde está, só em 127.0.0.1. Sem dependências.
param([int]$Porta = 8137, [switch]$SemNavegador)
$raiz = $PSScriptRoot
$tipos = @{ '.html'='text/html; charset=utf-8'; '.js'='text/javascript'; '.css'='text/css'; '.json'='application/json';
  '.glb'='model/gltf-binary'; '.wasm'='application/wasm'; '.webp'='image/webp'; '.jpg'='image/jpeg'; '.png'='image/png';
  '.svg'='image/svg+xml'; '.woff2'='font/woff2'; '.woff'='font/woff' }
$http = [System.Net.HttpListener]::new()
$http.Prefixes.Add("http://127.0.0.1:$Porta/")
$http.Start()
Write-Host "Maquete em http://127.0.0.1:$Porta/  (feche esta janela para parar)"
if (-not $SemNavegador) { Start-Process "http://127.0.0.1:$Porta/" }
try {
  while ($http.IsListening) {
    $ctx = $http.GetContext()
    $rel = [Uri]::UnescapeDataString($ctx.Request.Url.AbsolutePath.TrimStart('/'))
    if ($rel -eq '') { $rel = 'index.html' }
    $arquivo = [IO.Path]::GetFullPath((Join-Path $raiz $rel))
    $resp = $ctx.Response
    if (-not $arquivo.StartsWith($raiz) -or -not (Test-Path $arquivo -PathType Leaf)) {
      $resp.StatusCode = 404
    } else {
      $bytes = [IO.File]::ReadAllBytes($arquivo)
      $ext = [IO.Path]::GetExtension($arquivo).ToLower()
      $resp.ContentType = if ($tipos.ContainsKey($ext)) { $tipos[$ext] } else { 'application/octet-stream' }
      $resp.ContentLength64 = $bytes.Length
      $resp.OutputStream.Write($bytes, 0, $bytes.Length)
    }
    $resp.Close()
  }
} finally { $http.Stop() }
```

A query string (`?lote=`) não entra no caminho, porque `AbsolutePath` não a inclui. O `StartsWith($raiz)` impede `../`.

- [ ] **Step 2: `iniciar.cmd`**

```bat
@echo off
rem Abre a maquete sem internet: sobe o servidor local e o navegador. Feche a janela para parar.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0servidor.ps1" %*
```

- [ ] **Step 3: `pacote.mjs`** — apaga `pacote/`, copia `dist/` inteiro e `offline/iniciar.cmd` e `offline/servidor.ps1`, escreve um `LEIA-ME.txt` ("Dê dois cliques em iniciar.cmd. A maquete abre no navegador, sem internet. Para fechar, feche a janela preta.") e roda `verificar('pacote')` do `verificar-dist.mjs`, falhando se houver erro.

- [ ] **Step 4: Teste offline com a rede bloqueada**

`playwright.config.ts`: `webServer` vira lista; o segundo item é `{ command: 'npm run pacote && powershell -NoProfile -ExecutionPolicy Bypass -File pacote/servidor.ps1 -Porta 8138 -SemNavegador', url: 'http://127.0.0.1:8138/', reuseExistingServer: false, timeout: 240_000 }`. O projeto `offline` (`testMatch: /offline\.spec\.ts/`, `baseURL: 'http://127.0.0.1:8138'`, viewport do tablet) entra, e os outros dois ganham `testIgnore: /offline\.spec\.ts/`.

`e2e/offline.spec.ts`:

```ts
import { expect, test } from '@playwright/test';

test('o pacote abre sem internet: cena, ficha e galeria', async ({ page }) => {
  const fora: string[] = [];
  // Tudo que não é o servidor local é cortado: o teste prova que nada depende da rede.
  await page.route('**/*', r => {
    const u = new URL(r.request().url());
    if (u.hostname === '127.0.0.1') return r.continue();
    fora.push(u.href);
    return r.abort();
  });
  await page.addInitScript(() => localStorage.setItem('maquete:visitou', '1'));
  await page.goto('/?lote=Q07L04');
  await expect(page.getByRole('img', { name: /Maquete 3D/ })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Ficha do lote Q07 · L04' })).toBeVisible();
  await page.getByRole('region', { name: /Ficha do lote/ }).getByRole('button', { name: 'Fechar ficha' }).click();
  await page.getByRole('button', { name: 'Clube: abrir galeria' }).click();
  await expect(page.getByRole('region', { name: 'Galeria: Clube' }).getByRole('img').first()).toBeVisible();
  expect(fora).toEqual([]);
});
```

Run: `cd frontend && npm test`
Expected: as jornadas 1 a 10 passam nos dois projetos, o teste offline passa, e `fora` fica vazio.

- [ ] **Step 5: Commit**

```bash
git add frontend/offline frontend/scripts/pacote.mjs frontend/e2e/offline.spec.ts frontend/playwright.config.ts
git commit -m "feat(front): pacote offline com iniciar.cmd (servidor PowerShell local) e teste com a rede bloqueada"
```

---

### Task 11: Documentação e fechamento

**Files:**
- Create: `frontend/README.md`
- Modify: `docs/superpowers/plans/2026-10-14-00-plano-mestre.md`, `AGENTS.md`

- [ ] **Step 1: `frontend/README.md`**:
  - como rodar: `npm install`, `npm run dev`, `npm test`, `npm run test:unidade`;
  - de onde vem o `public/`: o `copiar-assets` lê as fontes de verdade; depois de regerar o pipeline Python, rode `npm run assets`;
  - `npm run verificar`: a regra de 15 MB por arquivo e a do nome guardado;
  - `npm run pacote`: o pacote offline;
  - publicação: ⛔ (decisão do usuário).

- [ ] **Step 2: Plano-mestre** — a linha do Plano 5 aponta para este arquivo (`2026-10-16-05-front-publicacao.md`), e a entrega passa a dizer "15 MB por arquivo". No contrato dos marcos, acrescente que o front registra o Draco (marcos) e o meshopt (os outros GLBs, comprimidos no `copiar-assets`).

- [ ] **Step 3: `AGENTS.md`** — na seção "Sources of truth", uma linha: "O `frontend/public/` é gerado por `npm run assets`; nunca editar à mão."

- [ ] **Step 4: Suítes completas**

Run: `uv run pytest -q` (raiz) e `cd frontend && npm run check && npm run test:unidade && npm test && npm run verificar`
Expected: tudo verde; o `verificar` sem `ERRO`.

- [ ] **Step 5: Commit**

```bash
git add frontend/README.md docs/superpowers/plans/2026-10-14-00-plano-mestre.md AGENTS.md
git commit -m "docs: front e publicação no plano-mestre e no AGENTS.md"
```

---

## Depois do plano

- **⛔ Publicação:** o usuário escolhe a proteção (Cloudflare Access ou `noindex` com caminho não óbvio) e o domínio; só então `npx wrangler deploy`.
- **Sessão de revisão visual (uma só, avisada antes):**
  - vista inicial (`config.vista`) e altura do estande;
  - escolha das fotos da galeria dos marcos e dos pontos (⛔ dos Planos 3b e 4);
  - conferir se algum render mostra logo ou nome;
  - gestos no celular e leitura dos pontos distantes.
- **Adiado (minor):** os 4 tiles do mapa (~2,2 MB) estão embutidos no `loteamento.glb` e no `entorno.glb`. A correção é no pipeline: um GLB sem as imagens, e o front reaproveita os materiais do outro. Não bloqueia: os arquivos ficam abaixo de 15 MB.
- **Fim da sessão:**
  - ponteiro no `_index.md` de Cumbuco;
  - entrada consolidada no `$VAULT_DIR\log.md`;
  - oferecer o sync do Drive.
