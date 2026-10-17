<!-- Modo dev (?dev): painel para ajustar a água e o sol ao vivo. Os valores ficam no navegador (localStorage)
     e "Copiar valores" entrega o que fechou, para virar o padrão em agua.ts e cena.ts. -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { COR_AGUA, COR_AGUA_PADRAO, PARAMETROS_AGUA, type CorDaAgua, type ModoCor } from '../lib/cena/agua';
  import { SOL, type Cena, type Sol } from '../lib/cena/cena';

  let { cena, cor }: { cena: Cena; cor: ModoCor } = $props();

  const CHAVE = 'maquete-dev-agua';
  const CHAVES_COR: { chave: keyof CorDaAgua; nome: string }[] = [
    { chave: 'rasa', nome: 'Água rasa' },
    { chave: 'funda', nome: 'Água funda' },
    { chave: 'espuma', nome: 'Espuma' },
  ];
  const SLIDERS_SOL: { chave: keyof Sol; nome: string; min: number; max: number; passo: number }[] = [
    { chave: 'azimute', nome: 'Azimute (° do norte, horário)', min: 0, max: 360, passo: 1 },
    { chave: 'altitude', nome: 'Altitude (°)', min: -5, max: 90, passo: 1 },
    { chave: 'calor', nome: 'Calor do céu (0 alto, 1 baixo)', min: 0, max: 1, passo: 0.01 },
    { chave: 'brilho', nome: 'Halo do sol no céu', min: 0, max: 1, passo: 0.01 },
  ];

  const padraoAgua = Object.fromEntries(PARAMETROS_AGUA.map(p => [p.uniforme, p.valor]));
  let aberto = $state(false);
  let agua = $state<Record<string, number>>({ ...padraoAgua });
  let sol = $state<Sol>({ ...SOL });
  // O hex de cada cor, do modo em uso; as duas paletas (claro e escuro) vivem em COR_AGUA.
  let cores = $state<Record<ModoCor, CorDaAgua>>({ claro: { ...COR_AGUA.claro }, escuro: { ...COR_AGUA.escuro } });
  let texto = $state('');
  let campo: HTMLTextAreaElement | undefined = $state();
  let aviso = $state('');

  const nomeCor = (modo: ModoCor) => (modo === 'claro' ? 'claro' : 'escuro');

  function guardar() {
    try {
      localStorage.setItem(CHAVE, JSON.stringify({ agua, sol, cores }));
    } catch { /* sem armazenamento: o painel funciona igual, só não lembra */ }
  }

  function mudarAgua(uniforme: string, valor: number) {
    agua[uniforme] = valor;
    cena.ajustarAgua(uniforme, valor);
    guardar();
  }

  function mudarCor(modo: ModoCor, chave: keyof CorDaAgua, hex: string) {
    cores[modo][chave] = hex;
    cena.ajustarCorAgua(modo, chave, hex);
    guardar();
  }

  function mudarSol(chave: keyof Sol, valor: number) {
    sol[chave] = valor;
    cena.ajustarSol({ ...sol });
    guardar();
  }

  function aplicarTudo() {
    for (const [u, v] of Object.entries(agua)) cena.ajustarAgua(u, v);
    for (const modo of ['claro', 'escuro'] as const) for (const { chave } of CHAVES_COR) cena.ajustarCorAgua(modo, chave, cores[modo][chave]);
    cena.ajustarSol({ ...sol });
  }

  function restaurar() {
    agua = { ...padraoAgua };
    sol = { ...SOL };
    cores = { claro: { ...COR_AGUA_PADRAO.claro }, escuro: { ...COR_AGUA_PADRAO.escuro } };
    aplicarTudo();
    try { localStorage.removeItem(CHAVE); } catch { /* idem */ }
    aviso = 'Padrão restaurado';
  }

  onMount(() => {
    try {
      const s = JSON.parse(localStorage.getItem(CHAVE) ?? 'null');
      if (s) {
        agua = { ...agua, ...s.agua };
        sol = { ...sol, ...s.sol };
        for (const modo of ['claro', 'escuro'] as const) cores[modo] = { ...cores[modo], ...s.cores?.[modo] };
        aplicarTudo();
      }
    } catch { /* valor guardado ilegível: fica o padrão */ }
  });

  async function copiar() {
    texto = JSON.stringify({ agua, sol, cores }, null, 2);
    try {
      // Na rede local (http) o clipboard assíncrono não existe: cai na seleção do campo.
      if (navigator.clipboard && isSecureContext) await navigator.clipboard.writeText(texto);
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

<div class="painel" class:aberto>
  <button class="titulo" aria-expanded={aberto} onclick={() => (aberto = !aberto)}>Água e sol</button>
  {#if aberto}
    <div class="corpo">
      <h3>Sol</h3>
      {#each SLIDERS_SOL as s (s.chave)}
        <label>
          <span>{s.nome}</span>
          <input type="range" min={s.min} max={s.max} step={s.passo} value={sol[s.chave]} oninput={e => mudarSol(s.chave, Number(e.currentTarget.value))} />
          <output>{sol[s.chave]}</output>
        </label>
      {/each}

      <h3>Cores ({nomeCor(cor)})</h3>
      {#each CHAVES_COR as c (c.chave)}
        <label class="cor">
          <span>{c.nome}</span>
          <input type="color" value={cores[cor][c.chave]} oninput={e => mudarCor(cor, c.chave, e.currentTarget.value)} />
          <output>{cores[cor][c.chave]}</output>
        </label>
      {/each}

      <h3>Água</h3>
      {#each PARAMETROS_AGUA as p (p.uniforme)}
        <label>
          <span>{p.nome}</span>
          <input type="range" min={p.min} max={p.max} step={p.passo} value={agua[p.uniforme]} oninput={e => mudarAgua(p.uniforme, Number(e.currentTarget.value))} />
          <output>{agua[p.uniforme]}</output>
        </label>
      {/each}

      <div class="acoes">
        <button onclick={copiar}>Copiar valores</button>
        <button onclick={restaurar}>Restaurar padrão</button>
        {#if aviso}<span>{aviso}</span>{/if}
      </div>
      <textarea bind:this={campo} readonly rows="3" aria-label="Valores copiados" value={texto} placeholder="valores ao copiar"></textarea>
    </div>
  {/if}
</div>

<style>
  .painel {
    position: absolute; left: 16px; top: 84px; z-index: 30; width: 300px; max-width: calc(100% - 32px);
    background: var(--tema-tinta); color: var(--tema-papel); border-radius: var(--raio-2);
    font-size: 12px; box-shadow: var(--tema-sombra-2); overflow: hidden;
  }
  .titulo { width: 100%; height: 36px; padding: 0 12px; border: 0; background: none; color: inherit; font: inherit; font-weight: 600; text-align: left; cursor: pointer; }
  .corpo { max-height: calc(100cqh - 160px); overflow-y: auto; padding: 0 12px 12px; }
  h3 { margin: 10px 0 4px; font-size: 11px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; opacity: .7; }
  label { display: grid; grid-template-columns: 1fr 58px; align-items: center; column-gap: 8px; margin: 4px 0; }
  label span { grid-column: 1 / -1; }
  label input[type="range"] { width: 100%; accent-color: var(--tema-acento); }
  label.cor { grid-template-columns: 1fr auto; }
  label.cor span { grid-column: auto; }
  label.cor input { width: 36px; height: 24px; padding: 0; border: 0; background: none; }
  output { font: 11px ui-monospace, monospace; text-align: right; }
  .acoes { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin: 12px 0 6px; }
  .acoes button { height: 30px; padding: 0 10px; border: 0; border-radius: var(--raio-1); background: var(--tema-acento); color: var(--tema-acento-contraste); font: inherit; font-weight: 600; cursor: pointer; }
  textarea { width: 100%; box-sizing: border-box; border: 0; border-radius: var(--raio-1); font: 10px ui-monospace, monospace; resize: vertical; }
</style>
