<script lang="ts">
  // A agulha aponta o norte na tela: gira ao contrário do rumo da câmera.
  let { graus, aoClicar }: { graus: number; aoClicar: () => void } = $props();
</script>

<button class="bussola" aria-label="Norte; voltar à vista inicial" onclick={aoClicar}>
  <svg width="30" height="30" viewBox="0 0 30 30" aria-hidden="true" focusable="false" style:transform="rotate({-graus}deg)">
    <path d="M15 3l4 12h-8z" fill="var(--tema-acento)" />
    <path d="M15 27l4-12h-8z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" />
    <text x="15" y="12.6" text-anchor="middle" font-size="6.5" font-weight="600" fill="var(--tema-acento-contraste)">N</text>
  </svg>
</button>

<style>
  .bussola {
    width: var(--toque); height: var(--toque); border-radius: 50%;
    display: grid; place-items: center; padding: 0; cursor: pointer;
    background: var(--tema-papel); color: var(--tema-tinta);
    border: 1px solid var(--tema-filete); box-shadow: var(--tema-sombra-1);
  }
  .bussola:hover { background: var(--tema-papel-2); }
  .bussola:focus-visible { outline: 2px solid var(--tema-acento); outline-offset: 2px; }
  svg { transition: transform var(--dur-rapida) linear; }
</style>
