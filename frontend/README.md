# Front da maquete

Site em Svelte 5 + Three.js que mostra a Fase 1: lotes clicáveis com a ficha, marcos com galeria e o
entorno com os pontos de referência. Roda online como Worker só de assets e offline pelo `iniciar.cmd`.

## Rodar

Tudo de dentro de `frontend/`:

```bash
npm install
npm run dev            # monta o public/ e abre o Vite em http://127.0.0.1:5173
npm run test:unidade   # Vitest: busca, preços, mídia, pontos
npm run test:leve      # Playwright com prioridade baixa e um navegador por vez (Windows)
npm test               # Playwright direto; E2E_WORKERS=2 sobe o paralelismo
npm run check          # svelte-check
```

O e2e desenha o WebGL na placa de vídeo (ANGLE/D3D11, ~1 min a suíte). Numa máquina sem GPU, `E2E_GPU=0` usa o
SwiftShader, por software: ocupa a CPU e leva uns 4 min; prefira o `test:leve` com a máquina em uso.

## De onde vem o `public/`

O `scripts/copiar-assets.mjs` monta o `public/` a partir das fontes de verdade: `dados/*.json` e as
fotos citadas neles (convertidas para WebP em 480 e 1920 px), a família ativa da `marca/`, os GLBs da
pasta do terreno (`TERRENO_DIR` no `.env` da raiz; meshopt nos GLBs, Draco mantido nos marcos) e o
decoder do Draco. Nada do `public/` é editado à mão, salvo o `_headers`. Depois de regerar o pipeline
Python, rode `npm run assets` (o `dev` e o `build` já rodam).

Os modelos finais (GLBs já comprimidos, `vegetacao.json` e os `mapa-osm_XX.jpg`, 15 MB) ficam versionados
em `modelos-finais/`: o `npm run assets` os regrava a cada vez que roda com `TERRENO_DIR`, e sem ele
(quem só clonou o repositório) copia dali. Assim `npm ci && npm run build` funciona sem o Blender. Depois
de regerar o pipeline, commite o `modelos-finais/` junto.

Ajustes de apresentação (vista inicial, altura do volume do estande) ficam em `../dados/config.json`.

## Verificar o `dist/`

`npm run verificar` falha se algum arquivo do `dist/` passar de 15 MB (o teto por arquivo do
Cloudflare; arquivo maior é quebrado em partes) ou se o nome guardado aparecer em qualquer caminho ou
conteúdo. Também reporta o total e o primeiro carregamento, sem o entorno.

## Pacote offline

`npm run build && npm run pacote` gera `pacote/`: o `dist/`, o `servidor.ps1` (PowerShell, só em
`127.0.0.1:8137`, sem instalar nada) e o `iniciar.cmd`. Dois cliques no `iniciar.cmd` abrem a maquete
no navegador, sem internet.

## Publicação

⛔ Decisão do usuário: a proteção (Cloudflare Access ou `noindex` com caminho não óbvio) e o domínio.
O `wrangler.jsonc` está pronto e `npx wrangler deploy --dry-run` passa; o deploy de verdade não é feito
por agente. Rode o Wrangler com `WRANGLER_SEND_METRICS=false`.

## Publicar no Cloudflare

`npm run publicar` faz o build e sobe o `dist/` como Worker de assets (`wrangler login` antes). O domínio
vem de `DOMINIO` no `.env` da raiz (ou do ambiente); vazio, publica no `workers.dev`. O `wrangler.jsonc`
não guarda domínio. Todos os caminhos e nomes da máquina ficam no `.env` (modelo em `.env.example`), e o
`tests/test_anonimo.py` falha se algum aparecer num arquivo versionado.
