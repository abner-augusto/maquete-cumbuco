<script lang="ts">
  import Icone from './Icone.svelte';

  let { src, alt, aoFechar }: { src: string; alt: string; aoFechar: () => void } = $props();

  let dialogo: HTMLElement | undefined = $state();
  let fechar: HTMLButtonElement | undefined = $state();
  let areaImg: HTMLElement | undefined = $state();
  let imgEl: HTMLImageElement | undefined = $state();
  let escala = $state(1);
  let panX = $state(0);
  let panY = $state(0);
  let animando = $state(false);
  let arrastando = $state(false);

  // Rastreamento de ponteiros para gestos de pinça (zoom com dois dedos) e arrasto
  const ponteiros = new Map<number, { x: number; y: number }>();
  let distanciaInicial = 0;
  let escalaInicial = 1;
  let centroPinchInicial = { x: 0, y: 0 };
  let panInicial = { x: 0, y: 0 };
  let ultimoPanPonto = { x: 0, y: 0 };

  // Detecção de toque duplo
  let ultimoToqueTempo = 0;
  let ultimoToquePos = { x: 0, y: 0 };

  function obterDoisPonteiros(): [{ x: number; y: number }, { x: number; y: number }] | null {
    const lista = Array.from(ponteiros.values());
    if (lista.length < 2 || !lista[0] || !lista[1]) return null;
    return [lista[0], lista[1]];
  }

  // Reseta estado quando a imagem muda
  $effect(() => {
    void src;
    resetarZoom(false);
  });

  // Limita o deslocamento com base nas dimensões reais renderizadas da imagem vs tela inteira
  function limitarPan() {
    if (!areaImg || !imgEl) return;
    const rect = areaImg.getBoundingClientRect();
    const wImg = imgEl.offsetWidth * escala;
    const hImg = imgEl.offsetHeight * escala;

    const maxPanX = Math.max(0, (wImg - rect.width) / 2);
    const maxPanY = Math.max(0, (hImg - rect.height) / 2);

    panX = Math.max(-maxPanX, Math.min(maxPanX, panX));
    panY = Math.max(-maxPanY, Math.min(maxPanY, panY));
  }

  function resetarZoom(animar = true) {
    if (animar) {
      animando = true;
      setTimeout(() => (animando = false), 240);
    }
    escala = 1;
    panX = 0;
    panY = 0;
  }

  function calcularEscalaAltura(): number {
    if (!areaImg || !imgEl || !imgEl.offsetHeight) return 2.5;
    const rect = areaImg.getBoundingClientRect();
    const proporcao = rect.height / imgEl.offsetHeight;
    return Math.max(1.8, Number(proporcao.toFixed(2)));
  }

  function tratarDuploToque(clientX: number, clientY: number) {
    if (escala > 1.05) {
      resetarZoom(true);
    } else {
      const escalaAlvo = calcularEscalaAltura();
      zoomNoPonto(clientX, clientY, escalaAlvo);
    }
  }

  function ajustarZoom(delta: number) {
    animando = true;
    const nova = Math.min(Math.max(1, escala + delta), 8);
    if (nova === 1) {
      resetarZoom(true);
    } else {
      escala = Number(nova.toFixed(2));
      limitarPan();
      setTimeout(() => (animando = false), 240);
    }
  }

  function zoomNoPonto(clientX: number, clientY: number, novaEscala: number) {
    if (!areaImg || !imgEl) return;
    animando = true;
    const rect = areaImg.getBoundingClientRect();
    const centroX = rect.left + rect.width / 2;
    const centroY = rect.top + rect.height / 2;
    const dx = clientX - centroX;
    const dy = clientY - centroY;
    panX = -dx * (novaEscala - 1);
    panY = -dy * (novaEscala - 1);
    escala = novaEscala;
    limitarPan();
    setTimeout(() => (animando = false), 240);
  }

  function aoBaixarPonteiro(e: PointerEvent) {
    if (!areaImg) return;
    ponteiros.set(e.pointerId, { x: e.clientX, y: e.clientY });
    areaImg.setPointerCapture(e.pointerId);

    // Toque duplo em dispositivos touch: alterna entre altura da tela e 100%
    if (e.pointerType === 'touch') {
      const agora = Date.now();
      const distToque = Math.hypot(e.clientX - ultimoToquePos.x, e.clientY - ultimoToquePos.y);
      if (agora - ultimoToqueTempo < 300 && distToque < 30) {
        tratarDuploToque(e.clientX, e.clientY);
        ultimoToqueTempo = 0;
        ponteiros.clear();
        return;
      }
      ultimoToqueTempo = agora;
      ultimoToquePos = { x: e.clientX, y: e.clientY };
    }

    if (ponteiros.size === 1) {
      arrastando = escala > 1;
      ultimoPanPonto = { x: e.clientX, y: e.clientY };
    } else if (ponteiros.size === 2) {
      arrastando = false;
      const dois = obterDoisPonteiros();
      if (dois) {
        const [p1, p2] = dois;
        distanciaInicial = Math.hypot(p2.x - p1.x, p2.y - p1.y);
        escalaInicial = escala;
        centroPinchInicial = { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 };
        panInicial = { x: panX, y: panY };
      }
    }
  }

  function aoMoverPonteiro(e: PointerEvent) {
    if (!ponteiros.has(e.pointerId)) return;
    ponteiros.set(e.pointerId, { x: e.clientX, y: e.clientY });

    // Pinça com dois dedos
    if (ponteiros.size === 2 && distanciaInicial > 0) {
      const dois = obterDoisPonteiros();
      if (dois) {
        const [p1, p2] = dois;
        const d = Math.hypot(p2.x - p1.x, p2.y - p1.y);
        const fator = d / distanciaInicial;
        const novaEscala = Math.min(Math.max(1, escalaInicial * fator), 8);
        const centroAtual = { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 };
        const dx = centroAtual.x - centroPinchInicial.x;
        const dy = centroAtual.y - centroPinchInicial.y;
        escala = Number(novaEscala.toFixed(3));
        panX = panInicial.x + dx;
        panY = panInicial.y + dy;
        limitarPan();
      }
    } else if (ponteiros.size === 1 && escala > 1 && arrastando) {
      const dx = e.clientX - ultimoPanPonto.x;
      const dy = e.clientY - ultimoPanPonto.y;
      panX += dx;
      panY += dy;
      ultimoPanPonto = { x: e.clientX, y: e.clientY };
      limitarPan();
    }
  }

  function aoSubirPonteiro(e: PointerEvent) {
    ponteiros.delete(e.pointerId);
    if (ponteiros.size < 2) {
      distanciaInicial = 0;
    }
    if (ponteiros.size === 1) {
      const lista = Array.from(ponteiros.values());
      const p = lista[0];
      if (p) {
        ultimoPanPonto = { x: p.x, y: p.y };
        arrastando = escala > 1;
      }
    } else if (ponteiros.size === 0) {
      arrastando = false;
      if (escala <= 1.05) {
        resetarZoom(true);
      } else {
        limitarPan();
      }
    }
  }

  function aoDuploClique(e: MouseEvent) {
    tratarDuploToque(e.clientX, e.clientY);
  }

  // Foco inicial, teclado e suporte a roda do mouse com preventDefault sem intervenção
  $effect(() => {
    const anterior = document.activeElement as HTMLElement | null;
    fechar?.focus();

    const tecla = (e: KeyboardEvent) => {
      if (e.key === 'Tab') {
        const botoes = Array.from(dialogo?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)') ?? []);
        const primeiro = botoes[0];
        const ultimo = botoes.at(-1);
        if (e.shiftKey && document.activeElement === primeiro) { e.preventDefault(); ultimo?.focus(); }
        else if (!e.shiftKey && document.activeElement === ultimo) { e.preventDefault(); primeiro?.focus(); }
      } else if (e.key === 'Escape') {
        aoFechar();
      } else if (e.key === '+' || e.key === '=') {
        ajustarZoom(0.5);
      } else if (e.key === '-' || e.key === '_') {
        ajustarZoom(-0.5);
      } else if (e.key === '0') {
        resetarZoom(true);
      }
    };
    addEventListener('keydown', tecla);

    const el = areaImg;
    const tratarRoda = (e: WheelEvent) => {
      e.preventDefault();
      const delta = -e.deltaY * 0.002;
      const nova = Math.min(Math.max(1, escala + delta), 8);
      if (nova === 1) {
        resetarZoom(false);
      } else if (el) {
        const rect = el.getBoundingClientRect();
        const mouseX = e.clientX - (rect.left + rect.width / 2);
        const mouseY = e.clientY - (rect.top + rect.height / 2);
        const ratio = nova / escala;
        panX = mouseX - ratio * (mouseX - panX);
        panY = mouseY - ratio * (mouseY - panY);
        escala = Number(nova.toFixed(3));
        limitarPan();
      }
    };

    if (el) {
      el.addEventListener('wheel', tratarRoda, { passive: false });
    }

    return () => {
      removeEventListener('keydown', tecla);
      if (el) el.removeEventListener('wheel', tratarRoda);
      anterior?.focus();
    };
  });
</script>

<!-- Visualizador em tela cheia (lightbox) -->
<div class="fundo" bind:this={dialogo} role="dialog" aria-modal="true" aria-label={alt}>
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="visualizador"
    class:ampliado={escala > 1}
    class:arrastando
    bind:this={areaImg}
    onpointerdown={aoBaixarPonteiro}
    onpointermove={aoMoverPonteiro}
    onpointerup={aoSubirPonteiro}
    onpointercancel={aoSubirPonteiro}
    ondblclick={aoDuploClique}
  >
    <img
      bind:this={imgEl}
      {src}
      {alt}
      draggable="false"
      onload={() => { resetarZoom(false); }}
      style:transform="translate3d({panX}px, {panY}px, 0) scale({escala})"
      class:transicao={animando}
    />
  </div>

  <button class="fechar" bind:this={fechar} aria-label="Fechar visualizador" onclick={aoFechar}>
    <Icone nome="fechar" tamanho={20} />
  </button>

  <div class="controles-zoom" role="toolbar" aria-label="Controles de zoom">
    <button
      class="btn-zoom"
      aria-label="Aproximar zoom"
      onclick={() => ajustarZoom(0.5)}
      disabled={escala >= 8}
    >
      <Icone nome="mais" tamanho={18} />
    </button>
    <span class="escala-rotulo">{Math.round(escala * 100)}%</span>
    <button
      class="btn-zoom"
      aria-label="Afastar zoom"
      onclick={() => ajustarZoom(-0.5)}
      disabled={escala <= 1}
    >
      <Icone nome="menos" tamanho={18} />
    </button>
    {#if escala > 1}
      <button
        class="btn-zoom reset"
        aria-label="Redefinir zoom"
        onclick={() => resetarZoom(true)}
      >
        <Icone nome="enquadrar" tamanho={18} />
      </button>
    {/if}
  </div>
</div>

<style>
  .fundo {
    position: fixed; inset: 0; z-index: 50;
    display: flex; align-items: center; justify-content: center;
    background: rgba(12, 12, 12, 0.94);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    animation: entra var(--dur-base) var(--ease-saida);
    overflow: hidden;
  }
  .visualizador {
    position: absolute; inset: 0;
    width: 100%; height: 100%;
    display: flex; align-items: center; justify-content: center;
    overflow: hidden;
    touch-action: none;
    user-select: none;
    -webkit-user-select: none;
    cursor: zoom-in;
  }
  .visualizador.ampliado {
    cursor: grab;
  }
  .visualizador.ampliado.arrastando {
    cursor: grabbing;
  }
  img {
    display: block;
    max-width: 100%;
    max-height: 100%;
    width: auto;
    height: auto;
    object-fit: contain;
    transform-origin: center center;
    will-change: transform;
    pointer-events: none;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
  }
  img.transicao {
    transition: transform var(--dur-base) var(--ease-saida);
  }
  .fechar {
    position: absolute;
    top: max(16px, env(safe-area-inset-top, 16px));
    right: max(16px, env(safe-area-inset-right, 16px));
    width: var(--toque); height: var(--toque);
    display: grid; place-items: center;
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 50%;
    background: rgba(28, 28, 28, 0.75);
    color: #FFFFFF;
    cursor: pointer;
    z-index: 10;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.35);
    transition: background-color var(--dur-rapida), transform var(--dur-rapida);
  }
  .fechar:hover {
    background: rgba(60, 60, 60, 0.85);
  }
  .fechar:focus-visible {
    outline: 2px solid var(--tema-acento);
    outline-offset: 2px;
  }
  .controles-zoom {
    position: absolute;
    bottom: max(24px, env(safe-area-inset-bottom, 24px));
    left: 50%;
    transform: translateX(-50%);
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    background: rgba(28, 28, 28, 0.8);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: var(--raio-3);
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.45);
    z-index: 10;
    pointer-events: auto;
  }
  .btn-zoom {
    width: 32px;
    height: 32px;
    display: grid;
    place-items: center;
    border: 0;
    border-radius: 50%;
    background: transparent;
    color: #FFFFFF;
    cursor: pointer;
    padding: 0;
    transition: background-color var(--dur-rapida);
  }
  .btn-zoom:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.15);
  }
  .btn-zoom:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }
  .btn-zoom:focus-visible {
    outline: 2px solid var(--tema-acento);
    outline-offset: 2px;
  }
  .escala-rotulo {
    font-size: 13px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    min-width: 42px;
    text-align: center;
    color: rgba(255, 255, 255, 0.95);
    user-select: none;
  }
  @keyframes entra { from { opacity: 0; } }
</style>
