# Marcos (clube, portaria, estande) — design

Data: 15/10/2026. Plano 3b. Spec-mãe: `2026-10-14-maquete-cumbuco-design.md` (§ Marcos, `marcos.json`).
Antecedentes: GLBs convertidos e aprovados (`scripts/marcos/conversao/README.md`); placa do loteamento (`2026-10-15-placa-loteamento-tiles-design.md`).

## O que entra

| Marco | Fonte | Na Cena |
|---|---|---|
| Clube | `10-MAQUETE INTERATIVA/clube - sem mobiliario.glb` | modelo na quadra central |
| Portaria | `10-MAQUETE INTERATIVA/portaria e rotatoria.glb`, coleção `PORTARIA` | modelo no acesso |
| Rotatória | o mesmo GLB, coleção `ROTATORIA` (a ilha com a fonte, ~35 m) | modelo na ilha da rotatória de acesso |
| Estande | DWG v10c em `08-ESTANDE/`, alinhado ao lote do KMZ | GLB detalhado em arquivo próprio; ver atualização de 17/10 abaixo |

## Decisões do usuário

- A implantação do SketchUp (clube, portaria e rotatória juntos) vale; o DXF exportado dela (650 MB) não é usado. A imagem `10-MAQUETE INTERATIVA/maqueteclubeplanta.jpg` (vista de cima da mesma maquete) serve só de conferência visual.
- Em 17/10/2026, o usuário pediu que o volume simples do estande fosse substituído por um modelo mais detalhado, baseado na planta e nas imagens de `08-ESTANDE/`.

## Encaixe

1. **Referencial comum.** Nos `.blend` de origem, portaria e rotatória têm só a translação `ORIGIN`; o clube tem a mesma translação e mais +28° em torno de `PIVOT` (40,56; 45,98). Desfazendo esses 28° (−28° em torno de `PIVOT`), os três ficam no referencial da portaria.
2. **Âncora.** Dois pares de pontos dão a transformação rígida (giro e translação, escala 1) do referencial da portaria para a planta de venda:
   - o centro da ilha da rotatória do GLB (caixa de `ROTATORIA_*` no plano) ↔ o centro do círculo da rotatória no DWG;
   - o centro do clube (caixa de `CLUBE_*`, já sem os 28°) ↔ o centroide da quadra central da placa (a maior peça `ChaoPlato` interior, 6.045 m²).

   O círculo é o `CIRCLE` das layers de via cujo raio difere do raio da ilha do GLB em até 3 m e cuja distância à quadra difere da distância ilha–clube do GLB em até 10 m; nenhum ou mais de um candidato falha. Nos dados atuais: círculo de r = 17,5 m em (176,2; 124,9), 364,2 m da quadra, contra 360,6 m e r ≈ 17,4 m no GLB.

   Refinamento: ICP rígido entre a borda do chão do GLB da portaria (faces voltadas para cima, perto de z = 0) e a borda das vias e calçadas do DWG, num raio de 150 m da rotatória, ignorando pares a mais de 5 m. O script imprime giro, translação e resíduo mediano, e falha acima de 1,5 m.
3. **Conferência.** Depois do refinamento, o centro do clube continua dentro da quadra central; senão o script falha. Prévia de cima da cena com os marcos, montada lado a lado com a imagem `maqueteclubeplanta.jpg`.
4. **Cotas.** O z = 0 dos modelos vai para a cota do platô; o do clube, para o topo da quadra (+0,25).

## Sem briga com a placa

O piso dos modelos não pode ficar coplanar com a placa, e a placa não pode ter buraco para o vazio. Cada marco tem uma **pegada**. Do modelo, ficam só as faces com os três vértices dentro da pegada (+1 cm). A placa perde o **furo**: a projeção das faces voltadas para cima do modelo recortado que estão até 0,6 m acima da base dele, piscina inclusive (as paredes da regra única aparecem na borda do furo). Onde o modelo não tem chão baixo (sob lajes, entre prédios), a placa fica. Laje e cobertura não furam a placa.

| Marco | Pegada |
|---|---|
| Clube | a quadra central inteira (a peça `ChaoPlato` interior que contém o clube). Conferência: a projeção das faces do modelo voltadas para cima, em qualquer altura, cobre ≥ 90% dela; senão, falha (só o chão perto de z = 0 dava 84%: prédios, piscina e decks ficam de fora). |
| Portaria | envoltória convexa das faces de topo dos objetos de edificação (laje, parede, pilar, viga, esquadria, vidro, equipamento) + 1 m; a caixa dos objetos não serve, porque paredes soltas sem topo a esticam por 370 m |
| Rotatória | o círculo da ilha no DWG |

Os pedaços de rua dos GLBs, inclusive o pedaço solto a 250 m da portaria, saem por essa regra.

## Arquivos

- `scripts/marcos/marcos.toml`: fontes, `ORIGIN`/`PIVOT`/28°, objetos de edificação, raio do ICP, limites.
- `scripts/marcos/encaixe.py` (Python puro): pegadas, âncora, ICP, conferências → `cache/cena/marcos.json` (transformações e pegadas no referencial local). A quadra central vem das peças da placa, que `cena.py` passa a expor sem montar malhas (`pecas_da_placa`).
- `scripts/blender/extrair_marcos.py` (Blender): contorno de piso e caixas dos GLBs fonte → `cache/cena/marcos-fonte.json`.
- `scripts/blender/gerar_marcos.py` (Blender): aplica as transformações, recorta pela pegada, exporta `10-MAQUETE INTERATIVA/marcos.glb` com os objetos `Clube`, `Portaria`, `Rotatoria` (materiais por categoria mantidos; vidro e água transparentes).
- `cena.py`: a placa perde as pegadas de `cache/cena/marcos.json` (se existir).
- `dados/marcos.json` (contrato com o front): `{"versao": 1, "marcos": [{id, nome, x, y, z, objeto, galeria: [{foto, legenda}], planta, lat, lon}]}`; `objeto` é o nome no `marcos.glb`, salvo `Estande`, carregado de `estande.glb`; sem modelo gerado, o estande mantém `objeto = null` e a extrusão da pegada. `planta` só no estande; `lat, lon` para "Como chegar".
- Galeria: `scripts/marcos/curadoria.json` (editada à mão) lista as imagens de cada marco; o script as reduz a 1600 px no lado maior (JPEG 82) em `dados/marcos/`. Primeira curadoria: seis renders de `04-CLUBE/Julho 25/Clube_Alta` (Alta 01 a 06), cinco de `05-PORTARIA/Artes Portaria` (portaria 01 a 05) e a planta humanizada do estande, ~3 MB no total; a escolha final fica para a sessão de revisão visual (⛔ Abner).
- Orçamento: `marcos.glb` ≤ 6 MB.

## Testes

- Desfazer o giro do clube: um ponto girado +28° em torno de `PIVOT` volta ao original.
- Âncora: com uma via sintética girada e deslocada, o ajuste devolve a transformação (≤ 0,1 m, ≤ 0,1°).
- Conferência do clube: centro fora da quadra → falha com mensagem.
- Pegadas: a placa sem a pegada não tem topo dentro dela; nenhuma face horizontal do marco a menos de 2 cm do topo da placa fora da pegada.
- `marcos.json`: os três marcos com objeto e o estande com `lat/lon` e `objeto = Estande` quando seu modelo foi gerado; fotos existentes.
- GLB: objetos `Clube`, `Portaria`, `Rotatoria`; ≤ 6 MB.

## Fora do escopo

Mobiliário detalhado dos outros marcos; ícones flutuantes e a Folha da galeria (Plano 5); escolha final das fotos (sessão de revisão).

## Atualização de 17/10/2026: estande pela planta v10c

O estande passa a usar a geometria do `2026-10-09 estande - estudo de partido Abner v10c.dwg`. O PDF da mesma revisão e a planta humanizada ajudam na conferência; os renders em `IMAGENS/` orientam os acabamentos. O desenho original fica intacto: a conversão DWG → DXF usa o `accoreconsole` e grava somente em `cache/estande/`.

O polígono da edificação contido no KMZ é de uma revisão anterior. A implantação usa os vértices correspondentes do lote `TER-LOTE` no DXF e do lote multifamiliar no KMZ. O encaixe é rígido, com escala 1; a frente pode divergir em até 15 cm, e qualquer vértice do lote, em até 20 cm. A pegada e o centro atuais vêm dos volumes `A-VOLUME` da v10c transformados para a cena. A base acompanha a cota do terreno no centro da edificação.

Entram paredes, divisórias, vidro, montantes, brises, painel de pedra, cobertura com beiral e forro, marquise de entrada, espelho d’água, rampa, estacionamento, deck em L, paisagismo e mobiliário simplificado. O mezanino e os degraus usam a planta; as alturas de fachada e cobertura e o comprimento suspenso dos brises são interpretações dos renders. Os níveis +0,45 e +3,20 são lidos dos textos do CAD. O deslocamento gráfico da planta do mezanino é lido de `build_v10.py`, sem executar esse arquivo. Textos e imagens das referências não são incorporados ao GLB.

Pipeline, a partir da raiz:

```bash
uv run python -m scripts.marcos.estande
uv run python -m scripts.marcos.dados
cd frontend
npm run build
```

- `scripts/marcos/estande.py`: lê o CAD, calcula a implantação e prepara as malhas, preservando os furos das hachuras.
- `scripts/blender/gerar_estande.py`: gera `estande.blend`, `estande.glb` implantado e `estande-local.glb` no referencial do CAD, na pasta `10-MAQUETE INTERATIVA`.
- `cache/estande/previa-estande.png` e `previa-estande-sem-cobertura.png`: vistas para conferir exterior e interior; o modelo exportado inclui a cobertura.
- `dados/estande.json`: fonte, hash do DWG, transformação, resíduo, pegada, centro e níveis; `scripts.marcos.dados` usa esses dados para gerar o marco `Estande`.
- `copiar-assets.mjs`: comprime o GLB com Meshopt e atualiza `public/` e `modelos-finais/`. O front carrega o estande junto dos demais modelos quando o marco declara `objeto = Estande`.

Orçamento bruto do GLB: 4 MB antes do Meshopt. Clube, portaria e rotatória continuam em `marcos.glb`.
