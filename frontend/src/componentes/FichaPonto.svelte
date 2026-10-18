<script lang="ts">
  import { midia } from '../lib/midia';
  import { ROTULO_CATEGORIA, rotuloKm, type Ponto } from '../lib/pontos';
  import Icone from './Icone.svelte';
  import IconePonto from './IconePonto.svelte';
  import type { ImagemAmpliada } from '../lib/historico';

  let { ponto, aoVoltar, aoAmpliar }: { ponto: Ponto; aoVoltar: () => void; aoAmpliar: (imagem: ImagemAmpliada) => void } = $props();
</script>

<div class="barra">
  <button class="voltar" onclick={aoVoltar}><Icone nome="voltar" tamanho={18} />Pontos de referência</button>
</div>
<h2 class="titulo">{ponto.nome}</h2>
<p class="tipo">{ROTULO_CATEGORIA[ponto.categoria] ?? ponto.categoria}</p>
<p class="medidas">
  <span class="km">{rotuloKm(ponto.km)}</span>
  <span class="tempo"><IconePonto nome="carro" tamanho={15} />{ponto.minutos_carro} min de carro</span>
</p>

{#if ponto.foto}
  <figure class="foto">
    <button class="ampliar" aria-label="Ampliar a foto" onclick={() => aoAmpliar({ src: midia(ponto.foto!, 'cheia'), alt: ponto.nome })}>
      <img src={midia(ponto.foto, 'mini')} alt={ponto.nome} loading="lazy" />
    </button>
    {#if ponto.credito}
      <figcaption>
        Foto: {ponto.credito}{#if ponto.licenca} · {#if ponto.licenca_url}<a href={ponto.licenca_url} target="_blank" rel="noopener noreferrer">{ponto.licenca}</a>{:else}{ponto.licenca}{/if}{/if}
      </figcaption>
    {/if}
  </figure>
{/if}

<a class="btn" href={ponto.maps} target="_blank" rel="noopener noreferrer">Abrir no Google Maps<Icone nome="externo" tamanho={18} /></a>

<style>
  .barra { display: flex; align-items: center; height: var(--toque); margin: 0 -8px 2px; }
  .voltar { display: inline-flex; align-items: center; gap: 4px; height: var(--toque); padding: 0 8px; border: 0; background: none; border-radius: var(--raio-1); color: var(--tema-tinta-2); font-size: 14px; font-weight: 500; cursor: pointer; }
  .voltar:hover { background: var(--tema-papel-2); color: var(--tema-tinta); }
  .voltar:focus-visible { outline: 2px solid var(--tema-acento); outline-offset: 2px; }
  .titulo { font-family: var(--tema-fonte-display); font-weight: 600; font-size: 26px; line-height: 1.1; margin: 0; }
  .tipo { margin: 4px 0 0; font-size: 14px; color: var(--tema-tinta-2); }
  .medidas { display: flex; align-items: center; gap: 14px; margin: 10px 0 0; }
  .km { font-family: var(--tema-fonte-display); font-weight: 600; font-size: 20px; }
  .tempo { display: inline-flex; align-items: center; gap: 4px; font-size: 14px; color: var(--tema-tinta-2); }
  .tempo :global(svg) { color: var(--tema-tinta-3); }
  .foto { margin: 14px 0 0; }
  .ampliar { display: block; width: 100%; padding: 0; border: 0; background: var(--tema-papel-2); border-radius: var(--raio-1); overflow: hidden; cursor: zoom-in; aspect-ratio: 4 / 3; }
  .ampliar img { display: block; width: 100%; height: 100%; object-fit: cover; }
  .ampliar:focus-visible { outline: 2px solid var(--tema-acento); outline-offset: 2px; }
  figcaption { margin-top: 6px; font-size: 11.5px; color: var(--tema-tinta-3); }
  figcaption a { color: inherit; }
  .btn {
    display: flex; align-items: center; justify-content: center; gap: 8px; width: 100%;
    height: 48px; margin: 16px 0 0; padding: 0 18px; border-radius: var(--raio-2);
    border: 1px solid var(--tema-acento); color: var(--tema-acento);
    font-size: 15.5px; font-weight: 600; text-decoration: none;
  }
  .btn:hover { background: var(--tema-acento); color: var(--tema-acento-contraste); }
  .btn:focus-visible { outline: 2px solid var(--tema-acento); outline-offset: 2px; }
</style>
