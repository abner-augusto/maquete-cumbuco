# Placa do loteamento em volume, chão em tiles e masterplan pintado — design

Data: 15/10/2026. Plano 3d, antes do 3b (marcos). Revê a cena do loteamento do Plano 3 e o mapa do chão do Plano 4.
Spec-mãe: `2026-10-14-maquete-cumbuco-design.md`. Relevo: `2026-10-14-relevo-plato-entorno-design.md`.

## Por quê

O loteamento briga consigo mesmo na vista (z-fighting), não recebe luz nem sombra, e o chão em volta está borrado. Medido em `cache/cena/loteamento.json`:

- Vias, calçadas, verdes e lotes são planos paralelos sobre o platô, de 21,02 a 21,25 m; via e calçada distam 4 cm. De longe, o buffer de profundidade do WebGL não separa as camadas.
- O desenho se sobrepõe: vias × calçadas 1.325 m², vias × verdes 1.882 m² (`Institucional` e `Fundo` têm a mesma área, ~15.507 m², mas são polígonos distintos e não se sobrepõem).
- No acesso norte o terreno atravessa a pista. A via já está no platô (todos os vértices de `Vias` a 21,12 m; `aneis_do_plato` inclui as camadas de via e a folga de 10 m faz o ombro), mas a grade de 10 m do terreno, que continua debaixo da placa, interpola nós altos do talude por cima da via estreita.
- O mapa do chão é um JPEG de 4096 px para 8 km (≈2 m/px), e o masterplan das outras fases não aparece.

## Decisões do usuário

- **Placa em volume** (não drapeado corrigido, não platô texturizado).
- **Exagero moderado** das alturas: legível de longe, crível no zoom do lote.
- **Chão em 4 tiles de 4096 px** (≈1 m/px no total).
- **Masterplan das fases 2–10 pintado no chão, em segundo plano**, rasterizado do `MASTER URBANO.pdf` em alta. O foco é a Fase 1, já aprovada.
- Clube, portaria e rotatória: GLBs aprovados como estão (`scripts/marcos/conversao/README.md`); o posicionamento é do Plano 3b.

## 1. Placa do loteamento

### Partição

Dentro do platô, cada metro quadrado pertence a uma peça só. As peças saem em shapely, na ordem de prioridade, e cada uma perde o que as anteriores ocuparam:

1. `Lagoa` (anel da lagoa, como hoje)
2. lotes (`Q07L04`…, de `lotes.json`)
3. `Calcadas`
4. `Verdes`, `Institucional`, `Fundo`, `APP`
5. `Pista`: a layer de vias menos o que já foi ocupado, mais as frestas entre peças com menos de `fresta_max` m² (padrão 2 m²) que encostam na via
6. `ChaoPlato`: o resto do platô (a folga além do desenho), no material do terreno

A prioridade resolve toda sobreposição; a partição é arredondada a 1 mm (`shapely.set_precision`) para não deixar lascas numéricas.

### Volume

Cotas a partir da cota do platô (`cena.toml`, nova seção `[placa]`):

| peça | topo | faces verticais |
|---|---|---|
| `Pista` | 0,00 | — |
| `Calcadas`, `Verdes`, `Institucional`, `Fundo`, `APP` | +0,25 | meio-fio até a pista |
| lote | +0,40 | recuo de 0,15 m por lado; a faixa recuada é a peça `Juntas` |
| `Juntas` | +0,25 | — |
| `Lagoa` | lâmina −0,30 | margem vertical até a peça vizinha |
| `ChaoPlato` | 0,00 | — |

- Topo de cada peça: triangulação com furos (`triangular`), plana; sem refino (a placa é plana).
- **Faces verticais, regra única:** cada peça ganha parede, do seu topo até −1,0 m, no trecho do contorno que não encosta em peça de topo igual ou mais alto. Isso dá o meio-fio (calçada contra pista), a margem da lagoa (pista ou verde contra a água) e a **saia** no contorno externo da placa (sem vizinho), que esconde qualquer fresta com o terreno.
- Lotes continuam um objeto cada, com o mesmo nome. **Pivô novo:** a origem do objeto fica no centro da caixa do topo (o front enquadra o lote no clique pela origem).
- O contrato de `lotes.json` não muda.

### Terreno com furo

O terreno perto continua sendo a grade de 10 m, com os mesmos dois triângulos por célula, para a vegetação e os prédios seguirem assentados na superfície desenhada (`cota_malha`). Muda só isto: a célula toda dentro da placa sai; a célula que cruza o contorno vira o polígono "célula menos placa", triangulado, com as cotas de `cota_malha`. A borda do furo coincide com o contorno da placa por construção. Ali o relevo está no platô ou no começo do talude, abaixo do topo da placa até 1 m, e a saia cobre a diferença. A lagoa deixa de escavar o terreno: ela é peça da placa.

O perfil escavado do acesso, considerado no brainstorming, sai do escopo: o furo resolve o morro na pista.

## 2. Chão em tiles

- O recorte de 8 km (`mapa.json`, ext −4050…3990 × −3960…4050) é cortado em 2×2 por uma linha vertical e uma horizontal que caem em nós comuns às grades de 30 m (Copernicus) e de 10 m (perto), as mais próximas do centro: x = −30 e y = 60 nos dados atuais (o script calcula). Os tiles têm larguras levemente diferentes.
- Um JPEG de 4096 px no lado maior por tile (`mapa_<ij>.jpg`, qualidade 85), rasterizado com 2 px a mais de borda; o UV mapeia só o miolo, então o filtro da GPU não abre costura.
- Malhas: `Entorno_00…11` (grade de 30 m cortada nas linhas, sem partir triângulo) e `Terreno_00…11` (seção 1). Cada pedaço usa o material do seu tile.
- Memória: 4 × 4096² ocupa o mesmo que uma de 8192² (~190 MB RGB sem mipmap). O ganho é que nenhuma textura passa do limite de 4096 de celular. Compressão (KTX2) ou tiles de 2048 no celular ficam para o Plano 5.

## 3. Masterplan pintado

- **Fonte:** `2-LEVANTAMENTOS/PLANTAS_BASE/MASTER URBANO.pdf`, página 5 ("MASTERPLAN", vetor, plano b). O DWG R05 não serve: as layers `AR-*` só têm a Fase 1, a poligonal, APP e duas vias. O PNG do `MASTER.kmz` está a ~1,7 m/px.
- **Rasterização:** PyMuPDF, recorte na caixa da poligonal, resolução de ≥ 1 px por 0,5 m.
- **Registro:** semelhança (escala, rotação, translação) entre a poligonal desenhada no PDF (o caminho fechado de maior área com o contorno da gleba em `page.get_drawings()`) e a poligonal do DWG R05 no referencial da topografia (674 vértices, 3.493.048 m²). Chute inicial por centroide, escala pela raiz da razão de áreas e varredura de rotação de 1 em 1°; depois ICP de semelhança (Umeyama) sobre pontos amostrados nos dois contornos a cada 2 m. O script imprime escala, rotação e resíduo, e falha se o resíduo mediano passar de 2 m. A poligonal do DWG é a cópia de 674 vértices do R05 cuja caixa contém a `AR-CNT-POL` da planta de venda (o R05 tem cópias da poligonal em vários deslocamentos).
- **Máscara:** só dentro da poligonal da gleba, fora do platô com folga + talude (o traçado antigo da Fase 1 no PDF não aparece encostado no real).
- **Camada de segundo plano** (decisão do usuário: o foco é a Fase 1, já aprovada). A imagem registrada entra nos tiles por cima do OSM, mas apagada: dessaturada (`masterplan_saturacao`, padrão 0,35) e misturada ao chão (`masterplan_opacidade`, padrão 0,55), com as curvas de nível do PDF suavizadas. Lê-se como "o que vem depois", nunca compete com a placa da Fase 1. Os dois valores ficam no `entorno.toml`, e o masterplan inteiro desliga com `masterplan = false`.
- **Ordem:** é a última tarefa do plano; se o registro não fechar, os tiles saem sem ele e nada mais depende disso.
- Arquivo da Fase 1: o R05 continua sendo usado só pela topografia (Plano 3).

## Arquivos

- Novos: `scripts/loteamento/placa.py` (partição e volume), `scripts/entorno/tiles.py` (corte e rasterização), `scripts/entorno/masterplan.py` (rasterização, registro, máscara).
- Novo também: `scripts/loteamento/chao.py` (terreno perto com furo, por tile).
- Alterados: `cena.py` (usa a placa e o chão), `cena.toml` (`[placa]`), `preparar.py` (tiles), `entorno.toml` (`tile_px = 4096`, no lugar de `mapa_px`), `blender.py` e `gerar_loteamento.py` (um material por tile, pivô dos lotes, `OBJETOS_ENTORNO`).
- GLBs em `6-PROJETOS/10-MAQUETE INTERATIVA/`: `loteamento.glb` (lotes, peças da placa, `Juntas`, `Terreno_*`) e `entorno.glb` (`Entorno_*`, `Mar`, `ViasPrincipais`, `Predios`), cada um ≤ 8 MB.
- Plano-mestre: linha do 3d e contratos novos (nomes `Entorno_*`/`Terreno_*`, pivô dos lotes, referencial dos marcos).

## Testes

- Partição: interseção entre quaisquer duas peças < 0,01 m²; soma das áreas = área do platô (± 0,1%).
- Volume: topo do lote a +0,40, pivô no centro da caixa do topo; parede só onde o vizinho é mais baixo ou não existe.
- Terreno: nenhum triângulo do terreno dentro da placa; área do terreno = área da janela − área da placa nela (± 0,1%); fora das células cortadas, os triângulos são os da grade.
- Tiles: linhas de corte em nós das duas grades; tiles cobrem o recorte sem fresta; nenhum triângulo partido; pixels da borda iguais entre vizinhos (com a margem de 2 px).
- Masterplan: com um contorno sintético girado 5°, escalado 1,02 e deslocado (100, −50), o registro devolve a transformação; máscara vazia dentro do platô.
- GLB: 347 lotes nomeados, objetos esperados nos dois GLBs, ≤ 8 MB cada.
- Prévias (geral, perto, lagoa, entorno): sem z-fighting na via de acesso; meio-fio e juntas com sombra; degrau da borda da placa legível como bandeja sobre o talude.

## Fora do escopo

Marcos (Plano 3b), front, shader do mar, meshopt e KTX2 (Plano 5); volumes das fases 2–10 (só pintadas); perfil próprio do acesso norte.
