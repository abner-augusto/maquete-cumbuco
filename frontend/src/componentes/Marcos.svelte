<script lang="ts">
  import type { Tela } from '../lib/cena/cena';
  import type { Marco } from '../lib/dados';
  import Icone from './Icone.svelte';

  // Um botão por marco, sempre na tela: fora do quadro, fica preso à borda a 12 px.
  let { marcos, telas, aoEscolher }: { marcos: Marco[]; telas: { id: string; tela: Tela | null }[]; aoEscolher: (id: string) => void } = $props();

  const MARGEM = 12;
  let largura = $state(0);
  let altura = $state(0);
  const porId = $derived(new Map(marcos.map(m => [m.id, m])));

  /** Posição presa ao retângulo da camada; a âncora do botão vira para dentro quando encosta na borda. */
  function lugar(t: Tela) {
    const x = Math.min(Math.max(t.x, MARGEM), largura - MARGEM);
    const y = Math.min(Math.max(t.y, MARGEM), altura - MARGEM);
    const ax = x <= MARGEM ? '0%' : x >= largura - MARGEM ? '-100%' : '-50%';
    const ay = y <= MARGEM ? '0%' : y >= altura - MARGEM ? '-100%' : '-50%';
    return { x, y, transform: `translate(${ax}, ${ay})` };
  }
</script>

<div class="marcos" bind:clientWidth={largura} bind:clientHeight={altura}>
  {#if largura && altura}
    {#each telas as { id, tela } (id)}
      {@const m = porId.get(id)}
      {#if m && tela}
        {@const p = lugar(tela)}
        <button class="marco" style:left="{p.x}px" style:top="{p.y}px" style:transform={p.transform} aria-label="{m.nome}: abrir galeria" onclick={() => aoEscolher(id)}>
          <Icone nome={m.objeto ? 'camera' : 'mapa'} tamanho={18} />{m.nome}
        </button>
      {/if}
    {/each}
  {/if}
</div>

<style>
  .marcos { position: absolute; inset: 0; pointer-events: none; overflow: hidden; }
  .marco {
    position: absolute; pointer-events: auto;
    display: inline-flex; align-items: center; gap: 6px;
    height: var(--toque); padding: 0 14px 0 11px; border-radius: 22px;
    background: var(--tema-papel); color: var(--tema-tinta);
    border: 1px solid var(--tema-filete); box-shadow: var(--tema-sombra-1);
    font-size: 13.5px; font-weight: 600; white-space: nowrap; cursor: pointer;
  }
  .marco :global(svg) { color: var(--tema-acento); }
  .marco:hover { background: var(--tema-papel-2); }
  .marco:focus-visible { outline: 2px solid var(--tema-acento); outline-offset: 2px; }
</style>
