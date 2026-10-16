<script lang="ts">
  import Icone from './Icone.svelte';

  let { escuro }: { escuro: boolean } = $props();
</script>

<img class="logo" src={escuro ? 'marca/produto-vertical-negativo.svg' : 'marca/produto-vertical-positivo.svg'} alt="" />
<h2>Como explorar</h2>
<ul class="gestos">
  <li><Icone gesto="girar" tamanho={44} /><span>Arraste para girar<small>Com um dedo, em qualquer ponto da cena.</small></span></li>
  <li><Icone gesto="pincar" tamanho={44} /><span>Pince para aproximar<small>Afaste os dedos para chegar perto das quadras.</small></span></li>
  <li><Icone gesto="tocar" tamanho={44} /><span>Toque num lote — a ficha abre aqui embaixo<small>Com a área, as medidas e o contorno.</small></span></li>
</ul>

<style>
  .logo { display: block; width: 120px; height: auto; margin: 4px auto 10px; }
  h2 { font-size: 22px; font-weight: 600; letter-spacing: -.01em; margin: 4px 0 12px; }
  .gestos { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
  li { display: grid; grid-template-columns: 44px 1fr; gap: 12px; align-items: center; font-size: 15px; font-weight: 500; }
  li :global(svg) { color: var(--tema-acento); }
  small { display: block; font-weight: 400; font-size: 13px; color: var(--tema-tinta-2); }
</style>
