# Plano-mestre — Maquete interativa Alternativa Residencial Cumbuco

**Spec:** `docs/superpowers/specs/2026-10-14-maquete-cumbuco-design.md`

A spec cobre cinco subsistemas independentes. Cada um tem seu plano, que produz software testável sozinho. Os planos 2 a 5 são escritos **quando o anterior destrava**, porque dependem do que os gates revelarem (layers do DWG, logo escolhido, lista de POIs). Escrever o código deles agora seria adivinhar.

| # | Plano | Entrega | Depende de | Gates (⛔ = Abner) |
|---|---|---|---|---|
| 1 | Fundação e dados do loteamento | Projeto Python, DWG → DXF, inventário de layers, `lotes.json`, `georref.json`, `relatorio-conferencia.md` | — | ⛔ inventário de layers (Task 4) |
| 2a | Marca: paleta, tokens e prancha (`2026-10-14-02-marca.md`) | `paleta.json`, `tokens.css` no formato de tema do espelho, prancha comparativa | — | ⛔ escolha do logo e das fontes |
| 2b | Marca: vetorização e brandbook (`2026-10-14-02b-marca-vetores.md`) | SVGs gerados por script, brandbook HTML+PDF | 2a | — |
| 3 | Modelagem do loteamento | Script bpy: relevo, lotes `Q07L04`, vias, lagoa, volumes de estande/portaria/clube → `loteamento.glb` e `.blend` em `6-PROJETOS/10-MAQUETE INTERATIVA/` | 1 | — |
| 4 | Entorno, vegetação e pontos | `scripts/entorno` derivado do Manoa (raio de 2,5 km), vegetação instanciada, `pontos.json` com fotos e créditos, `marcos.json` → `entorno.glb` | 1 (origem local) | ⛔ lista de POIs e fotos |
| 5 | Front e publicação | `frontend/` derivado do espelho: Cena, Folha, Ficha, marcos, pontos, marca; Playwright; orçamento de 15 MB; Worker estático e `iniciar.cmd` | 2 (tokens), 3, 4 | ⛔ proteção do nome antes de publicar |

Ao fim do Plano 5: uma única sessão de revisão visual, e depois o ponteiro no `_index.md` de Cumbuco e a entrada no `log.md` do vault.

## Contratos entre planos

São fixados no Plano 1 e consumidos pelos demais:

- **Id de lote:** `Q<quadra>L<lote>`, com quadra numérica de 2 dígitos (`Q07L04`) ou alfabética (`QHL01`, `QML03`) e lote de 2 dígitos. É o nome do objeto no Blender, a chave do `lotes.json` e o valor de `?lote=`.
- **Origem local:** `dados/georref.json` → `{"crs": "EPSG:31984", "origem": {"E": <float>, "N": <float>}}`. Coordenada local = (E − E0, N − N0) em metros; no Three.js, x = leste, z = −norte, y = cota.
- **`dados/lotes.json`:** schema na Task 7 do Plano 1.
