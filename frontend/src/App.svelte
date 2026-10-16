<script lang="ts">
  import { onMount } from 'svelte';
  import { carregarDados, type Dados } from './lib/dados';
  import { criarCena, type Cena } from './lib/cena/cena';

  type Fase = 'carregando' | 'pronto' | 'erro';
  let fase = $state<Fase>('carregando');
  let palco: HTMLDivElement;
  let dados: Dados | null = null;
  let cena: Cena | null = null;

  onMount(() => {
    (async () => {
      try {
        const base = new URL('./', location.href);
        dados = await carregarDados(base);
        cena = await criarCena({ base, dados, aoEscolher: () => {}, aoPassar: () => {}, aoMoverEtiqueta: () => {}, aoGirar: () => {} });
        cena.montar(palco);
        fase = 'pronto';
      } catch (e) {
        console.error(e);
        fase = 'erro';
      }
    })();
    return () => cena?.descartar();
  });
</script>

<div class="maquete" data-tema="americas" data-cor="claro">
  <div class="cena" bind:this={palco}></div>
  {#if fase === 'carregando'}
    <p class="carregando" role="status">Carregando a maquete…</p>
  {:else if fase === 'erro'}
    <p class="carregando" role="alert">Não foi possível abrir a maquete</p>
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
  .carregando {
    position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); margin: 0;
    padding: 10px 16px; border-radius: var(--raio-2); background: var(--tema-papel); color: var(--tema-tinta-2);
    border: 1px solid var(--tema-filete); font-size: 14px;
  }
</style>
