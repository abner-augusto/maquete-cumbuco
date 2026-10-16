<script lang="ts" module>
  export type Batente = 'some' | 'espiar' | 'cheia';
</script>

<script lang="ts">
  import type { Snippet } from 'svelte';

  let {
    batente = $bindable(),
    rotulo,
    espiar = 320,
    corpo,
    rodape,
  }: { batente: Batente; rotulo: string; espiar?: number; corpo: Snippet; rodape?: Snippet } = $props();

  let folha: HTMLElement | undefined = $state();
  let arrasto = $state(0);
  let inicio: { y: number; id: number; moveu: boolean } | null = null;

  // Arrasto de verdade na borda superior: a folha acompanha o dedo e encaixa no batente mais próximo.
  function baixar(e: PointerEvent) {
    inicio = { y: e.clientY, id: e.pointerId, moveu: false };
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  }
  function mover(e: PointerEvent) {
    if (!inicio || e.pointerId !== inicio.id) return;
    arrasto = e.clientY - inicio.y;
    if (Math.abs(arrasto) > 6) inicio.moveu = true;
  }
  function soltar(e: PointerEvent) {
    if (!inicio || e.pointerId !== inicio.id || !folha) return;
    const moveu = inicio.moveu;
    inicio = null;
    if (!moveu) {
      arrasto = 0;
      batente = batente === 'cheia' ? 'espiar' : 'cheia';
      return;
    }
    const altura = folha.offsetHeight;
    const cheia = (folha.parentElement?.clientHeight ?? 800) - 80;
    const alvos: [Batente, number][] = [['some', 0], ['espiar', espiar], ['cheia', cheia]];
    alvos.sort((a, b) => Math.abs(a[1] - altura) - Math.abs(b[1] - altura));
    arrasto = 0;
    batente = alvos[0]![0];
  }
</script>

{#if batente !== 'some'}
  <section
    class="folha"
    class:arrastando={arrasto !== 0}
    bind:this={folha}
    aria-label={rotulo}
    style:--arrasto="{batente === 'cheia' ? Math.max(arrasto, 0) : arrasto}px">
    <div
      class="alca"
      role="button"
      tabindex="0"
      aria-label={batente === 'cheia' ? 'Recolher a folha' : 'Expandir a folha'}
      onpointerdown={baixar}
      onpointermove={mover}
      onpointerup={soltar}
      onpointercancel={() => ((inicio = null), (arrasto = 0))}
      onkeydown={e => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          batente = batente === 'cheia' ? 'espiar' : 'cheia';
        }
      }}></div>
    <div class="corpo">{@render corpo()}</div>
    {#if rodape}<div class="rodape">{@render rodape()}</div>{/if}
  </section>
{/if}

<style>
  .folha {
    position: absolute; left: 0; right: 0; bottom: 0;
    /* A altura anima (e não um transform) para o rodapé ficar visível em todos os batentes. */
    height: max(0px, calc(var(--folha-h) - var(--arrasto, 0px)));
    background: var(--tema-papel);
    color: var(--tema-tinta);
    border-radius: var(--raio-3) var(--raio-3) 0 0;
    box-shadow: var(--tema-sombra-2);
    display: flex; flex-direction: column;
    overflow: hidden;
    transition: height var(--dur-folha) var(--ease-saida);
    touch-action: none;
  }
  .folha.arrastando { transition: none; }
  .alca { flex: none; height: 26px; display: grid; place-items: center; cursor: grab; touch-action: none; }
  .alca::before { content: ""; width: 40px; height: 4px; border-radius: 2px; background: var(--tema-filete-forte); }
  .alca:focus-visible { outline: 2px solid var(--tema-acento); outline-offset: -4px; border-radius: var(--raio-2); }
  .corpo { flex: 1; overflow-y: auto; overscroll-behavior: contain; padding: 0 20px 16px; min-height: 0; touch-action: pan-y; }
  .rodape { flex: none; padding: 12px 20px calc(12px + env(safe-area-inset-bottom)); border-top: 1px solid var(--tema-filete); background: var(--tema-papel); }

  @container maquete (min-width: 900px) {
    .folha { left: 16px; right: auto; bottom: 16px; width: 384px; max-height: calc(100cqh - 112px); border-radius: var(--raio-3); box-shadow: var(--tema-sombra-3); }
  }
</style>
