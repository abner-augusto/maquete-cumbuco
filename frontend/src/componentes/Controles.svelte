<script lang="ts">
  import Bussola from './Bussola.svelte';
  import Icone from './Icone.svelte';

  let {
    rumo,
    buscaAtiva,
    entorno,
    escuro,
    masterplan,
    aoBuscar,
    aoEnquadrar,
    aoEntorno,
    aoMasterplan,
    aoAproximar,
    aoAfastar,
    aoAlternarCor,
    aoAjuda,
    aoCinema,
  }: {
    /** Rumo da câmera em graus, para a bússola. */
    rumo: number;
    buscaAtiva: boolean;
    /** Modo entorno; `null` enquanto não houver entorno para mostrar. */
    entorno: { ativo: boolean; carregando: boolean } | null;
    escuro: boolean;
    /** Projeção do masterplan no chão: ligada, o mapa leva o desenho dele; desligada, só o OSM. */
    masterplan: boolean;
    aoBuscar: () => void;
    aoEnquadrar: () => void;
    aoEntorno: () => void;
    aoMasterplan: () => void;
    aoAproximar: () => void;
    aoAfastar: () => void;
    aoAlternarCor: (origem: HTMLElement) => void;
    aoAjuda: () => void;
    aoCinema: () => void;
  } = $props();
</script>

<div class="controles">
  <Bussola graus={rumo} aoClicar={aoEnquadrar} />
  <div class="grupo">
    <button class="ctl" aria-label="Buscar lote" aria-pressed={buscaAtiva} onclick={aoBuscar}><Icone nome="buscar" /></button>
    <button class="ctl" aria-label="Enquadrar o loteamento" onclick={aoEnquadrar}><Icone nome="enquadrar" /></button>
    {#if entorno}
      <button class="ctl" class:carregando={entorno.carregando} aria-label="Entorno e pontos de referência" aria-pressed={entorno.ativo} aria-busy={entorno.carregando} onclick={aoEntorno}><Icone nome="entorno" /></button>
    {/if}
    <button class="ctl" aria-label="Projeção do masterplan" aria-pressed={masterplan} onclick={aoMasterplan}><Icone nome="mapa" /></button>
  </div>
  <div class="grupo">
    <button class="ctl" aria-label="Aproximar" onclick={aoAproximar}><Icone nome="mais" /></button>
    <button class="ctl" aria-label="Afastar" onclick={aoAfastar}><Icone nome="menos" /></button>
  </div>
  <div class="grupo">
    <button class="ctl" aria-label={escuro ? 'Usar modo claro' : 'Usar modo escuro'} onclick={e => aoAlternarCor(e.currentTarget)}><Icone nome={escuro ? 'claro' : 'lua'} /></button>
    <button class="ctl" aria-label="Como explorar" onclick={aoAjuda}><Icone nome="ajuda" /></button>
    <button class="ctl" aria-label="Modo cinema" onclick={aoCinema}><Icone nome="cinema" /></button>
  </div>
</div>

<style>
  .controles {
    position: absolute; right: 16px; top: 80px;
    display: flex; flex-direction: column; align-items: center; gap: 10px;
  }
  .grupo {
    display: flex; flex-direction: column;
    background: var(--tema-papel);
    border: 1px solid var(--tema-filete);
    border-radius: var(--raio-2);
    box-shadow: var(--tema-sombra-1);
    overflow: hidden;
  }
  .ctl {
    width: var(--toque); height: var(--toque);
    display: grid; place-items: center;
    border: 0; background: transparent; padding: 0; cursor: pointer;
    color: var(--tema-tinta);
    transition: background-color var(--dur-rapida) var(--ease-saida);
  }
  .grupo .ctl + .ctl { border-top: 1px solid var(--tema-filete); }
  .ctl:hover { background: var(--tema-papel-2); }
  .ctl:focus-visible { outline: 2px solid var(--tema-acento); outline-offset: -3px; }
  .ctl[aria-pressed="true"] { background: var(--tema-acento); color: var(--tema-acento-contraste); }
  .ctl.carregando :global(svg) { animation: girar 1.6s linear infinite; }
  @keyframes girar { to { transform: rotate(1turn); } }
  @media (prefers-reduced-motion: reduce) { .ctl.carregando :global(svg) { animation: none; opacity: .5; } }
  @container maquete (min-width: 900px) {
    .controles { top: 16px; }
  }
</style>
