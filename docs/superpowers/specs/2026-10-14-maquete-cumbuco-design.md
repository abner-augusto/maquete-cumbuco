# Maquete interativa — Alternativa Residencial Cumbuco (Fase 1, Cancun)

Spec de design, aprovada em conversa em 14/10/2026. Status: **aguardando revisão do Abner**.

## 1. Objetivo

Um site com maquete 3D em Three.js da Fase 1 (Cancun) do loteamento Cidade das Américas, com a marca **Alternativa Residencial Cumbuco**, usado na venda dos lotes. O cliente e o corretor clicam num lote e veem a ficha dele, exploram o entorno e os pontos de interesse (próximos e distantes) e abrem o estande, a portaria e o clube com fotos e planta humanizada.

O mesmo `dist/` atende dois usos:

- **Online:** Worker de assets estáticos no Cloudflare.
- **Offline:** pasta com `iniciar.cmd`, que sobe um servidor local. `file://` com duplo clique não funciona (módulos ES e `fetch` do GLB) e não é objetivo.

### Fora do escopo

- Integração com o CV CRM (API, sincronia, iframe, "Abrir no CV"): o cadastro do loteamento no CV ainda não está completo.
- Simulação de sol e de horário, e painel de sol.
- Zoom até planta humanizada de lote ou casa: o produto ainda é só lote.
- Fases 2 a 10 do masterplan.
- Chrome de corretor, modo apresentação e resumo de vendas do espelho do Manoa.
- Filtro por faixa de área e indicador de "vista para o mar": oferecidos e recusados na v1.

## 2. Referências

| Referência | O que se aproveita |
|---|---|
| `$REPOS_DIR/cv_espelho_vendas` (Manoa) | Esqueleto do front (Svelte 5 + Three.js puro, Cena, Folha de três batentes, Ficha, tema por tokens), pipeline `scripts/entorno` (OSM + Overture → Blender → `entorno.glb`, vegetação instanciada, minutos pelo grafo OSM, pontos no vazio), testes e2e com Playwright, publicação como Worker estático |
| Casa do Benevides (`10 - BENEVIDES - PA/.../6-PROJETOS/CASA 2Q SEM SUITE 43,47m2 - MODELO 3D/casa0_benevides_v21.blend`) | Método: o desenho CAD é a fonte, e o modelo é **gerado inteiro por script** no Blender, reexecutável a cada ajuste |
| `$REPOS_DIR/UFCIM-FRONT3D` | Mapeamento correto dos gestos de toque da câmera |

O Manoa foi modelado por imagens e planta humanizada. Aqui há dados (DWG, curvas de nível, KMZ, cadastro), então o loteamento sai dos dados, não de imagem.

## 3. Arquitetura

Repo novo: `$REPOS_DIR/maquete-cumbuco`, derivado do `cv_espelho_vendas`, sem tocar no Manoa (em produção e acoplado ao CRM). A duplicação de código é aceita. Se o Cumbuco ganhar CRM, decide-se então entre convergir com o espelho ou portar a integração.

```
① MARCA ──────────────► tokens (cores/fontes) + SVGs ──────────┐
② LOTEAMENTO  DXF ─► script Blender ─► loteamento.glb          │
              DXF+IPTU+tabela ─► lotes.json                    ├─► ④ FRONT (Svelte+Three) ─► dist/
③ ENTORNO  OSM/Overture/DEM ─► script Blender ─► entorno.glb   │      ├─ Cloudflare Worker estático
           POIs curados ─► pontos.json (+ fotos)               ┘      └─ offline: iniciar.cmd
```

| Pasta | Responsabilidade |
|---|---|
| `marca/` | Logo vetorizado (SVG), `tokens.css`, brandbook preliminar (HTML + PDF) |
| `scripts/loteamento/` | DXF → inventário de layers, georreferência, relevo, `lotes.json`, geração no Blender, export de `loteamento.glb` |
| `scripts/entorno/` | Derivado do Manoa: base OSM/Overture/DEM, cena do entorno, vegetação, minutos de carro, export de `entorno.glb` |
| `scripts/pontos/` | Curadoria dos POIs, fotos e créditos → `pontos.json` |
| `dados/` | `lotes.json`, `marcos.json`, `pontos.json` (gerados) e `config.json` (editado à mão) |
| `frontend/` | Cena, Folha, Ficha, marcos, pontos, marca aplicada |

**Fontes de verdade** (lidas da pasta do terreno, nunca copiadas à mão). Raiz: `$TERRENO_DIR\`, apontada por `TERRENO_DIR` no `.env`.

| Dado | Arquivo |
|---|---|
| Geometria dos lotes, vias e áreas | `6-PROJETOS/01-URBANISMO/DWG/PLANTA VENDA.dwg` (07/10/2026); conferência com `00-CIDADE DAS AMÉRICAS- MASTERPLAN GERAL-R05,.dwg` |
| Curvas de nível | DWG do urbanismo, se trouxer as curvas; senão `2-LEVANTAMENTOS/PLANTAS_BASE/C) BASE GRAFICA 1 ETAPA C CURVAS DE NIVEL 03-PL-ARQ-MPL-0721 R05.pdf` |
| Cadastro | `4-PREFEITURA/IPTU_2025/00-INDICE IPTU 2025 - LOTES CANCUN.csv` (quadra; lote; tipo; inscrição) |
| Preço | Tabela de preços indicada em `config.json`; hoje a referência é `1-ADMINISTRATIVO/FINANCEIRO/Tab Lancamento SET26 R01.xls`, ainda **não validada** para venda |
| Estande | `6-PROJETOS/08-ESTANDE/2026-10-07 estande - implantacao georreferenciada.kmz`, `... v10c.dwg`, `... v10c - planta humanizada.pdf`, `... v10c - humanizada Gemini (editado).png` |
| Portaria | `6-PROJETOS/05-PORTARIA/portaria e rotatoria 3d categorizado (do SKP).blend`, artes e plantas |
| Clube | `6-PROJETOS/04-CLUBE/` (renders e projeto anterior) |
| Mídia | `6-PROJETOS/09-MIDIA/`, `2-LEVANTAMENTOS/FOTOS/` |
| Restinga | `2-LEVANTAMENTOS/AMBIENTAL/MAPA_RESTRICOES_*.pdf` e zonas do OSM |

O `2-LEVANTAMENTOS/MASTER.kmz` está **desatualizado** nos lotes comerciais (ata de 08/10/2026) e não serve de fonte de geometria.

## 4. Marca

**Arquitetura de marca:** o produto **Alternativa Residencial Cumbuco** fica em destaque, e a marca-mãe **Alternativa Desenvolvimento Urbano** entra como assinatura discreta (rodapé e carimbo).

**Insumos** (todos raster, aparentemente gerados por IA):

- Produto: `6-PROJETOS/09-MIDIA/LOGO Preliminar.jpeg`. Arco de marquise, pipa de kitesurf, sol no horizonte e reflexo; ouro sobre creme; tagline "Natureza • Arte • Liberdade".
- Marca-mãe: `6-PROJETOS/09-MIDIA/Estudo Logo Joao Carlos/` (seis estudos). Arco e pilar vertical, e numa variante um "N" monolítico; ouro escovado sobre creme ou preto; tagline "Cidades que inspiram gerações".

**DNA comum:** arco de casca, ouro escovado, fundo creme (modo claro) ou preto (modo escuro), serifada clássica de alto contraste em "ALTERNATIVA", sans geométrica fina com espaçamento largo nas sub-linhas, filete com estrela central.

**Entregáveis:**

1. Prancha comparativa do logo preliminar e dos seis estudos, com as combinações possíveis. **Gate: o Abner escolhe a versão ou a mistura.**
2. `tokens.css`: paleta medida (ouro claro, ouro escuro, bronze, creme, preto) e fontes abertas do Google Fonts, uma serifada do tipo Trajan (candidatas: Cinzel, Marcellus) e uma sans geométrica fina (candidatas: Jost, Montserrat). Sai **antes** da escolha do logo, para não travar o front.
3. Vetorização em SVG: produto horizontal e vertical; positivo, negativo e monocromático; símbolo isolado (favicon e ícones); assinatura da marca-mãe.
4. Brandbook preliminar em HTML e PDF: arquitetura de marca, área de proteção, tamanho mínimo, usos certos e errados, paleta, tipografia e cores de status (fixas, fora da marca). O brandbook anota as fontes profissionais equivalentes (família Trajan e similares), para a Brasil Urbano decidir se compra.

## 5. Cena e interação

A gramática é a do espelho do Manoa: uma **Cena** única que nunca troca de tela e uma **Folha** inferior com três batentes (some, espiar, cheia).

- **Abertura:** vista aérea oblíqua da Fase 1 com o mar e a lagoa no quadro. Folha de boas-vindas só na primeira visita: marca e três dicas de gesto.
- **Lotes:** placas assentadas no relevo. A cor vem do tipo (residencial, uso misto) ou, se o JSON tiver status, do status (disponível, reservado, vendido), com cores fixas fora do tema. No desktop, passar o mouse realça o lote e mostra o rótulo "Q07 · L04". O clique ou toque leva a câmera até o lote e abre a Ficha. Busca por quadra e lote ("7 4", "Q7L4").
- **Marcos (estande, portaria, clube):** volume simplificado com ícone flutuante. O clique abre na Folha uma galeria (fotos, renders e, no estande, a planta humanizada), com ampliação em tela cheia. O estande tem também "Como chegar", que abre o Google Maps na coordenada do KMZ.
- **Entorno e pontos:** ao afastar a câmera entram os POIs próximos (até cerca de 3 km), com pin, nome e minutos de carro pelo grafo OSM. Os POIs distantes ficam **no vazio**, como no Manoa: na direção real, a uma distância comprimida, com km e minutos verdadeiros no rótulo. Exemplos: Praia de Iracema, Pecém, Cumbuco, Taíba, Lagoa do Banana, picos de kitesurf, aeroporto. O clique abre um popup com foto real e crédito. A lista dos pontos na Folha é a alternativa acessível.
- **Câmera:** órbita com limites de distância e inclinação; gestos de toque do UFCIM-FRONT3D; botões de recentralizar e de alternar loteamento/entorno; rosa dos ventos.
- **Luz:** fixa, de fim de tarde. Modo claro e escuro pelo `prefers-color-scheme` (creme e preto).
- **Parâmetros de URL:** `?lote=Q07L04` abre direto na Ficha do lote (para compartilhar); `?precos=0` esconde os preços (regra na §6).
- **Público:** cliente no celular em retrato e corretor em tablet ou desktop. WCAG AA: contraste, foco visível, teclado e movimento reduzido.

## 6. Dados e Ficha

Um script de build gera os dados. **Nenhum número é digitado à mão no front.**

| Arquivo | Origem | Conteúdo |
|---|---|---|
| `lotes.json` | DXF × índice de IPTU × tabela de preços | id `Q07L04`, quadra, lote, tipo, área, frente, fundo e laterais, polígono local, inscrição de IPTU (opcional), preço total e por m² (opcional), status (opcional) |
| `marcos.json` | KMZ, DWG e pastas de mídia | id, nome, posição, galeria (imagens com legenda), planta humanizada, coordenada para "Como chegar" |
| `pontos.json` | curadoria | nome, categoria, coordenada, km, minutos de carro, foto, crédito, licença, faixa (próximo ou distante) |
| `config.json` | editado à mão | `mostrarPrecos`, nome e data de referência da tabela de preços, textos da marca |

**Conferência no build.** O relatório vai para `dados/relatorio-conferencia.md`.

| Caso | Efeito |
|---|---|
| Lote no desenho sem linha no cadastro, ou o contrário | **Erro**: o build falha |
| Área calculada pela geometria difere da área escrita na planta acima de 0,5% | **Erro** |
| Lote sem inscrição de IPTU | Aviso; o lote aparece sem o campo |
| Lote sem preço com `mostrarPrecos: true` | **Erro** |

O relatório explicita a diferença entre 347 lotes no projeto, 344 matrículas e 325 linhas no índice de IPTU, sem escondê-la.

**Ficha do lote (na Folha):**

- Cabeçalho "Quadra 07 · Lote 04" e o tipo.
- Área em m², dimensões e miniatura do contorno com cotas.
- Inscrição de IPTU, quando houver.
- Preço total e por m², só com os preços ligados, com o carimbo "Tabela <nome> · ref. <data>".
- Status, quando houver.
- Botão "Compartilhar" com o link `?lote=`.

**Regra dos preços:**

| `config.json` `mostrarPrecos` | URL | Preços |
|---|---|---|
| `false` (**padrão**) | qualquer | escondidos; a URL não liga |
| `true` | sem parâmetro | visíveis |
| `true` | `?precos=0` | escondidos |

Com os preços escondidos, a seção some da Ficha sem deixar espaço vazio. O padrão `false` vale até existir tabela aprovada para venda: a SET26 é só referência no vault (decisão de 05/10/2026).

**Mídia:** o build converte fotos e renders para WebP em dois tamanhos (miniatura e tela cheia). As fotos dos POIs são próprias quando existirem; senão vêm do Wikimedia Commons com licença livre, com crédito no popup. Imagem de banco sem direito de uso não entra.

## 7. Modelagem

O método é o do Benevides: **o CAD é a fonte e o Blender é só destino de script.** Nada é modelado à mão; ajuste é editar o script e rodar de novo.

### 7.1 Loteamento (`scripts/loteamento/`)

1. **DWG → DXF** pelo ODA File Converter e **inventário de layers** do `PLANTA VENDA.dwg`: lotes, números de lote e quadra, meio-fio, calçadas, áreas verdes, APP, lagoa, curvas de nível. **Gate: o Abner confere o inventário.**
2. **Georreferência:** verificar se o DWG está em UTM SIRGAS 2000, fuso 24S. Se não estiver, registrar o desenho pelo KMZ do estande e por pontos notáveis (rotatória, CE-090). A cena usa origem local e norte verdadeiro, e a transformação fica registrada em arquivo.
3. **Relevo:** TIN pelas curvas de nível do projeto dentro do loteamento e Copernicus GLO-30 no entorno, costurados na borda. Sem exagero vertical.
4. **Geração no Blender (bpy):** terreno; lotes como placas finas assentadas no relevo, **um objeto por lote com nome `Q07L04`** (chave do clique e do `lotes.json`); vias, calçadas e meio-fio; áreas verdes; lagoa como água.
5. **Volumes simplificados** (só casca, cobertura e aberturas principais; sem móveis nem paredes internas):
   - Estande: footprint da v10c extrudado, com cobertura.
   - Portaria e rotatória: o `.blend` existente, sem interiores.
   - Clube: massa a partir do projeto anterior.

### 7.2 Entorno (`scripts/entorno/`)

Derivado do Manoa, com novo centro e raio de cerca de 2,5 km: prédios do Overture extrudados, vias e áreas do OSM, mar, faixa de praia e dunas pelo relevo. Os minutos de carro saem do grafo OSM.

### 7.3 Vegetação

Instanciada como no Manoa, com 3 ou 4 espécies (coqueiro, cajueiro, arbusto de restinga). Posições pelas zonas de restinga (OSM e mapa de restrições ambiental) e pelo eixo das grandes avenidas da Fase 1, com espaçamento regular. Instâncias de GPU, sem duplicar malha.

### 7.4 Export e arquivos

- `loteamento.glb` e `entorno.glb` separados, com compressão meshopt. O entorno pode carregar depois do loteamento.
- **Orçamento: menos de 15 MB no primeiro carregamento**, medido sobre o `dist/`.
- Os `.blend` e GLBs gerados ficam na pasta do terreno, em `6-PROJETOS/10-MAQUETE INTERATIVA/`. Essas maquetes **vão para o Drive** pelo sync; scripts não (os `*.py` já estão excluídos do sync). Os GLBs publicados são copiados para o `frontend/public` no build.

## 8. Ordem de execução

O símbolo ⛔ marca um gate do Abner.

1. Repo, spec e plano de implementação.
2. Inventário do DXF e georreferência ⛔. Em paralelo: paleta, fontes e prancha comparativa da marca ⛔ (escolha do logo).
3. Dados: `lotes.json` e relatório de conferência.
4. Blender: loteamento, relevo e volumes do estande, da portaria e do clube.
5. Entorno, vegetação e curadoria dos pontos ⛔ (lista e fotos aprovadas).
6. Front: Cena, Ficha, marcos, pontos e marca aplicada. A vetorização e o brandbook fecham aqui.
7. Publicação: Worker estático e pacote offline com `iniciar.cmd` ⛔ (proteção do nome, ver §10).
8. Uma única sessão de revisão visual no fim.

## 9. Testes

- **pytest** no pipeline de dados: leitura do DXF, cruzamento de chaves, tolerância de área, regras do relatório de conferência.
- **Playwright e2e** no front:
  - o clique num lote abre a Ficha certa;
  - `?lote=` abre direto na Ficha;
  - a tabela de regras dos preços (§6) se cumpre nas três linhas;
  - o build roda pelo `iniciar.cmd` sem internet.
- **Orçamento de peso:** um script mede o `dist/` e falha acima de 15 MB no primeiro carregamento.
- Aparência, gestos e leitura da cena: avaliados a olho na sessão final.

## 10. Riscos e pendências

- **Confidencialidade do nome.** "Alternativa" é confidencial até a assinatura do compliance do uso do nome (MOC de Cumbuco). Antes de publicar a URL, decidir entre `noindex` com caminho não óbvio e Cloudflare Access. ⛔ no passo 7.
- **Contagem de lotes:** 347 no projeto, 344 matrículas, 325 no índice de IPTU. O relatório expõe as diferenças; o desenho de venda é a geometria.
- **Tabela de preços não validada:** os preços ficam desligados por padrão (§6).
- **Layers do DWG desconhecidas:** se o `PLANTA VENDA.dwg` não tiver os lotes como polilinhas fechadas, o passo 2 inclui reconstruir os polígonos, e o prazo cresce.
- **Logos gerados por IA:** a vetorização é redesenho, não traço automático; detalhes podem mudar na transcrição para vetor.
