# Marcos (clube, portaria, estande) — design

Data: 15/10/2026. Plano 3b. Spec-mãe: `2026-10-14-maquete-cumbuco-design.md` (§ Marcos, `marcos.json`).
Antecedentes: GLBs convertidos e aprovados (`scripts/marcos/conversao/README.md`); placa do loteamento (`2026-10-15-placa-loteamento-tiles-design.md`).

## O que entra

| Marco | Fonte | Na Cena |
|---|---|---|
| Clube | `10-MAQUETE INTERATIVA/clube - sem mobiliario.glb` | modelo na quadra central |
| Portaria | `10-MAQUETE INTERATIVA/portaria e rotatoria.glb`, coleção `PORTARIA` | modelo no acesso |
| Rotatória | o mesmo GLB, coleção `ROTATORIA` (a ilha com a fonte, ~35 m) | modelo na ilha da rotatória de acesso |
| Estande | `08-ESTANDE/2026-10-07 estande - implantacao georreferenciada.kmz`, polígono "Estande (edificacao)" | só um ponto (centroide da pegada); pegada guardada no JSON |

## Decisões do usuário

- A implantação do SketchUp (clube, portaria e rotatória juntos) vale; o DXF exportado dela (650 MB) não é usado. A imagem `10-MAQUETE INTERATIVA/maqueteclubeplanta.jpg` (vista de cima da mesma maquete) serve só de conferência visual.
- O estande entra como ponto de referência, sem volume.

## Encaixe

1. **Referencial comum.** Nos `.blend` de origem, portaria e rotatória têm só a translação `ORIGIN`; o clube tem a mesma translação e mais +28° em torno de `PIVOT` (40,56; 45,98). Desfazendo esses 28° (−28° em torno de `PIVOT`), os três ficam no referencial da portaria.
2. **Âncora.** A transformação rígida (giro e translação, escala 1) do referencial da portaria para a planta de venda sai de dois pares:
   - o centro da ilha da rotatória do GLB (caixa de `ROTATORIA_*` no plano) com o centro do círculo da rotatória de acesso na planta de venda (o `CIRCLE` das layers de via com o raio mais próximo do raio da ilha do GLB; empate ou diferença > 3 m falha);
   - a direção ilha → portaria (centro da caixa dos objetos de edificação de `PORTARIA`) com a direção do eixo da via de acesso no DWG, do centro da rotatória para o platô.

   Refinamento: ICP rígido entre o contorno do piso do GLB (`PORTARIA_PISO`, faces voltadas para cima e perto de z = 0) e o contorno das vias e calçadas do DWG, só num raio de 150 m da rotatória. O script imprime giro, translação e resíduo mediano, e falha acima de 1,5 m.
3. **Conferência.** Com a mesma transformação, o centro do clube tem de cair dentro da quadra central da placa (peça `ChaoPlato` interior, 6.045 m²); senão o script falha. Prévia de cima com a imagem `maqueteclubeplanta.jpg` sobreposta.
4. **Cotas.** O z = 0 dos modelos vai para a cota do platô; o do clube, para o topo da quadra (+0,25).

## Sem briga com a placa

O piso dos modelos não pode ficar coplanar com a placa. Cada marco tem uma **pegada**, e a placa perde a pegada (as paredes da regra única aparecem na borda do furo). Do modelo, ficam só as faces cujo centro está dentro da pegada mais 1 m.

| Marco | Pegada |
|---|---|
| Clube | a quadra central inteira (a peça `ChaoPlato` interior que contém o clube). Conferência: o piso do modelo cobre ≥ 90% dela; senão, falha. |
| Portaria | envoltória convexa dos objetos de edificação (laje, parede, pilar, viga, esquadria, vidro, equipamento) + 1 m |
| Rotatória | o círculo da ilha no DWG |

Os pedaços de rua dos GLBs, inclusive o pedaço solto a 250 m da portaria, saem por essa regra.

## Arquivos

- `scripts/marcos/marcos.toml`: fontes, `ORIGIN`/`PIVOT`/28°, objetos de edificação, raio do ICP, limites.
- `scripts/marcos/encaixe.py` (Python puro): pegadas, âncora, ICP, conferências → `cache/cena/marcos.json` (transformações e pegadas no referencial local).
- `scripts/blender/extrair_marcos.py` (Blender): contorno de piso e caixas dos GLBs fonte → `cache/cena/marcos-fonte.json`.
- `scripts/blender/gerar_marcos.py` (Blender): aplica as transformações, recorta pela pegada, exporta `10-MAQUETE INTERATIVA/marcos.glb` com os objetos `Clube`, `Portaria`, `Rotatoria` (materiais por categoria mantidos; vidro e água transparentes).
- `cena.py`: a placa perde as pegadas de `cache/cena/marcos.json` (se existir).
- `dados/marcos.json` (contrato com o front): `{"versao": 1, "marcos": [{id, nome, x, y, z, objeto, galeria: [{foto, legenda}], planta, lat, lon}]}`; `objeto` é o nome no `marcos.glb` (`null` no estande); `planta` só no estande (a planta humanizada do KMZ); `lat, lon` para "Como chegar".
- Galeria: `scripts/marcos/curadoria.json` (editada à mão) lista as imagens de cada marco; o script as reduz a 1600 px no lado maior (JPEG 82) em `dados/marcos/`. Primeira curadoria: todas as candidatas de `04-CLUBE/Julho 25/Clube_Alta`, `05-PORTARIA/Artes Portaria` e a planta humanizada do estande; a escolha final fica para a sessão de revisão visual (⛔ Abner).
- Orçamento: `marcos.glb` ≤ 6 MB.

## Testes

- Desfazer o giro do clube: um ponto girado +28° em torno de `PIVOT` volta ao original.
- Âncora: com uma via sintética girada e deslocada, o ajuste devolve a transformação (≤ 0,1 m, ≤ 0,1°).
- Conferência do clube: centro fora da quadra → falha com mensagem.
- Pegadas: a placa sem a pegada não tem topo dentro dela; nenhuma face horizontal do marco a menos de 2 cm do topo da placa fora da pegada.
- `marcos.json`: os três marcos com objeto e o estande com `lat/lon` e `objeto = null`; fotos existentes.
- GLB: objetos `Clube`, `Portaria`, `Rotatoria`; ≤ 6 MB.

## Fora do escopo

Volume do estande; mobiliário; ícones flutuantes e a Folha da galeria (Plano 5); escolha final das fotos (sessão de revisão).
