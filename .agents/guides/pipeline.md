Leia este guia antes de mudar um script do pipeline, um esquema de `dados/` ou a ordem de geração.

# Contratos do pipeline

- **Id de lote:** `Q<quadra>L<lote>`, com quadra numérica de 2 dígitos (`Q07L04`) ou alfabética (`QHL01`, `QML03`) e lote de 2 dígitos. É o nome do objeto no Blender, a chave do `lotes.json` e o valor de `?lote=`.
- **Origem local:** `dados/georref.json` → `{"crs": "EPSG:31984", "origem": {"E": <float>, "N": <float>}}`. Coordenada local = (E − E0, N − N0) em metros; no Three.js, x = leste, z = −norte, y = cota.
- **`dados/lotes.json`:** esquema em [`scripts/loteamento/saida.py`](../../scripts/loteamento/saida.py).
- **`dados/pontos.json`:** `{"versao": 1, "pontos": [{nome, categoria, lat, lon, x, y, km, minutos_carro, faixa ("proximo" até 3 km, "distante"), osm, foto, credito, licenca, licenca_url, fonte_foto}]}`; `foto` relativo a `dados/` ou `null` até a aprovação. Curadoria (fonte editada à mão) em `scripts/pontos/curadoria.json`.
- **`vegetacao.json`:** campos `x_dm, y_dm, z_cm, escala_pct, rotacao_graus` por espécie (`coqueiro`, `cajueiro`, `arbusto`), embaralhados; malhas `VEG_<especie>` no `vegetacao.glb`, base em z = 0.
- **Objetos do chão:** `Entorno_<ij>` (`entorno.glb`) e `Terreno_<ij>` (`loteamento.glb`), `i` 0/1 = oeste/leste, `j` 0/1 = sul/norte; cada um com o material `chao_mapa_<ij>` do seu tile. `cache/entorno/mapa.json` = `{"tiles": {ij: {arquivo, ext, janela, px}}}`.
- **Pivô dos lotes:** a origem de cada objeto `Q…` é o centro da caixa do topo do lote (topo a +0,40 m do platô); no glTF, `translation` = (x, z, −y).
- **Marcos:** `clube - sem mobiliario.glb` e `portaria e rotatoria.glb` em `10-MAQUETE INTERATIVA/`; o clube está girado +28° em torno de `PIVOT` (40,56; 45,98) em relação à portaria (detalhes em `scripts/marcos/conversao/README.md`).
- **Acesso:** a faixa do DWG entre a rotatória e a CE vira avenida em rampa (`scripts/loteamento/acesso.py`, `[acesso]` do `cena.toml`): seção da avenida, perfil plano → rampa → patamar, boca em curva e ilha triangular; objetos `AcessoPista`, `AcessoCalcadas`, `AcessoCanteiro` no `loteamento.glb`. A faixa da CE fica no chão natural.
- **`marcos.glb`:** objetos `Clube`, `Portaria`, `Rotatoria` já no referencial local, com compressão Draco (o front carrega com o `DRACOLoader`, decoder local em `draco/`). Os outros GLBs são comprimidos com meshopt no `copiar-assets` do front, que registra os dois decoders.
- **`dados/marcos.json`:** `{"versao": 1, "marcos": [{id, nome, x, y, z, objeto, galeria: [{foto, legenda}], planta, lat, lon}]}`; `objeto` é o nome no `marcos.glb` (`Clube`, `Portaria`, `Rotatoria`) ou `null` (estande, que leva também `pegada`); fotos relativas a `dados/`.
- **Ordem de geração:** `entorno.extrair` (as vias do OSM: o terreno acha a CE nelas) → `loteamento.terreno` (grava `cache/cena/acesso.json`) → `marcos.blender --extrair` → `marcos.encaixe` → `loteamento.cena` → `entorno.preparar` → `entorno.vegetacao` → `loteamento.blender` → `marcos.blender` → `marcos.dados`.
