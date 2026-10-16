// Estados do aparelho: primeira visita e escolha de cor.
// Toda leitura e escrita tolera storage bloqueado (aba anônima, prévia).

const CHAVE = { visitou: 'maquete:visitou', cor: 'maquete:cor', vegetacao: 'maquete:vegetacao' } as const;

/**
 * Quanto da vegetação do entorno o aparelho desenha: tela com mouse, tudo; tablet, metade;
 * celular, um quarto. `maquete:vegetacao` (0 a 1) sobrepõe a faixa, para medir num aparelho.
 */
export const vegetacao = {
  ler(): number {
    try {
      const salvo = Number.parseFloat(localStorage.getItem(CHAVE.vegetacao) ?? '');
      if (salvo >= 0 && salvo <= 1) return salvo;
    } catch {
      /* sem storage, vale a faixa do aparelho */
    }
    if (!matchMedia('(pointer: coarse)').matches) return 1;
    return Math.min(screen.width, screen.height) >= 600 ? 0.5 : 0.25;
  },
};

/** Escolha manual de claro/escuro; sem ela, vale o `prefers-color-scheme` do aparelho. */
export const modoCor = {
  ler(): 'claro' | 'escuro' | null {
    try {
      const valor = localStorage.getItem(CHAVE.cor);
      return valor === 'claro' || valor === 'escuro' ? valor : null;
    } catch {
      return null;
    }
  },
  gravar(valor: 'claro' | 'escuro') {
    try {
      localStorage.setItem(CHAVE.cor, valor);
    } catch {
      /* sem storage, a escolha vale só nesta visita */
    }
  },
};

export const primeiraVisita = {
  pendente(): boolean {
    try {
      return localStorage.getItem(CHAVE.visitou) !== '1';
    } catch {
      return true;
    }
  },
  concluir() {
    try {
      localStorage.setItem(CHAVE.visitou, '1');
    } catch {
      /* sem storage, a ajuda volta na próxima visita */
    }
  },
};
