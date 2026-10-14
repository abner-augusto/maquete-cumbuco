# Relevo simplificado: platô, morro e entorno de 4 km — design

Data: 14/10/2026. Plano 3c, antes do 3b (marcos). Revê o relevo do Plano 3 e antecipa o relevo do Plano 4.
Spec-mãe: `2026-10-14-maquete-cumbuco-design.md` (§7.1.3 relevo, §7.2 entorno).

## Por quê

O relevo detalhado das curvas dentro do loteamento não ajuda a vender: a Fase 1 vai ser
planificada para abrir as ruas. O que importa é a leitura do conjunto: o **platô** do
loteamento, o **morro** em volta (mais alto na área do estande e do multifamiliar) e o
**relevo macro** do entorno, até 4 km (o usuário fixou 4 km; a spec-mãe dizia ~2,5 km).

## Decisões do usuário

- Platô plano único para toda a Fase 1, com talude curto até o terreno em volta.
- Fora do platô: levantamento suavizado perto, Copernicus GLO-30 até 4 km, costurados.
- O mar será um shader no Three.js (Plano 5). Aqui ele é só uma malha plana nomeada.

## Faixas

| Faixa | Área | Fonte | Forma |
|---|---|---|---|
| Platô | dentro da poligonal `AR-CNT-POL` | cota única | plano; cota = mediana do levantamento sob os lotes, arredondada a 0,5 m (`cena.toml`, `plato_cota`, padrão calculado) |
| Talude | 0–20 m fora da poligonal | interpolação | do platô ao morro, contínuo |
| Morro | até ~300 m da poligonal | curvas do levantamento (cotação do Plano 3) | gaussiana σ ≈ 25 m: só as formas grandes |
| Transição | ~100 m | mistura linear | levantamento suavizado → Copernicus |
| Entorno | até 4 km do centro dos lotes | Copernicus GLO-30 (DSM, 30 m) | sem suavização extra; sem exagero vertical |

- A lagoa continua escavada no platô (água no percentil 10 da margem, terreno abaixo dela).
- A faixa norte sem curvas, hoje preenchida por vizinho mais próximo, passa a vir do Copernicus.
- Vias, calçadas, verdes e lotes continuam assentados com os offsets do `cena.toml`; o
  rebaixo de 0,6 m e a suavização σ 8 m do Plano 3 saem (o platô plano os dispensa).

## Copernicus

- Tile público, sem login: `Copernicus_DSM_COG_10_S04_00_W039_00_DEM` (bucket AWS
  `copernicus-dem-30m`); o raio de 4 km cabe nele. Baixado uma vez para `cache/dem/`.
- Reprojeção de EPSG:4326 para EPSG:31984 e para as coordenadas locais da cena
  (origem de `dados/georref.json`), reamostrado numa grade de 30 m.
- **Datum:** o Copernicus usa EGM2008; o levantamento, a referência dele. A diferença é
  a mediana de (levantamento − Copernicus) na área em comum, fora da poligonal; o script
  a imprime e a aplica ao Copernicus.
- O Copernicus é modelo de superfície (copa e telhado entram): aceito no entorno.

## Mar

- Pontos do Copernicus com cota ≤ 0 (após o ajuste) e ligados à borda do recorte são mar.
- Malha plana `Mar` em z = 0 cobrindo o mar do recorte, material `mar` (cor provisória);
  o terreno debaixo desce um pouco para não brigar com o plano.
- O front troca o material `mar` por um shader de água (Plano 5).

## Malhas e arquivos

- `loteamento.glb`: terreno perto (grade de 5 m sobre a área do levantamento),
  áreas, lagoa e lotes, como hoje. Nomes e contrato de lotes inalterados.
- `entorno.glb` (novo, mesma pasta `6-PROJETOS/10-MAQUETE INTERATIVA/`): objeto
  `Entorno` (grade de 30 m até 4 km, com furo onde está o terreno perto) e `Mar`.
- **Costura:** a borda do furo do entorno usa as mesmas cotas da borda do terreno perto;
  sem fresta nem degrau na vista.
- Orçamento: entorno < 3 MB antes do meshopt (que fica no Plano 5).
- Prévias: vista geral do raio de 4 km e vista do platô.

## Testes

- Platô: todo ponto da grade dentro da poligonal na cota do platô; talude contínuo
  (sem salto entre células vizinhas além do declive do talude).
- Transição levantamento → Copernicus sem degrau acima de um limite.
- Costura: cotas da borda do furo do entorno = cotas da borda do terreno perto.
- Datum: diferença mediana medida só na área em comum; com dado sintético deslocado
  de 3 m, o ajuste devolve 3 m.
- Mar: só a água ligada à borda vira mar (lagoa interna não vira).
- GLB: `Entorno` e `Mar` nomeados; `loteamento.glb` mantém os 347 lotes.

## Fora do escopo

Prédios, vias e áreas do OSM/Overture, vegetação, POIs e minutos de carro (Plano 4);
shader do mar, meshopt e front (Plano 5); estande, portaria e clube (Plano 3b).
