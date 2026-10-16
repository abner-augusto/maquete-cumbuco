// Estados do aparelho: primeira visita e escolha de cor.
// Toda leitura e escrita tolera storage bloqueado (aba anônima, prévia).

const CHAVE = { visitou: 'maquete:visitou', cor: 'maquete:cor' } as const;

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
