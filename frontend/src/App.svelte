<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { criarCena, type Cena, type QuadroEntorno, type Tela } from './lib/cena/cena';
  import { carregarDados, type Dados, type Lote } from './lib/dados';
  import { modoCor, primeiraVisita, vegetacao } from './lib/dispositivo';
  import { prepararPontos } from './lib/pontos';
  import { buscar, loteDaUrl, precosVisiveis, rotuloCurto } from './lib/lotes';
  import { trocarCorComTransicao } from './lib/transicao-cor';
  import BoasVindas from './componentes/BoasVindas.svelte';
  import Busca from './componentes/Busca.svelte';
  import Controles from './componentes/Controles.svelte';
  import Ficha from './componentes/Ficha.svelte';
  import FichaPonto from './componentes/FichaPonto.svelte';
  import Folha, { type Batente } from './componentes/Folha.svelte';
  import Legenda from './componentes/Legenda.svelte';
  import ListaEntorno from './componentes/ListaEntorno.svelte';
  import Galeria from './componentes/Galeria.svelte';
  import Marca from './componentes/Marca.svelte';
  import Marcos from './componentes/Marcos.svelte';
  import PontosEntorno from './componentes/PontosEntorno.svelte';

  type Fase = 'carregando' | 'pronto' | 'erro';
  type Conteudo = 'busca' | 'ficha' | 'boas-vindas' | 'marco' | 'entorno' | 'ponto';

  let fase = $state<Fase>('carregando');
  let cena = $state<Cena | null>(null);
  let dados = $state<Dados | null>(null);
  let palco: HTMLElement | undefined = $state();

  const escuroMedia = matchMedia('(prefers-color-scheme: dark)');
  let corSistema = $state<'claro' | 'escuro'>(escuroMedia.matches ? 'escuro' : 'claro');
  let corEscolhida = $state(modoCor.ler());
  const cor = $derived(corEscolhida ?? corSistema);

  let batente = $state<Batente>('some');
  let conteudo = $state<Conteudo>('busca');
  let consulta = $state('');
  let selecionado = $state<string | null>(null);
  let etiqueta = $state<Tela | null>(null);
  let hover = $state<{ id: string; tela: Tela } | null>(null);
  let rumo = $state(0);
  let precos = $state(false);
  let marcoAberto = $state<string | null>(null);
  let telasMarcos = $state<{ id: string; tela: Tela | null }[]>([]);
  // Modo entorno: carrega no primeiro toque e fica guardado para as próximas vezes.
  let modoEntorno = $state(false);
  let carregandoEntorno = $state(false);
  let erroEntorno = $state(false);
  let quadroEntorno = $state<QuadroEntorno | null>(null);
  let pontoSelecionado = $state<number | null>(null);

  // ---- dados derivados ----
  const porId = $derived(new Map((dados?.lotes ?? []).map(l => [l.id, l])));
  const loteAberto = $derived(selecionado ? porId.get(selecionado) ?? null : null);
  const loteHover = $derived(hover ? porId.get(hover.id) ?? null : null);
  const marco = $derived(marcoAberto ? dados?.marcos.find(m => m.id === marcoAberto) ?? null : null);
  const pontos = $derived(dados ? prepararPontos(dados.pontos) : []);
  const pontoAberto = $derived(pontoSelecionado !== null ? pontos.find(p => p.id === pontoSelecionado) ?? null : null);
  const resultados = $derived(dados ? buscar(dados.lotes, consulta) : []);
  const temStatus = $derived((dados?.lotes ?? []).some(l => l.status));
  const espiarPx = $derived(conteudo === 'boas-vindas' ? 404 : 320);
  const folhaH = $derived(batente === 'some' ? '0px' : batente === 'espiar' ? `${espiarPx}px` : 'calc(100cqh - 80px)');
  const rotuloFolha = $derived(
    conteudo === 'ficha' && loteAberto
      ? `Ficha do lote ${rotuloCurto(loteAberto)}`
      : conteudo === 'marco' && marco
        ? `Galeria: ${marco.nome}`
        : conteudo === 'ponto' && pontoAberto
        ? `Ponto: ${pontoAberto.nome}`
        : conteudo === 'entorno'
        ? 'Pontos de referência'
        : conteudo === 'boas-vindas'
        ? 'Como explorar'
        : 'Busca de lote',
  );

  // ---- carregamento ----
  onMount(async () => {
    escuroMedia.addEventListener('change', () => (corSistema = escuroMedia.matches ? 'escuro' : 'claro'));
    try {
      const base = new URL('./', location.href);
      const d = await carregarDados(base);
      dados = d;
      precos = precosVisiveis(d.config, location.search);
      cena = await criarCena({
        base,
        dados: d,
        aoEscolher: id => (id ? abrirFicha(id, true) : fecharFicha()),
        aoPassar: r => (hover = r),
        aoMoverEtiqueta: t => (etiqueta = t),
        aoGirar: g => (rumo = g),
        aoMoverMarcos: t => (telasMarcos = t),
        aoMoverEntorno: q => (quadroEntorno = q),
        vegetacao: vegetacao.ler(),
      });
    } catch (e) {
      console.error(e);
      return void (fase = 'erro');
    }
    fase = 'pronto';
    const inicial = loteDaUrl(dados.lotes, location.search);
    if (inicial) abrirFicha(inicial.id, true);
    else {
      // Id da URL que não existe: some da barra, a cena abre na vista inicial.
      if (new URLSearchParams(location.search).has('lote')) atualizarUrl(null);
      if (primeiraVisita.pendente()) {
        conteudo = 'boas-vindas';
        batente = 'espiar';
      }
    }
  });

  onDestroy(() => cena?.descartar());

  // ---- cena acompanha o estado ----
  $effect(() => {
    if (cena && palco) cena.montar(palco);
  });
  $effect(() => {
    cena?.ceu(cor);
  });
  $effect(() => {
    cena?.selecionar(selecionado);
  });

  // ---- ações ----
  /** `?lote=` reflete a ficha aberta; `precos=0`, se veio na URL, fica. */
  function atualizarUrl(id: string | null) {
    const p = new URLSearchParams();
    if (id) p.set('lote', id);
    if (new URLSearchParams(location.search).get('precos') === '0') p.set('precos', '0');
    const busca = p.toString();
    history.replaceState(null, '', busca ? `?${busca}` : location.pathname);
  }

  function abrirFicha(id: string, enquadrar: boolean) {
    if (!porId.has(id)) return;
    if (conteudo === 'boas-vindas') primeiraVisita.concluir();
    selecionado = id;
    conteudo = 'ficha';
    // No tablet/desktop a folha fica ao lado da cena e não cobre o lote: abre cheia.
    batente = (palco?.clientWidth ?? 0) >= 900 ? 'cheia' : 'espiar';
    if (enquadrar) cena?.enquadrar(id);
    atualizarUrl(id);
  }

  function fecharFicha() {
    if (conteudo !== 'ficha') return;
    selecionado = null;
    // No modo entorno, fechar a ficha devolve a lista dos pontos.
    conteudo = modoEntorno ? 'entorno' : 'busca';
    batente = modoEntorno ? 'espiar' : 'some';
    atualizarUrl(null);
  }

  async function alternarEntorno() {
    if (!cena) return;
    erroEntorno = false;
    if (modoEntorno || carregandoEntorno) {
      modoEntorno = carregandoEntorno = false;
      pontoSelecionado = null;
      quadroEntorno = null;
      if (conteudo === 'entorno' || conteudo === 'ponto') {
        conteudo = 'busca';
        batente = 'some';
      }
      await cena.entorno(false, []);
      return;
    }
    carregandoEntorno = true;
    try {
      await cena.entorno(true, pontos);
    } catch (e) {
      console.error(e);
      if (carregandoEntorno) erroEntorno = true;
      carregandoEntorno = false;
      return;
    }
    // Desligado durante o carregamento.
    if (!carregandoEntorno) return;
    carregandoEntorno = false;
    modoEntorno = true;
    if (conteudo === 'boas-vindas') primeiraVisita.concluir();
    if (conteudo === 'ficha') fecharFicha();
    conteudo = 'entorno';
    batente = 'espiar';
  }

  function escolherPonto(id: number) {
    pontoSelecionado = id;
    conteudo = 'ponto';
    if (batente === 'some') batente = 'espiar';
  }

  function voltarALista() {
    pontoSelecionado = null;
    conteudo = 'entorno';
  }

  function abrirMarco(id: string) {
    if (conteudo === 'boas-vindas') primeiraVisita.concluir();
    if (conteudo === 'ficha') fecharFicha();
    marcoAberto = id;
    conteudo = 'marco';
    batente = (palco?.clientWidth ?? 0) >= 900 ? 'cheia' : 'espiar';
    cena?.enquadrarMarco(id);
  }

  function fecharMarco() {
    marcoAberto = null;
    conteudo = modoEntorno ? 'entorno' : 'busca';
    batente = modoEntorno ? 'espiar' : 'some';
  }

  function concluirBoasVindas() {
    primeiraVisita.concluir();
    if (conteudo === 'boas-vindas') {
      conteudo = 'busca';
      batente = 'some';
    }
  }

  function alternarBusca() {
    if (batente !== 'some' && conteudo === 'busca') {
      batente = 'some';
      return;
    }
    if (conteudo === 'ficha') fecharFicha();
    conteudo = 'busca';
    batente = 'espiar';
  }

  function ajuda() {
    if (conteudo === 'ficha') fecharFicha();
    conteudo = 'boas-vindas';
    batente = 'espiar';
  }

  // Quem mexe na cena durante a primeira visita já entendeu o gesto.
  function tocouCena() {
    if (conteudo === 'boas-vindas' && primeiraVisita.pendente()) concluirBoasVindas();
  }
</script>

<div class="maquete" data-tema="americas" data-cor={cor} style:--folha-h={folhaH}>
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="cena" bind:this={palco} onpointerdown={tocouCena}></div>

  {#if fase === 'carregando'}
    <p class="carregando" role="status">Carregando a maquete…</p>
  {:else if fase === 'erro'}
    <p class="carregando" role="alert">Não foi possível abrir a maquete. Recarregue a página.</p>
  {:else if dados && cena}
    <!-- Antes do chrome no DOM: os ícones ficam atrás da marca, dos controles e da folha. -->
    {#if modoEntorno && quadroEntorno}
      <PontosEntorno {pontos} quadro={quadroEntorno} selecionado={pontoSelecionado} aoEscolher={escolherPonto} />
    {/if}
    <Marcos marcos={dados.marcos} telas={telasMarcos} aoEscolher={abrirMarco} />
    {#if carregandoEntorno}
      <p class="carregando" role="status">Carregando o entorno…</p>
    {:else if erroEntorno}
      <p class="carregando" role="status">Não foi possível carregar o entorno. Tente de novo.</p>
    {/if}
    <Marca escuro={cor === 'escuro'} />

    <Controles
      {rumo}
      buscaAtiva={batente !== 'some' && conteudo === 'busca'}
      entorno={{ ativo: modoEntorno, carregando: carregandoEntorno }}
      escuro={cor === 'escuro'}
      aoBuscar={alternarBusca}
      aoEnquadrar={() => cena?.inicio()}
      aoEntorno={alternarEntorno}
      aoAproximar={() => cena?.aproximar(0.7)}
      aoAfastar={() => cena?.aproximar(1.4)}
      aoAjuda={ajuda}
      aoAlternarCor={origem => {
        const nova = cor === 'escuro' ? 'claro' : 'escuro';
        modoCor.gravar(nova);
        trocarCorComTransicao(() => (corEscolhida = nova), origem);
      }} />

    {#if etiqueta && loteAberto}
      <div class="etiqueta" style:left="{etiqueta.x}px" style:top="{etiqueta.y}px" aria-hidden="true">{rotuloCurto(loteAberto)}</div>
    {/if}
    {#if hover && loteHover && hover.id !== selecionado}
      <div class="etiqueta leve" style:left="{hover.tela.x}px" style:top="{hover.tela.y}px" aria-hidden="true">{rotuloCurto(loteHover)}</div>
    {/if}

    <Legenda cores={cena.cores()} status={temStatus} />

    <Folha bind:batente espiar={espiarPx} rotulo={rotuloFolha}>
      {#snippet corpo()}
        {#if conteudo === 'ficha' && loteAberto}
          <Ficha lote={loteAberto as Lote} config={dados!.config} {precos} aoFechar={fecharFicha} />
        {:else if conteudo === 'ponto' && pontoAberto}
          <FichaPonto ponto={pontoAberto} aoVoltar={voltarALista} />
        {:else if conteudo === 'entorno'}
          <ListaEntorno {pontos} fontes={dados!.fontesPontos} selecionado={pontoSelecionado} aoEscolher={escolherPonto} />
        {:else if conteudo === 'marco' && marco}
          <Galeria {marco} aoFechar={fecharMarco} />
        {:else if conteudo === 'boas-vindas'}
          <BoasVindas escuro={cor === 'escuro'} />
        {:else}
          <Busca bind:consulta {resultados} aoEscolher={id => abrirFicha(id, true)} />
        {/if}
      {/snippet}
      {#snippet rodape()}
        {#if conteudo === 'boas-vindas'}
          <button class="btn primario" onclick={concluirBoasVindas}>Começar</button>
        {/if}
      {/snippet}
    </Folha>
  {/if}
</div>

<style>
  .maquete {
    container: maquete / size;
    position: absolute; inset: 0; overflow: hidden;
    background: var(--tema-ceu);
    color: var(--tema-tinta);
    font-family: var(--tema-fonte-texto);
    font-size: 15px; line-height: 1.45;
    font-variant-numeric: tabular-nums;
  }
  .cena { position: absolute; inset: 0; touch-action: none; }
  .cena :global(canvas) { display: block; width: 100%; height: 100%; outline: none; }
  /* Só avisa: o toque passa para a cena embaixo. */
  .carregando {
    position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); margin: 0; pointer-events: none;
    padding: 10px 16px; border-radius: var(--raio-2); background: var(--tema-papel); color: var(--tema-tinta-2);
    border: 1px solid var(--tema-filete); font-size: 14px;
  }
  .etiqueta {
    position: absolute; transform: translate(-50%, calc(-100% - 10px));
    background: var(--tema-tinta); color: var(--tema-papel);
    font-family: var(--tema-fonte-display); font-weight: 600; font-size: 16px; line-height: 1;
    padding: 7px 10px; border-radius: var(--raio-1); pointer-events: none; white-space: nowrap;
  }
  .etiqueta::after { content: ""; position: absolute; left: 50%; bottom: -6px; transform: translateX(-50%); border: 6px solid transparent; border-bottom: 0; border-top-color: var(--tema-tinta); }
  .etiqueta.leve { background: var(--tema-papel); color: var(--tema-tinta); box-shadow: var(--tema-sombra-1); font-size: 14px; }
  .etiqueta.leve::after { border-top-color: var(--tema-papel); }
  .btn {
    display: flex; align-items: center; justify-content: center; gap: 8px; width: 100%;
    height: 48px; padding: 0 18px; border-radius: var(--raio-2); border: 1px solid transparent;
    font-size: 15.5px; font-weight: 600; cursor: pointer; text-decoration: none;
  }
  .primario { background: var(--tema-acento); color: var(--tema-acento-contraste); }
  .primario:hover { background: var(--tema-acento-hover); }
  .btn:focus-visible { outline: 2px solid var(--tema-acento); outline-offset: 2px; }
</style>
