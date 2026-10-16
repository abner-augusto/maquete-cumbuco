<script lang="ts">
  import { ROTULO_CATEGORIA, rotuloKm, type Ponto } from '../lib/pontos';
  import Icone from './Icone.svelte';
  import IconePonto, { iconeDaCategoria } from './IconePonto.svelte';

  let {
    pontos,
    fontes,
    selecionado,
    aoEscolher,
  }: { pontos: Ponto[]; fontes: string; selecionado: number | null; aoEscolher: (id: number) => void } = $props();

  let lista: HTMLElement | undefined = $state();
  // O ponto tocado na cena aparece na lista, sem a folha pular para o topo.
  $effect(() => {
    if (selecionado === null || !lista) return;
    lista.querySelector(`[data-ponto="${selecionado}"]`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  });
</script>

<h2 class="titulo">Pontos de referência</h2>
<p class="apoio">Distância em linha reta a partir do Residencial Cumbuco. Tempos de carro estimados pelo mapa viário.</p>

<ol class="pontos" bind:this={lista}>
  {#each pontos as ponto (ponto.id)}
    <li data-ponto={ponto.id} class:ativo={ponto.id === selecionado}>
      <button class="ponto" aria-pressed={ponto.id === selecionado} onclick={() => aoEscolher(ponto.id)}>
        <span class="icone"><IconePonto nome={iconeDaCategoria(ponto.categoria)} /></span>
        <span class="texto">
          <span class="nome">{ponto.nome}</span>
          <span class="tipo">{ROTULO_CATEGORIA[ponto.categoria] ?? ponto.categoria}</span>
          <span class="tempo"><IconePonto nome="carro" tamanho={15} />{ponto.minutos_carro} min<span class="leitor"> de carro</span></span>
        </span>
        <span class="distancia">{rotuloKm(ponto.km)}</span>
      </button>
      <a class="maps" href={ponto.maps} target="_blank" rel="noopener noreferrer" aria-label="Abrir {ponto.nome} no Google Maps"><Icone nome="externo" tamanho={18} /></a>
    </li>
  {/each}
</ol>

<p class="atribuicao">
  {fontes}{fontes ? '. ' : ''}Mapa: © OpenStreetMap contributors (ODbL), Overture Maps Foundation, Copernicus GLO-30. Ícones: Phosphor Icons (MIT).
</p>

<style>
  .titulo { margin: 0; font-family: var(--tema-fonte-display); font-size: 22px; font-weight: 600; line-height: 1.15; }
  .apoio { margin: 4px 0 8px; font-size: 13px; color: var(--tema-tinta-2); }
  .pontos { list-style: none; margin: 0 -20px; padding: 0; }
  li { display: grid; grid-template-columns: 1fr auto; align-items: center; }
  li + li { border-top: 1px solid var(--tema-filete); }
  li.ativo { background: var(--tema-papel-2); }
  .ponto { display: grid; grid-template-columns: 36px 1fr auto; align-items: center; gap: 12px; padding: 11px 0 11px 20px; border: 0; background: none; text-align: left; cursor: pointer; color: var(--tema-tinta); font: inherit; }
  .ponto:focus-visible, .maps:focus-visible { outline: 2px solid var(--tema-acento); outline-offset: -2px; }
  .icone { display: grid; place-items: center; width: 36px; height: 36px; border-radius: 50%; background: var(--tema-papel-2); color: var(--tema-tinta); }
  li.ativo .icone { background: var(--tema-acento); color: var(--tema-acento-contraste); }
  .texto { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .nome { font-size: 15px; font-weight: 500; line-height: 1.25; }
  .tipo { font-size: 13px; color: var(--tema-tinta-2); }
  .tempo { display: inline-flex; align-items: center; gap: 4px; font-size: 13px; color: var(--tema-tinta-2); white-space: nowrap; }
  .tempo :global(svg) { color: var(--tema-tinta-3); }
  .leitor { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
  .distancia { font-family: var(--tema-fonte-display); font-weight: 600; font-size: 16px; line-height: 1; white-space: nowrap; }
  .maps { display: grid; place-items: center; width: var(--toque); height: var(--toque); margin-right: 8px; color: var(--tema-tinta-2); border-radius: var(--raio-1); }
  .maps:hover { color: var(--tema-tinta); background: var(--tema-papel-2); }
  .atribuicao { margin: 12px 0 0; font-size: 11px; line-height: 1.35; color: var(--tema-tinta-3); }
</style>
