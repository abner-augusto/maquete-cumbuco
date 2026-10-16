<script lang="ts">
  import type { Tela } from '../lib/cena/cena';
  import type { Marco } from '../lib/dados';
  import Icone from './Icone.svelte';

  // Um botão por marco, sempre clicável: fora do quadro, fica preso à borda da camada a 12 px. A camada
  // desvia da marca, dos controles, da legenda e da folha, para o botão preso nunca ficar sob o chrome.
  let { marcos, telas, aoEscolher }: { marcos: Marco[]; telas: { id: string; tela: Tela | null }[]; aoEscolher: (id: string) => void } = $props();

  const MARGEM = 12;
  let largura = $state(0);
  let altura = $state(0);
  let camada: HTMLDivElement | undefined = $state();
  const porId = $derived(new Map(marcos.map(m => [m.id, m])));

  /** Posição presa ao retângulo da camada; a âncora do botão vira para dentro quando encosta na borda. */
  function lugar(t: Tela) {
    // A tela vem no referencial da cena inteira; a camada começa abaixo da marca.
    const x = Math.min(Math.max(t.x - (camada?.offsetLeft ?? 0), MARGEM), largura - MARGEM);
    const y = Math.min(Math.max(t.y - (camada?.offsetTop ?? 0), MARGEM), altura - MARGEM);
    const ax = x <= MARGEM ? '0%' : x >= largura - MARGEM ? '-100%' : '-50%';
    const ay = y <= MARGEM ? '0%' : y >= altura - MARGEM ? '-100%' : '-50%';
    return { x, y, transform: `translate(${ax}, ${ay})` };
  }
</script>

<div class="marcos" bind:this={camada} bind:clientWidth={largura} bind:clientHeight={altura}>
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
  .marcos {
    position: absolute; pointer-events: none; overflow: hidden;
    top: 80px; left: 0; right: 68px; bottom: calc(var(--folha-h) + 104px);
  }
  @container maquete (min-width: 900px) {
    .marcos { top: 88px; bottom: 112px; }
  }
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
