<script lang="ts">
  let { escuro }: { escuro: boolean } = $props();
</script>

<div class="marca">
  <img src={escuro ? 'marca/produto-horizontal-negativo.svg' : 'marca/produto-horizontal-positivo.svg'} alt="Cidade das Américas — Residencial Cumbuco" />
</div>

<style>
  .marca {
    position: absolute; top: 12px; left: 16px;
    display: flex; align-items: center;
    height: 58px; padding: 0 14px;
    background: var(--tema-papel);
    border: 1px solid var(--tema-filete);
    border-radius: var(--raio-2);
    box-shadow: var(--tema-sombra-1);
  }
  img { display: block; height: 38px; width: auto; }
  @container maquete (min-width: 900px) {
    .marca { top: 16px; height: 62px; }
    img { height: 42px; }
  }
</style>
