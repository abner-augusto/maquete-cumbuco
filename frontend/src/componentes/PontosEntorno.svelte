<!--
  Pontos de referência como camada 2D sobre a cena no lugar de pins 3D. Perto: marcador
  ancorado no chão. Além do raio: pílula na borda da tela, com a seta para o rumo do ponto.
  A camada fica atrás de toda a interface: as pílulas não desviam do carimbo nem da folha.
-->
<script lang="ts">
  import { fade } from 'svelte/transition';
  import { MARGEM_FADE, type QuadroEntorno, type Tela } from '../lib/cena/cena';
  import { rotuloKm, type Ponto } from '../lib/pontos';
  import { rotulosQueCabem } from '../lib/cena/entorno';
  import Icone from './Icone.svelte';
  import IconePonto, { iconeDaCategoria } from './IconePonto.svelte';

  let {
    pontos,
    quadro,
    selecionado,
    aoEscolher,
    masterplan,
  }: {
    pontos: Ponto[];
    quadro: QuadroEntorno;
    selecionado: number | null;
    aoEscolher: (id: number) => void;
    /** As etiquetas das fases são do masterplan: com a projeção desligada, somem junto. */
    masterplan: boolean;
  } = $props();

  let largura = $state(0);
  let altura = $state(0);

  // Tamanho da pílula distante, para encaixá-la inteira na tela, a `BORDA` px dela. Na tela
  // estreita (celular) as 15 pílulas não cabem na borda e cobririam a cena: vira um círculo de
  // 44 px com o ícone da categoria e a ponta no rumo; o nome fica na lista da folha.
  const compacto = $derived(largura > 0 && largura < 600);
  const L = $derived(compacto ? 44 : 196);
  const A = $derived(compacto ? 44 : 46);
  const FOLGA = 6;
  const BORDA = 12;

  const formatoRaio = (raio: number) => (raio < 1000 ? `${raio} m` : `${String(raio / 1000).replace('.', ',')} km`);

  // Ponto distante que cai na tela vira marcador no lugar real. A folga para entrar é maior que a
  // para sair: no limite da vista, o ponto não alterna entre marcador e seta.
  const ENTRA = 40;
  const SAI = 4;
  const ancorados = new Set<number>();
  const naVista = (t: Tela, folga: number) => t.x >= folga && t.x <= largura - folga && t.y >= folga && t.y <= altura - folga;

  /** Esmaece ao se aproximar da borda da tela: some de vez a `MARGEM_FADE` px do lado de fora. */
  const opacidade = (t: Tela) => Math.min(Math.max((Math.min(t.x, t.y, largura - t.x, altura - t.y) + MARGEM_FADE) / (MARGEM_FADE * 1.5), 0), 1);

  // As setas da borda servem a quem olha o entorno de longe; de perto da maquete, saem devagar.
  const presenca = $derived(Math.min(Math.max((quadro.alcance - 500) / 700, 0), 1));

  const camadas = $derived.by(() => {
    const marcadores: { ponto: Ponto; x: number; y: number; opacidade: number }[] = [];
    const rumos: { ponto: Ponto; angulo: number }[] = [];
    pontos.forEach((ponto, i) => {
      const posicao = quadro.pontos[i];
      if (!posicao) return;
      if (!('angulo' in posicao)) return void marcadores.push({ ponto, ...posicao, opacidade: opacidade(posicao) });
      const ancorado = posicao.tela !== null && naVista(posicao.tela, ancorados.has(ponto.id) ? SAI : ENTRA);
      if (ancorado) {
        ancorados.add(ponto.id);
        marcadores.push({ ponto, ...posicao.tela!, opacidade: 1 });
      } else {
        ancorados.delete(ponto.id);
        rumos.push({ ponto, angulo: posicao.angulo });
      }
    });
    return { marcadores: comRotulos(marcadores), distantes: naBorda(rumos) };
  });

  /**
   * Rótulos que se tocariam (perto do horizonte os pontos se juntam) não se empilham: o escolhido
   * e depois o mais perto da origem ficam com o rótulo; os outros mostram só o ponto. A caixa do
   * rótulo é estimada pelo número de letras, sem medir o DOM a cada quadro.
   */
  function comRotulos<T extends { ponto: Ponto; x: number; y: number }>(marcadores: T[]) {
    const ocupadas: { x0: number; y0: number; x1: number; y1: number }[] = [];
    const ordem = [...marcadores].sort((a, b) => Number(b.ponto.id === selecionado) - Number(a.ponto.id === selecionado) || a.ponto.km - b.ponto.km);
    const comRotulo = new Set<number>();
    for (const { ponto, x, y } of ordem) {
      const largura = Math.min(ponto.nome.length * 6.6 + 16, ponto.id === selecionado ? 220 : 150);
      const caixa = { x0: x - largura / 2, y0: y - 34, x1: x + largura / 2, y1: y - 9 };
      if (ocupadas.some(o => caixa.x0 < o.x1 && caixa.x1 > o.x0 && caixa.y0 < o.y1 && caixa.y1 > o.y0)) continue;
      ocupadas.push(caixa);
      comRotulo.add(ponto.id);
    }
    return marcadores.map(m => ({ ...m, rotulo: comRotulo.has(m.ponto.id) }));
  }

  /**
   * Cada seta vai onde o raio que sai da origem, no rumo do ponto, encontra a borda da tela.
   * Rumos parecidos (vários distantes caem no mesmo lado) se afastam ao longo da borda, em
   * ordem e numa passada só: um passo pequeno da câmera move as pílulas pouco, sem trocar de lugar.
   */
  function naBorda(rumos: { ponto: Ponto; angulo: number }[]) {
    const r = { x0: BORDA + L / 2, y0: BORDA + A / 2, x1: largura - BORDA - L / 2, y1: altura - BORDA - A / 2 };
    if (presenca === 0 || !rumos.length || r.x1 < r.x0 || r.y1 < r.y0) return [];
    const W = r.x1 - r.x0;
    const H = r.y1 - r.y0;
    const P = 2 * (W + H);
    const c = { x: Math.min(Math.max(quadro.origem.x, r.x0), r.x1), y: Math.min(Math.max(quadro.origem.y, r.y0), r.y1) };
    // Posição ao longo do perímetro, em sentido horário a partir do canto superior esquerdo.
    const perimetro = (angulo: number) => {
      const dx = Math.cos(angulo);
      const dy = Math.sin(angulo);
      let t = Infinity;
      if (dx > 1e-6) t = Math.min(t, (r.x1 - c.x) / dx);
      if (dx < -1e-6) t = Math.min(t, (r.x0 - c.x) / dx);
      if (dy > 1e-6) t = Math.min(t, (r.y1 - c.y) / dy);
      if (dy < -1e-6) t = Math.min(t, (r.y0 - c.y) / dy);
      if (!Number.isFinite(t)) t = 0;
      const x = c.x + dx * t;
      const y = c.y + dy * t;
      if (Math.abs(y - r.y0) < 0.5) return x - r.x0;
      if (Math.abs(x - r.x1) < 0.5) return W + (y - r.y0);
      if (Math.abs(y - r.y1) < 0.5) return W + H + (r.x1 - x);
      return 2 * W + H + (r.y1 - y);
    };
    const noPerimetro = (s: number): Tela => {
      s = ((s % P) + P) % P;
      if (s < W) return { x: r.x0 + s, y: r.y0 };
      if (s < W + H) return { x: r.x1, y: r.y0 + s - W };
      if (s < 2 * W + H) return { x: r.x1 - (s - W - H), y: r.y1 };
      return { x: r.x0, y: r.y1 - (s - 2 * W - H) };
    };
    // Em cima e embaixo, as pílulas lado a lado pedem a largura; nas laterais, a altura.
    const vao = (s: number) => {
      const p = ((s % P) + P) % P;
      return (p < W || (p >= W + H && p < 2 * W + H) ? L : A) + FOLGA;
    };
    if (compacto) return naBordaCompacta(rumos.map(rumo => ({ ...rumo, ...noPerimetro(perimetro(rumo.angulo)) })));
    const itens = rumos.map(rumo => ({ ...rumo, s: perimetro(rumo.angulo) })).sort((a, b) => a.s - b.s);
    const original = itens.map(item => item.s);
    // Na virada de um canto, a distância ao longo da borda engana: confere as caixas na tela.
    const cobre = (s1: number, s2: number) => {
      const a = noPerimetro(s1);
      const b = noPerimetro(s2);
      return Math.abs(a.x - b.x) < L + FOLGA && Math.abs(a.y - b.y) < A + FOLGA;
    };
    for (let i = 1; i < itens.length; i++) {
      const anterior = itens[i - 1]!;
      itens[i]!.s = Math.max(itens[i]!.s, anterior.s + Math.max(vao(anterior.s), vao(itens[i]!.s)));
      for (let k = 0; k < 60 && cobre(anterior.s, itens[i]!.s); k++) itens[i]!.s += 4;
    }
    // Recentra o grupo onde os rumos apontavam, para ele não escorregar só para um lado.
    const desvio = itens.reduce((soma, item, i) => soma + item.s - original[i]!, 0) / itens.length;
    return itens.map(({ ponto, angulo, s }) => ({ ponto, angulo, ...noPerimetro(s - desvio), visivel: true, fora: 0 }));
  }

  /**
   * Celular: cada círculo fica no ponto da borda do seu rumo, atrás da interface, sem empurrar os
   * vizinhos. Se dois se chocam, o mais perto fica e o outro some (fade), já que é o mais distante.
   * Quanto mais longe o ponto, mais o círculo sai pela borda: de 10 a 25 km, até meio para fora.
   */
  function naBordaCompacta(itens: { ponto: Ponto; angulo: number; x: number; y: number }[]) {
    const ficam: { x: number; y: number }[] = [];
    return [...itens].sort((a, b) => Number(b.ponto.id === selecionado) - Number(a.ponto.id === selecionado) || a.ponto.km - b.ponto.km)
      .map(item => {
        const visivel = !ficam.some(o => Math.abs(o.x - item.x) < L + FOLGA && Math.abs(o.y - item.y) < A + FOLGA);
        if (visivel) ficam.push(item);
        const fora = Math.min(Math.max((item.ponto.km - 10) / 15, 0), 1) * (L / 2);
        return { ...item, x: item.x + Math.cos(item.angulo) * fora, y: item.y + Math.sin(item.angulo) * fora, visivel, fora };
      });
  }
</script>

<div class="camada" bind:clientWidth={largura} bind:clientHeight={altura} aria-label="Pontos de referência na cena">
  {#each rotulosQueCabem(quadro.aneis, 52) as anel (anel.raio)}
    <span class="anel" style:left="{anel.tela!.x}px" style:top="{anel.tela!.y}px" aria-hidden="true">{formatoRaio(anel.raio)}</span>
  {/each}

  {#each masterplan ? quadro.fases : [] as fase (fase.id)}
    {#if fase.tela}
      <span class="fase" style:left="{fase.tela.x}px" style:top="{fase.tela.y}px" style:opacity={opacidade(fase.tela)}><b>{fase.nome}</b>Em breve</span>
    {/if}
  {/each}

  {#each camadas.marcadores as { ponto, x, y, opacidade, rotulo } (ponto.id)}
    <button
      class="marcador"
      class:ativo={ponto.id === selecionado}
      style:left="{x}px"
      style:top="{y}px"
      style:opacity={opacidade}
      aria-label="{ponto.nome}, {rotuloKm(ponto.km)}"
      aria-pressed={ponto.id === selecionado}
      onclick={() => aoEscolher(ponto.id)}
      transition:fade={{ duration: ponto.distante ? 160 : 0 }}>
      <span class="rotulo" class:oculto={!rotulo}>{ponto.nome}{ponto.distante ? ` · ${rotuloKm(ponto.km)}` : ''}</span>
    </button>
  {/each}

  {#each camadas.distantes as { ponto, angulo, x, y, visivel, fora } (ponto.id)}
    {#if compacto}
      <button
        class="distante compacto"
        class:ativo={ponto.id === selecionado}
        class:escondido={!visivel}
        style:left="{x}px"
        style:top="{y}px"
        style:opacity={visivel ? presenca * (1 - (fora / L) * 0.5) : 0}
        transition:fade={{ duration: 160 }}
        aria-label="{ponto.nome}, {rotuloKm(ponto.km)}, fora do mapa"
        aria-hidden={!visivel}
        tabindex={visivel ? 0 : -1}
        aria-pressed={ponto.id === selecionado}
        onclick={() => aoEscolher(ponto.id)}>
        <span class="ponta" style:transform="rotate({angulo}rad)" aria-hidden="true"></span>
        <IconePonto nome={iconeDaCategoria(ponto.categoria)} tamanho={18} />
      </button>
    {:else}
    <button
      class="distante"
      class:ativo={ponto.id === selecionado}
      style:left="{x}px"
      style:top="{y}px"
      style:opacity={presenca}
      transition:fade={{ duration: 160 }}
      style:width="{L}px"
      style:height="{A}px"
      aria-label="{ponto.nome}, {rotuloKm(ponto.km)}, fora do mapa"
      aria-pressed={ponto.id === selecionado}
      onclick={() => aoEscolher(ponto.id)}>
      <span class="seta" style:transform="rotate({angulo}rad)"><Icone nome="seta" tamanho={18} /></span>
      <span class="texto">
        <span class="nome">{ponto.nome}</span>
        <span class="tempo">{rotuloKm(ponto.km)} · <IconePonto nome="carro" tamanho={13} />{ponto.minutos_carro} min<span class="leitor"> de carro</span></span>
      </span>
    </button>
    {/if}
  {/each}
</div>

<style>
  .camada { position: absolute; inset: 0; pointer-events: none; overflow: hidden; }
  .anel {
    position: absolute; transform: translate(6px, -50%);
    font-size: 11.5px; font-weight: 600; color: var(--tema-tinta);
    text-shadow: 0 0 3px var(--tema-papel), 0 0 6px var(--tema-papel);
  }
  /* Etiqueta no centro de cada fase ainda por vir: só informa, não recebe toque. */
  .fase {
    position: absolute; transform: translate(-50%, -50%); display: flex; flex-direction: column; align-items: center;
    padding: 5px 12px; border-radius: var(--raio-2); text-align: center; line-height: 1.2; white-space: nowrap;
    background: color-mix(in srgb, var(--tema-papel) 80%, transparent); color: var(--tema-tinta-2);
    border: 1px solid var(--tema-filete-forte); box-shadow: var(--tema-sombra-1); font-size: 10px;
  }
  .fase b { color: var(--tema-tinta); font-size: 11px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; }
  .marcador {
    position: absolute; width: 14px; height: 14px; margin: -7px 0 0 -7px; padding: 0;
    border-radius: 50%; border: 2px solid var(--tema-papel); background: var(--tema-tinta);
    box-shadow: var(--tema-sombra-1); cursor: pointer; pointer-events: auto;
  }
  /* Alvo de toque de 44px em volta do ponto de 14px. */
  .marcador::before { content: ""; position: absolute; inset: -15px; border-radius: 50%; }
  .rotulo {
    position: absolute; left: 50%; bottom: calc(100% + 6px); transform: translateX(-50%);
    max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    padding: 3px 7px; border-radius: var(--raio-1);
    background: color-mix(in srgb, var(--tema-papel) 92%, transparent); color: var(--tema-tinta);
    border: 1px solid var(--tema-filete); font-size: 12px; font-weight: 500; line-height: 1.2;
  }
  .rotulo { transition: opacity var(--dur-rapida) var(--ease-saida); }
  /* Sem espaço para o rótulo: só o ponto; passar o mouse ou focar mostra o nome. */
  .rotulo.oculto { opacity: 0; }
  .marcador:hover .rotulo.oculto, .marcador:focus-visible .rotulo.oculto { opacity: 1; z-index: 2; }
  .marcador.ativo { background: var(--tema-acento); transform: scale(1.25); }
  .marcador.ativo .rotulo { background: var(--tema-tinta); color: var(--tema-papel); border-color: var(--tema-tinta); max-width: 220px; z-index: 1; }
  .marcador:focus-visible, .distante:focus-visible { outline: 2px solid var(--tema-acento); outline-offset: 2px; }

  .distante {
    position: absolute; transform: translate(-50%, -50%); box-sizing: border-box;
    display: flex; align-items: center; gap: 8px; padding: 0 12px 0 8px;
    background: var(--tema-papel); color: var(--tema-tinta); text-align: left;
    border: 1px solid var(--tema-filete); border-radius: var(--raio-2); box-shadow: var(--tema-sombra-1);
    font: inherit; cursor: pointer; pointer-events: auto;
    /* Quando uma pílula entra ou sai do grupo, as vizinhas deslizam até o lugar novo. */
    transition: left var(--dur-rapida) var(--ease-saida), top var(--dur-rapida) var(--ease-saida);
  }
  @media (prefers-reduced-motion: reduce) { .distante { transition: none; } }
  .distante.ativo { border-color: var(--tema-acento); box-shadow: 0 0 0 1px var(--tema-acento), var(--tema-sombra-1); }
  .compacto {
    width: 44px; height: 44px; padding: 0; justify-content: center; border-radius: 50%;
    background: var(--tema-tinta); color: var(--tema-papel); border-color: var(--tema-papel);
  }
  .compacto.ativo { background: var(--tema-acento); }
  /* Chocou com um mais perto: some devagar e não recebe toque. */
  .compacto { transition: opacity 240ms var(--ease-saida); }
  .compacto.escondido { pointer-events: none; }
  /* A ponta gira em volta do círculo e aponta o rumo do ponto. */
  .ponta { position: absolute; inset: 0; pointer-events: none; }
  .ponta::after {
    content: ""; position: absolute; top: 50%; left: 100%; margin: -6px 0 0 -2px;
    border: 6px solid transparent; border-left: 8px solid var(--tema-tinta);
  }
  .compacto.ativo .ponta::after { border-left-color: var(--tema-acento); }
  .seta {
    flex: none; display: grid; place-items: center; width: 28px; height: 28px; border-radius: 50%;
    background: var(--tema-tinta); color: var(--tema-papel);
  }
  .texto { min-width: 0; display: flex; flex-direction: column; line-height: 1.2; }
  .nome { font-size: 13px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .tempo { display: inline-flex; align-items: center; gap: 3px; font-size: 12px; color: var(--tema-tinta-2); white-space: nowrap; }
  .tempo :global(svg) { color: var(--tema-tinta-3); }
  .leitor { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
</style>
