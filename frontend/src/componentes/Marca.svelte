<script lang="ts">
  /** Com `aoClicar`, a marca vira botão: no modo cinema é a saída por toque. */
  let { escuro, aoClicar }: { escuro: boolean; aoClicar?: () => void } = $props();
</script>

{#snippet logo()}
  <img src={escuro ? 'marca/produto-horizontal-negativo.svg' : 'marca/produto-horizontal-positivo.svg'} alt="Cidade das Américas — Residencial Cumbuco" />
{/snippet}

{#if aoClicar}
  <button class="marca" aria-label="Sair do modo cinema" onclick={aoClicar}>{@render logo()}</button>
{:else}
  <div class="marca">{@render logo()}</div>
{/if}

<style>
  .marca {
    position: absolute; top: 12px; left: 16px;
    display: flex; align-items: center;
    height: 58px; padding: 0 14px;
    background: var(--tema-papel);
    border: 1px solid var(--tema-filete);
    border-radius: var(--raio-2);
    box-shadow: var(--tema-sombra-1);
  }
  button.marca { cursor: pointer; font: inherit; }
  button.marca:focus-visible { outline: 2px solid var(--tema-acento); outline-offset: 2px; }
  img { display: block; height: 38px; width: auto; }
  @container maquete (min-width: 900px) {
    .marca { top: 16px; height: 62px; }
    img { height: 42px; }
  }
</style>
