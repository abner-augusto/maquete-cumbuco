// A troca de claro/escuro se revela num círculo que cresce a partir do botão tocado,
// como no UFCIM-FRONT3D (src/composables/useDarkMode.ts). Sem View Transitions ou com
// movimento reduzido, a troca é seca.
import { flushSync } from 'svelte';

type DocumentoComTransicao = Document & {
  startViewTransition?: (atualizar: () => void) => { finished: Promise<void> };
};

export function trocarCorComTransicao(trocar: () => void, origem?: HTMLElement): void {
  const doc = document as DocumentoComTransicao;
  if (!doc.startViewTransition || matchMedia('(prefers-reduced-motion: reduce)').matches) {
    trocar();
    return;
  }
  const raiz = document.documentElement;
  const caixa = origem?.getBoundingClientRect();
  const x = caixa ? caixa.left + caixa.width / 2 : innerWidth / 2;
  const y = caixa ? caixa.top + caixa.height / 2 : innerHeight / 2;
  const raio = Math.ceil(Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y)));
  raiz.style.setProperty('--transicao-cor-x', `${x}px`);
  raiz.style.setProperty('--transicao-cor-y', `${y}px`);
  raiz.style.setProperty('--transicao-cor-raio', `${raio}px`);
  // flushSync aplica o novo tema (e o céu da cena) dentro do callback, antes do quadro novo.
  void doc.startViewTransition(() => flushSync(trocar)).finished;
}
