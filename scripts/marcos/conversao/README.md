# Conversão dos marcos (clube e portaria) para GLB — 15/10/2026

Registro da conversão feita por um agente, guardado como prova e para refazer. Scripts soltos, não um módulo do pipeline: o Plano 3b os transforma em pipeline se os marcos forem regenerados.

## Fontes e saídas

| fonte (`6-PROJETOS/…`) | saída em `10-MAQUETE INTERATIVA/` | MB | triângulos |
|---|---|---|---|
| `04-CLUBE/DWG Abner/clube 3d categorizado (do SKP).blend` | `clube - completo.glb` | 78,4 | 3.237.071 |
| idem, sem mobiliário | `clube - sem mobiliario.glb` | 4,5 | 234.961 |
| `05-PORTARIA/portaria e rotatoria 3d categorizado (do SKP).blend` | `portaria e rotatoria.glb` | 19,9 | 562.117 |

Aprovados pelo Abner em 15/10/2026 como estão (com os itens em dúvida mantidos).

## Referencial

Cena em metros, escala 1. Clube e portaria **não** estão no mesmo referencial (do `prep_np.py` que gerou os `.blend`):

- clube: translação por `ORIGIN` (515,2508; 979,5262) e rotação de +28° em torno de `PIVOT` (40,56; 45,98);
- portaria e rotatória: só a translação por `ORIGIN`.

Com `export_yup`, (x, y, z) do Blender vira (x, z, −y) no Three.js. A portaria tem um pedaço solto de 360 triângulos a ~250 m dela, que estica a caixa para 402 m.

## Ordem para refazer (`S` = pasta de trabalho)

1. `inventario.py` (dentro do Blender): coleções, triângulos, materiais → `inv_*.json`.
2. `probe_clube.py` (Blender): grava `eq_V.npy`/`eq_T.npy` do `CLUBE_EQUIPAMENTO`; `dump_cat.py` faz o mesmo para as outras categorias (`<CAT>_V/T.npy`).
3. `islands.py S` → ilhas conexas do equipamento (`eq_facelab.npy`); `clusters.py S` → ilhas agrupadas por caixa (`eq_clusters.json`).
4. `clusters2.py S <CAT>` → grupos das outras categorias (`<CAT>_clusters.json`).
5. `render_*.py` e `montage*.py`: prévias por grupo (`cl_montage*.png`) para classificar à vista.
6. `mask.py S` → máscaras de remoção. `KEEP` lista os grupos do equipamento mantidos, escolhidos olhando as montagens.
7. `export.py S sem|completo saida.glb` (Blender, com o `.blend` de origem aberto): tira `*_LINHAS`, copia a cor do viewport para o Principled (vidro alpha 0,35, água 0,8, `BLEND`), aplica as máscaras e exporta.
8. `verify.py` / `verify_port2.py`: reimporta o GLB num Blender limpo e confere.

`rm_report.json` tem os triângulos removidos por categoria e por grupo.
