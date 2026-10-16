<script lang="ts">
  import Icone from './Icone.svelte';

  let { src, alt, aoFechar }: { src: string; alt: string; aoFechar: () => void } = $props();

  let fechar: HTMLButtonElement | undefined = $state();
  $effect(() => {
    const anterior = document.activeElement as HTMLElement | null;
    fechar?.focus();
    const tecla = (e: KeyboardEvent) => e.key === 'Escape' && aoFechar();
    addEventListener('keydown', tecla);
    return () => {
      removeEventListener('keydown', tecla);
      anterior?.focus();
    };
  });
</script>

<!-- Fecha ao tocar fora do desenho; tocar na planta não fecha. -->
<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div class="fundo" onclick={e => e.target === e.currentTarget && aoFechar()}>
  <div class="caixa" role="dialog" aria-modal="true" aria-label={alt}>
    <img {src} {alt} />
  </div>
  <button class="fechar" bind:this={fechar} aria-label="Fechar planta" onclick={aoFechar}><Icone nome="fechar" /></button>
</div>

<style>
  .fundo {
    position: fixed; inset: 0; z-index: 20;
    display: grid; place-items: center;
    padding: 56px 16px 24px;
    background: color-mix(in srgb, var(--tema-tinta) 72%, transparent);
    animation: entra var(--dur-base) var(--ease-saida);
  }
  .caixa {
    max-width: min(1400px, 100%); max-height: 100%;
    padding: 14px; border-radius: var(--raio-2);
    background: #FFFFFF;
    box-shadow: var(--tema-sombra-3);
    display: grid;
  }
  /* A arte tem fundo branco próprio: a moldura fica branca nos dois modos. */
  img { display: block; max-width: 100%; max-height: calc(100dvh - 108px); object-fit: contain; }
  .fechar {
    position: absolute; top: 12px; right: 16px;
    width: var(--toque); height: var(--toque); display: grid; place-items: center;
    border: 1px solid var(--tema-filete); border-radius: var(--raio-2);
    background: var(--tema-papel); color: var(--tema-tinta); cursor: pointer;
  }
  .fechar:focus-visible { outline: 2px solid var(--tema-acento); outline-offset: 2px; }
  @keyframes entra { from { opacity: 0; } }
</style>
