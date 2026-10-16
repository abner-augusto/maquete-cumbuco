<!-- Modo dev (?dev): copia o link com a câmera de agora, para reproduzir exatamente o quadro visto. -->
<script lang="ts">
  import { linkDaCamera, type CameraDev } from '../lib/dev';

  let { camera }: { camera: () => CameraDev } = $props();
  let link = $state('');
  let campo: HTMLInputElement | undefined = $state();
  let aviso = $state('');

  async function copiar() {
    link = linkDaCamera(location.href, camera());
    try {
      // Na rede local (http) o clipboard assíncrono não existe: cai na seleção do campo.
      if (navigator.clipboard && isSecureContext) await navigator.clipboard.writeText(link);
      else {
        await Promise.resolve();
        campo?.select();
        if (!document.execCommand('copy')) throw Error('cópia recusada');
      }
      aviso = 'Copiado';
    } catch {
      aviso = 'Selecione e copie';
      campo?.select();
    }
  }
</script>

<div class="dev">
  <button onclick={copiar}>Copiar câmera</button>
  <input bind:this={campo} readonly value={link} aria-label="Link da câmera" placeholder="link da câmera" />
  {#if aviso}<span>{aviso}</span>{/if}
</div>

<style>
  .dev {
    position: absolute; left: 50%; top: 12px; transform: translateX(-50%); z-index: 30;
    display: flex; align-items: center; gap: 6px; padding: 6px; max-width: calc(100% - 32px);
    background: var(--tema-tinta); color: var(--tema-papel); border-radius: var(--raio-2);
    font-size: 12px; box-shadow: var(--tema-sombra-2);
  }
  button { height: 32px; padding: 0 10px; border: 0; border-radius: var(--raio-1); background: var(--tema-acento); color: var(--tema-acento-contraste); font: inherit; font-weight: 600; cursor: pointer; white-space: nowrap; }
  input { min-width: 0; width: 220px; height: 32px; padding: 0 8px; border: 0; border-radius: var(--raio-1); font: 11px ui-monospace, monospace; }
  span { white-space: nowrap; }
</style>
