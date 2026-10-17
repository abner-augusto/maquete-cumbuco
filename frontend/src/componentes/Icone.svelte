<script lang="ts" module>
  // Traço 1,6, cantos redondos, grade de 24px (DESIGN.md, "Controles flutuantes").
  const ICONES = {
    buscar: '<circle cx="10.5" cy="10.5" r="6"/><path d="M15 15l5 5"/>',
    fechar: '<path d="M6 6l12 12M18 6L6 18"/>',
    voltar: '<path d="M14.5 6l-6 6 6 6"/>',
    enquadrar: '<path d="M4 8.5V5a1 1 0 011-1h3.5M15.5 4H19a1 1 0 011 1v3.5M20 15.5V19a1 1 0 01-1 1h-3.5M8.5 20H5a1 1 0 01-1-1v-3.5"/><path d="M9 16.5v-6l3-2 3 2v6"/>',
    entorno: '<circle cx="12" cy="12" r="9" stroke-dasharray="2.2 2.2"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.4" fill="currentColor"/>',
    seta: '<path d="M5 12h13.5M13 6.5l5.5 5.5-5.5 5.5"/>',
    mais: '<path d="M12 5.5v13M5.5 12h13"/>',
    menos: '<path d="M5.5 12h13"/>',
    ajuda: '<circle cx="12" cy="12" r="8.5"/><path d="M9.6 9.6a2.5 2.5 0 114 2c-.9.6-1.6 1.1-1.6 2.2"/><circle cx="12" cy="16.9" r=".4" fill="currentColor"/>',
    externo: '<path d="M13.5 4.5h6v6M19.5 4.5l-8 8"/><path d="M17 14v4.5a1 1 0 01-1 1H5.5a1 1 0 01-1-1V8a1 1 0 011-1H10"/>',
    link: '<path d="M10 14a3.5 3.5 0 005 0l3-3a3.5 3.5 0 00-5-5l-1 1"/><path d="M14 10a3.5 3.5 0 00-5 0l-3 3a3.5 3.5 0 005 5l1-1"/><path d="M3.5 3.5l3 3M20.5 20.5l-3-3"/>',
    lua: '<path d="M19.5 14.5A8 8 0 019.5 4.5a8 8 0 1010 10z"/>',
    claro: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2.2M12 19.3v2.2M2.5 12h2.2M19.3 12h2.2M5.3 5.3l1.5 1.5M17.2 17.2l1.5 1.5M5.3 18.7l1.5-1.5M17.2 6.8l1.5-1.5"/>',
    camera: '<path d="M4 8.5h3l1.5-2h7l1.5 2h3v10H4z"/><circle cx="12" cy="13" r="3.2"/>',
    mapa: '<path d="M9 4.5l-5 2v13l5-2 6 2 5-2v-13l-5 2z"/><path d="M9 4.5v13M15 6.5v13"/>',
    cinema: '<rect x="3.5" y="6" width="17" height="12" rx="1.5"/><path d="M7.5 6v12M16.5 6v12M3.5 10h4M3.5 14h4M16.5 10h4M16.5 14h4"/>',
    foto: '<rect x="3.5" y="5" width="17" height="14" rx="1.5"/><circle cx="9" cy="10" r="1.8"/><path d="M20.5 16l-5-5-8 8"/>',
  } as const;
  export type NomeIcone = keyof typeof ICONES;

  // Gestos da primeira visita, grade de 44px.
  const GESTOS = {
    girar: '<path d="M9 17c5-6 21-6 26 0"/><path d="M31 12.5l4 4.5-5.5 1.2"/><path d="M19 37v-12.5a2.2 2.2 0 014.4 0V31l5.8 1.2a2.8 2.8 0 012.2 3.2l-.6 2.6"/>',
    pincar: '<path d="M12 12l-5-5M7 11.5V7h4.5M32 12l5-5M37 11.5V7h-4.5"/><path d="M16 38v-11a2 2 0 014 0v-9a2 2 0 014 0v9a2 2 0 014 0v4l-2 7"/>',
    tocar: '<rect x="8" y="5" width="11" height="9" rx="1"/><rect x="25" y="5" width="11" height="9" rx="1" fill="currentColor" fill-opacity=".18"/><path d="M27 21v-3.5a2.2 2.2 0 014.4 0V28l5 1a2.6 2.6 0 012 3l-1 5.5M27 21l-2.8-1.4a2 2 0 00-2.6 2.9L26 30"/><circle cx="30.5" cy="9.5" r="7.5" stroke-dasharray="2 3"/>',
  } as const;
  export type NomeGesto = keyof typeof GESTOS;
</script>

<script lang="ts">
  let { nome, gesto, tamanho = 22 }: { nome?: NomeIcone; gesto?: NomeGesto; tamanho?: number } = $props();
  const caixa = $derived(gesto ? 44 : 24);
  const desenho = $derived(gesto ? GESTOS[gesto] : nome ? ICONES[nome] : '');
</script>

<svg
  width={tamanho}
  height={tamanho}
  viewBox="0 0 {caixa} {caixa}"
  fill="none"
  stroke="currentColor"
  stroke-width="1.6"
  stroke-linecap="round"
  stroke-linejoin="round"
  aria-hidden="true"
  focusable="false">{@html desenho}</svg>
