<script lang="ts">
  // Miniatura do lote: o polígono do JSON encaixado numa caixa 240×160, norte para cima.
  let { poligono, area }: { poligono: [number, number][]; area: string } = $props();

  const L = 240;
  const A = 160;
  const M = 12;
  const pontos = $derived.by(() => {
    const xs = poligono.map(p => p[0]);
    const ys = poligono.map(p => p[1]);
    const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
    const k = Math.min((L - 2 * M) / (x1 - x0 || 1), (A - 2 * M) / (y1 - y0 || 1));
    const dx = (L - (x1 - x0) * k) / 2;
    const dy = (A - (y1 - y0) * k) / 2;
    return poligono.map(([x, y]) => `${(dx + (x - x0) * k).toFixed(1)},${(A - dy - (y - y0) * k).toFixed(1)}`).join(' ');
  });
</script>

<svg viewBox="0 0 {L} {A}" width={L} height={A} role="img" aria-label="Contorno do lote, {area}">
  <polygon points={pontos} />
</svg>

<style>
  svg { display: block; width: 100%; max-width: 240px; height: auto; margin: 0 auto; }
  polygon { fill: var(--tema-areia); stroke: var(--tema-tinta); stroke-width: 1.4; stroke-linejoin: round; }
</style>
