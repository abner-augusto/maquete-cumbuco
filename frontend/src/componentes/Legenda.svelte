<script lang="ts">
  import type { Lote } from '../lib/dados';
  import { ROTULO_TIPO } from '../lib/lotes';

  // As cores dos tipos vêm dos materiais do GLB (cena.cores()); o status só aparece se algum lote tiver.
  let { cores, status }: { cores: Record<Lote['tipo'], string>; status: boolean } = $props();
</script>

<div class="legenda" aria-label="Legenda">
  <ul>
    {#each Object.entries(ROTULO_TIPO) as [tipo, rotulo] (tipo)}
      <li><i class="amostra" style:background={cores[tipo as Lote['tipo']]}></i>{rotulo}</li>
    {/each}
  </ul>
  {#if status}
    <ul class="status">
      <li><i class="amostra disponivel"></i>Disponível</li>
      <li><i class="amostra reservado"></i>Reservado</li>
      <li><i class="amostra vendido"></i>Vendido</li>
    </ul>
  {/if}
  <p class="ressalva">Maquete ilustrativa, não é projeto executivo.</p>
</div>

<style>
  .legenda {
    position: absolute; right: 16px;
    bottom: calc(var(--folha-h) + 12px);
    background: color-mix(in srgb, var(--tema-papel) 92%, transparent);
    border: 1px solid var(--tema-filete);
    border-radius: var(--raio-2);
    padding: 8px 10px;
    font-size: 12.5px; line-height: 1.25;
    box-shadow: var(--tema-sombra-1);
    transition: bottom var(--dur-folha) var(--ease-saida);
  }
  ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 5px; }
  .status { margin-top: 6px; padding-top: 6px; border-top: 1px solid var(--tema-filete); }
  li { display: flex; align-items: center; gap: 7px; }
  .amostra { width: 12px; height: 12px; border-radius: 2px; flex: none; box-shadow: inset 0 0 0 1px var(--tema-filete-forte); }
  .disponivel { background: var(--status-disponivel); }
  .reservado { background: var(--status-reservado); }
  .vendido { background: var(--status-vendido); opacity: var(--amostra-vendida-opacidade); }
  .ressalva { display: none; margin: 7px 0 0; padding-top: 6px; border-top: 1px solid var(--tema-filete); font-size: 11px; color: var(--tema-tinta-3); max-width: 150px; line-height: 1.3; }

  @container maquete (min-width: 900px) {
    .legenda { bottom: 16px; }
    .ressalva { display: block; }
  }
</style>
