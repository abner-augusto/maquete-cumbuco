# Plano-mestre — Maquete interativa Alternativa Residencial Cumbuco

**Spec:** `docs/superpowers/specs/2026-10-14-maquete-cumbuco-design.md`

A spec cobre cinco subsistemas independentes. Cada um tem seu plano, que produz software testável sozinho. Os planos 2 a 5 são escritos **quando o anterior destrava**, porque dependem do que os gates revelarem (layers do DWG, logo escolhido, lista de POIs). Escrever o código deles agora seria adivinhar.

| # | Plano | Entrega | Depende de | Gates (⛔ = Abner) |
|---|---|---|---|---|
| 1 | Fundação e dados do loteamento | Projeto Python, DWG → DXF, inventário de layers, `lotes.json`, `georref.json`, `relatorio-conferencia.md` | — | ⛔ inventário de layers (Task 4) |
| 2a | Marca: paleta, tokens e prancha (`2026-10-14-02-marca.md`) | `paleta.json`, `tokens.css` no formato de tema do espelho, prancha comparativa | — | ⛔ escolha do logo e das fontes |
| 2b | Marca: vetorização e brandbook (`2026-10-14-02b-marca-vetores.md`) | SVGs gerados por script, brandbook HTML+PDF | 2a | — |
| 3 | Loteamento no Blender (`2026-10-14-03-loteamento-blender.md`) | Relevo pelas curvas cotadas, cena em JSON, `loteamento.glb` e `.blend` em `6-PROJETOS/10-MAQUETE INTERATIVA/` com 347 lotes nomeados | 1 | — |
| 3c | Relevo simplificado (`2026-10-14-03c-relevo-plato-entorno.md`) | Platô plano, morro pelo levantamento suavizado, Copernicus até 4 km; `entorno.glb` (`Entorno`, `Mar`) costurado ao terreno perto | 3 | — |
| 3d | Placa em volume e chão em tiles (`2026-10-15-03d-placa-loteamento-tiles.md`) | Loteamento como placa sem sobreposição (pista, meio-fio, juntas, lagoa, saia), terreno com furo, chão em 4 tiles de 4096 px, masterplan das fases 2–10 em segundo plano; GLBs dos marcos convertidos (`scripts/marcos/conversao/`) | 3c, 4 | — |
| 3b | Marcos (`2026-10-15-03b-marcos.md`) | `marcos.glb` (clube, portaria e rotatória encaixados por âncora + ICP, recortados pela pegada; Draco), placa com os furos das pegadas, `dados/marcos.json` com galeria e o estande como ponto do KMZ | 3, 3d | ⛔ fotos da galeria |
| 4 | Entorno, vegetação e pontos (`2026-10-14-04-entorno-vegetacao-pontos.md`) | `entorno.glb` com mapa do OSM pintado no relevo, vias principais em faixa 3D e prédios do Overture (até 1,5 km); `vegetacao.glb/.json` (coqueiro, cajueiro, arbusto); `dados/pontos.json` (coordenada do OSM, minutos de carro, fotos livres do Commons) | 1 (origem local), 3c | ⛔ fotos dos pontos |
| 5 | Front e publicação | `frontend/` derivado do espelho: Cena, Folha, Ficha, marcos, pontos, marca; Playwright; orçamento de 15 MB; Worker estático e `iniciar.cmd` | 2 (tokens), 3, 4 | ⛔ proteção do nome antes de publicar |

Ao fim do Plano 5: uma única sessão de revisão visual, e depois o ponteiro no `_index.md` de Cumbuco e a entrada no `log.md` do vault.

## Contratos entre planos

São fixados no Plano 1 e consumidos pelos demais:

- **Id de lote:** `Q<quadra>L<lote>`, com quadra numérica de 2 dígitos (`Q07L04`) ou alfabética (`QHL01`, `QML03`) e lote de 2 dígitos. É o nome do objeto no Blender, a chave do `lotes.json` e o valor de `?lote=`.
- **Origem local:** `dados/georref.json` → `{"crs": "EPSG:31984", "origem": {"E": <float>, "N": <float>}}`. Coordenada local = (E − E0, N − N0) em metros; no Three.js, x = leste, z = −norte, y = cota.
- **`dados/lotes.json`:** schema na Task 7 do Plano 1.
- **`dados/pontos.json`:** `{"versao": 1, "pontos": [{nome, categoria, lat, lon, x, y, km, minutos_carro, faixa ("proximo" até 3 km, "distante"), osm, foto, credito, licenca, licenca_url, fonte_foto}]}`; `foto` relativo a `dados/` ou `null` até a aprovação. Curadoria (fonte editada à mão) em `scripts/pontos/curadoria.json`.
- **`vegetacao.json`:** campos `x_dm, y_dm, z_cm, escala_pct, rotacao_graus` por espécie (`coqueiro`, `cajueiro`, `arbusto`), embaralhados; malhas `VEG_<especie>` no `vegetacao.glb`, base em z = 0.
- **Objetos do chão:** `Entorno_<ij>` (`entorno.glb`) e `Terreno_<ij>` (`loteamento.glb`), `i` 0/1 = oeste/leste, `j` 0/1 = sul/norte; cada um com o material `chao_mapa_<ij>` do seu tile. `cache/entorno/mapa.json` = `{"tiles": {ij: {arquivo, ext, janela, px}}}`.
- **Pivô dos lotes:** a origem de cada objeto `Q…` é o centro da caixa do topo do lote (topo a +0,40 m do platô); no glTF, `translation` = (x, z, −y).
- **Marcos:** `clube - sem mobiliario.glb` e `portaria e rotatoria.glb` em `10-MAQUETE INTERATIVA/`; o clube está girado +28° em torno de `PIVOT` (40,56; 45,98) em relação à portaria (detalhes em `scripts/marcos/conversao/README.md`).
- **Acesso:** a faixa do DWG entre a rotatória e a CE vira avenida em rampa (`scripts/loteamento/acesso.py`, `[acesso]` do `cena.toml`): seção da avenida, perfil plano → rampa → patamar, boca em curva e ilha triangular; objetos `AcessoPista`, `AcessoCalcadas`, `AcessoCanteiro` no `loteamento.glb`. A faixa da CE fica no chão natural.
- **`marcos.glb`:** objetos `Clube`, `Portaria`, `Rotatoria` já no referencial local, com compressão Draco (o front carrega com o `DRACOLoader`).
- **`dados/marcos.json`:** `{"versao": 1, "marcos": [{id, nome, x, y, z, objeto, galeria: [{foto, legenda}], planta, lat, lon}]}`; `objeto` é o nome no `marcos.glb` (`Clube`, `Portaria`, `Rotatoria`) ou `null` (estande, que leva também `pegada`); fotos relativas a `dados/`.
- **Ordem de geração:** `entorno.extrair` (as vias do OSM: o terreno acha a CE nelas) → `loteamento.terreno` (grava `cache/cena/acesso.json`) → `marcos.blender --extrair` → `marcos.encaixe` → `loteamento.cena` → `entorno.preparar` → `entorno.vegetacao` → `loteamento.blender` → `marcos.blender` → `marcos.dados`.
