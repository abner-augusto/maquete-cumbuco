<script lang="ts">
  import type { Config, Lote } from '../lib/dados';
  import { formatarArea, linkDoLote, metros, reais, ROTULO_TIPO, rotuloLongo } from '../lib/lotes';
  import Contorno from './Contorno.svelte';
  import Icone from './Icone.svelte';

  let { lote, config, precos, aoFechar }: { lote: Lote; config: Config; precos: boolean; aoFechar: () => void } = $props();
  let copiado = $state(false);
  // No pacote offline o link seria 127.0.0.1, inútil para o cliente.
  const offline = typeof document !== 'undefined' && !!document.querySelector('meta[name="maquete-offline"]');
  const temPreco = $derived(precos && lote.preco_total !== undefined);
  const STATUS = { disponivel: 'Disponível', reservado: 'Reservado', vendido: 'Vendido' } as const;

  async function compartilhar() {
    const url = linkDoLote(location.href, lote.id);
    const dados = { title: rotuloLongo(lote), url };
    if (navigator.share) await navigator.share(dados).catch(() => {});
    else { await navigator.clipboard?.writeText(url); copiado = true; setTimeout(() => (copiado = false), 2000); }
  }
</script>

<div class="barra"><span></span><button class="fechar" aria-label="Fechar ficha" onclick={aoFechar}><Icone nome="fechar" tamanho={18} /></button></div>
<h2 class="titulo">{rotuloLongo(lote)}</h2>
<p class="tipo">{ROTULO_TIPO[lote.tipo]}{#if lote.status} · <span class="status {lote.status}">{STATUS[lote.status]}</span>{/if}</p>

<dl class="campos">
  <div><dt>Área</dt><dd>{formatarArea(lote.area_m2)}</dd></div>
  {#if lote.frente_m !== null}<div><dt>Frente</dt><dd>{metros(lote.frente_m)}</dd></div>{/if}
  {#if lote.inscricao_iptu}<div><dt>Inscrição IPTU</dt><dd>{lote.inscricao_iptu}</dd></div>{/if}
</dl>

<figure class="contorno"><Contorno poligono={lote.poligono} area={formatarArea(lote.area_m2)} />
  <figcaption>Lados: {lote.lados_m.map(n => metros(n)).join(' · ')}</figcaption></figure>

{#if temPreco}
  <section class="preco" aria-label="Preço">
    <p class="total">{reais(lote.preco_total!)}</p>
    {#if lote.preco_m2 !== undefined}<p class="m2">{reais(lote.preco_m2)}/m²</p>{/if}
    <p class="carimbo">Tabela {config.tabelaPrecos.nome} · ref. {config.tabelaPrecos.referencia}</p>
  </section>
{/if}

{#if !offline}<button class="btn" onclick={compartilhar}><Icone nome="link" tamanho={18} />{copiado ? 'Link copiado' : 'Compartilhar'}</button>{/if}

<style>
  .barra { display: flex; align-items: center; justify-content: space-between; height: var(--toque); margin: 0 -12px 2px; }
  .fechar { display: inline-flex; align-items: center; justify-content: center; width: var(--toque); height: var(--toque); padding: 0; border: 0; background: none; border-radius: var(--raio-1); color: var(--tema-tinta-2); cursor: pointer; }
  .fechar:hover { background: var(--tema-papel-2); color: var(--tema-tinta); }
  .fechar:focus-visible { outline: 2px solid var(--tema-acento); outline-offset: 2px; }
  .titulo { font-family: var(--tema-fonte-display); font-weight: 600; font-size: 30px; line-height: 1.05; margin: 0; }
  .tipo { margin: 6px 0 0; font-size: 15px; color: var(--tema-tinta-2); font-weight: 500; }
  .status.disponivel { color: var(--status-disponivel-texto); }
  .status.reservado { color: var(--status-reservado-texto); }
  .status.vendido { color: var(--status-vendido-texto); }
  .campos { display: grid; grid-template-columns: repeat(auto-fit, minmax(0, 1fr)); margin: 16px 0 0; border: 1px solid var(--tema-filete); border-radius: var(--raio-1); }
  .campos > div { padding: 8px 10px 9px; min-width: 0; }
  .campos > div + div { border-left: 1px solid var(--tema-filete); }
  dt { font-family: var(--tema-fonte-rotulo); font-size: 11px; letter-spacing: .14em; text-transform: uppercase; color: var(--tema-tinta-3); font-weight: 500; line-height: 1.2; }
  dd { margin: 3px 0 0; font-weight: 600; font-size: 15px; line-height: 1.2; overflow-wrap: anywhere; }
  .contorno { margin: 16px 0 0; padding: 12px; background: var(--tema-papel-2); border-radius: var(--raio-1); }
  figcaption { margin-top: 8px; font-size: 12.5px; color: var(--tema-tinta-2); }
  .preco { margin: 16px 0 0; padding: 12px; border: 1px solid var(--tema-filete); border-radius: var(--raio-1); }
  .preco p { margin: 0; }
  .total { font-family: var(--tema-fonte-display); font-weight: 600; font-size: 26px; }
  .m2 { font-size: 14px; color: var(--tema-tinta-2); }
  .carimbo { margin-top: 6px !important; font-size: 12px; color: var(--tema-tinta-3); }
  .btn {
    display: flex; align-items: center; justify-content: center; gap: 8px; width: 100%;
    height: 48px; margin: 16px 0 0; padding: 0 18px; border-radius: var(--raio-2);
    border: 1px solid var(--tema-acento); background: none; color: var(--tema-acento);
    font-size: 15.5px; font-weight: 600; cursor: pointer;
  }
  .btn:hover { background: var(--tema-acento); color: var(--tema-acento-contraste); }
  .btn:focus-visible { outline: 2px solid var(--tema-acento); outline-offset: 2px; }
</style>
