<script lang="ts">
  import type { Marco } from '../lib/dados';
  import { midia } from '../lib/midia';
  import Icone from './Icone.svelte';
  import type { ImagemAmpliada } from '../lib/historico';

  let { marco, aoFechar, aoAmpliar }: { marco: Marco; aoFechar: () => void; aoAmpliar: (imagem: ImagemAmpliada) => void } = $props();
  const maps = $derived(`https://www.google.com/maps/search/?api=1&query=${marco.lat},${marco.lon}`);
</script>

<div class="barra"><span></span><button class="fechar" aria-label="Fechar galeria" onclick={aoFechar}><Icone nome="fechar" tamanho={18} /></button></div>
<h2 class="titulo">{marco.nome}</h2>
{#if marco.id === 'estande'}
  <a class="btn" href={maps} target="_blank" rel="noopener noreferrer">Como chegar<Icone nome="externo" tamanho={18} /></a>
{/if}
<ul class="fotos">
  {#each marco.galeria as f, i (f.foto)}
    <li><button class="miniatura" aria-label="Ampliar foto {i + 1} de {marco.galeria.length}" onclick={() => aoAmpliar({ src: midia(f.foto, 'cheia'), alt: f.legenda || `${marco.nome}, foto ${i + 1}` })}>
      <img src={midia(f.foto, 'mini')} alt={f.legenda || `${marco.nome}, foto ${i + 1}`} loading="lazy" /></button></li>
  {/each}
</ul>
{#if marco.planta}
  <button class="miniatura planta" aria-label="Ampliar a planta humanizada" onclick={() => aoAmpliar({ src: midia(marco.planta!, 'cheia'), alt: `Planta humanizada do ${marco.nome.toLowerCase()}` })}>
    <img src={midia(marco.planta, 'mini')} alt="Planta humanizada do {marco.nome.toLowerCase()}" loading="lazy" /></button>
{/if}

<style>
  .barra { display: flex; align-items: center; justify-content: space-between; height: var(--toque); margin: 0 -12px 2px; }
  .fechar { display: inline-flex; align-items: center; justify-content: center; width: var(--toque); height: var(--toque); padding: 0; border: 0; background: none; border-radius: var(--raio-1); color: var(--tema-tinta-2); cursor: pointer; }
  .fechar:hover { background: var(--tema-papel-2); color: var(--tema-tinta); }
  .fechar:focus-visible { outline: 2px solid var(--tema-acento); outline-offset: 2px; }
  .titulo { font-family: var(--tema-fonte-display); font-weight: 600; font-size: 30px; line-height: 1.05; margin: 0 0 14px; }
  .btn {
    display: flex; align-items: center; justify-content: center; gap: 8px; width: 100%;
    height: 48px; margin: 0 0 14px; padding: 0 18px; border-radius: var(--raio-2);
    background: var(--tema-acento); color: var(--tema-acento-contraste);
    font-size: 15.5px; font-weight: 600; text-decoration: none;
  }
  .btn:hover { background: var(--tema-acento-hover); }
  .btn:focus-visible { outline: 2px solid var(--tema-acento); outline-offset: 2px; }
  .fotos { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .miniatura { display: block; width: 100%; padding: 0; border: 0; background: var(--tema-papel-2); border-radius: var(--raio-1); overflow: hidden; cursor: zoom-in; aspect-ratio: 4 / 3; }
  .miniatura img { display: block; width: 100%; height: 100%; object-fit: cover; }
  .miniatura:focus-visible { outline: 2px solid var(--tema-acento); outline-offset: 2px; }
  .planta { margin-top: 8px; aspect-ratio: auto; background: #FFFFFF; }
  .planta img { height: auto; object-fit: contain; }
  @container maquete (min-width: 900px) {
    .fotos { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  }
</style>
