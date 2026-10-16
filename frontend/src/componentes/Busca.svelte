<script lang="ts">
  import type { Lote } from '../lib/dados';
  import { formatarArea, ROTULO_TIPO, rotuloCurto } from '../lib/lotes';
  import Icone from './Icone.svelte';

  let {
    consulta = $bindable(''),
    resultados,
    aoEscolher,
  }: { consulta: string; resultados: Lote[]; aoEscolher: (id: string) => void } = $props();

  let campo: HTMLInputElement | undefined = $state();
  $effect(() => campo?.focus());
</script>

<label class="busca">
  <Icone nome="buscar" tamanho={20} />
  <input bind:this={campo} bind:value={consulta} aria-label="Quadra e lote" placeholder="Quadra e lote, ex.: 7 4" inputmode="text" autocomplete="off" />
  {#if consulta}<button class="limpar" aria-label="Limpar busca" onclick={() => ((consulta = ''), campo?.focus())}><Icone nome="fechar" tamanho={18} /></button>{/if}
</label>

{#if consulta.trim()}
  <p class="contagem" role="status">
    {resultados.length === 0 ? 'Nenhum lote encontrado' : resultados.length === 1 ? '1 lote' : `${resultados.length} lotes`}
  </p>
  <ul class="resultados">
    {#each resultados as lote (lote.id)}
      <li>
        <button class="resultado" onclick={() => aoEscolher(lote.id)}>
          <span class="n">{rotuloCurto(lote)}</span>
          <span class="tipo">{ROTULO_TIPO[lote.tipo]} · {formatarArea(lote.area_m2)}</span>
        </button>
      </li>
    {/each}
  </ul>
{/if}

<style>
  .busca { display: flex; align-items: center; gap: 10px; height: 48px; padding: 0 6px 0 14px; border: 1.5px solid var(--tema-acento); border-radius: var(--raio-2); background: var(--tema-campo); color: var(--tema-tinta-2); }
  input { flex: 1; min-width: 0; border: 0; outline: 0; background: none; font: inherit; font-size: 20px; font-weight: 600; color: var(--tema-tinta); caret-color: var(--tema-acento); }
  input::placeholder { color: var(--tema-tinta-3); font-weight: 400; font-size: 15px; }
  .limpar { width: var(--toque); height: var(--toque); display: grid; place-items: center; border: 0; background: none; color: var(--tema-tinta-2); border-radius: var(--raio-1); cursor: pointer; }
  .contagem { margin: 12px 0 4px; font-size: 13px; color: var(--tema-tinta-2); }
  .resultados { list-style: none; margin: 0 -20px; padding: 0; }
  .resultados li + li { border-top: 1px solid var(--tema-filete); }
  .resultado { display: grid; grid-template-columns: auto 1fr; align-items: center; gap: 14px; width: 100%; min-height: var(--toque); padding: 12px 20px; border: 0; background: none; text-align: left; cursor: pointer; color: var(--tema-tinta); }
  .resultado:hover { background: var(--tema-papel-2); }
  .resultado:focus-visible { outline: 2px solid var(--tema-acento); outline-offset: -2px; }
  .n { font-family: var(--tema-fonte-display); font-weight: 600; font-size: 22px; line-height: 1; min-width: 120px; }
  .tipo { font-size: 13.5px; color: var(--tema-tinta-2); }
</style>
