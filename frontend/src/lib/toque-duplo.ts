interface Contato {
  pointerId: number;
  pointerType: string;
  clientX: number;
  clientY: number;
  timeStamp: number;
}
interface Limites {
  duracaoMaxima: number;
  intervaloMinimo: number;
  intervaloMaximo: number;
  duracaoTotalMaxima: number;
  movimentoMaximo: number;
  distanciaMaxima: number;
}
const PADRAO: Limites = {
  duracaoMaxima: 250,
  intervaloMinimo: 40,
  intervaloMaximo: 350,
  duracaoTotalMaxima: 700,
  movimentoMaximo: 12,
  distanciaMaxima: 28,
};

/** Reconhece dois contatos completos. Os tempos usam a mesma origem monotônica de PointerEvent.timeStamp. */
export function criarToqueDuplo(ajustes: Partial<Limites> = {}) {
  const limites = { ...PADRAO, ...ajustes };
  const ativos = new Set<number>();
  let candidato: Contato | null = null;
  let anterior: { inicio: Contato; fim: number } | null = null;

  function limpar() {
    ativos.clear();
    candidato = anterior = null;
  }
  function baixar(e: Contato) {
    ativos.add(e.pointerId);
    if (e.pointerType !== 'touch' || ativos.size !== 1) {
      candidato = anterior = null;
      return;
    }
    // Eventos DOM têm propriedades no protótipo, por isso copiamos os campos explicitamente.
    candidato = { pointerId: e.pointerId, pointerType: e.pointerType,
      clientX: e.clientX, clientY: e.clientY, timeStamp: e.timeStamp };
  }
  function mover(e: Contato) {
    if (!candidato || candidato.pointerId !== e.pointerId) return;
    if (Math.hypot(e.clientX - candidato.clientX, e.clientY - candidato.clientY) > limites.movimentoMaximo) {
      candidato = anterior = null;
    }
  }
  function subir(e: Contato): boolean {
    mover(e);
    const toque = candidato;
    ativos.delete(e.pointerId);
    if (!toque || toque.pointerId !== e.pointerId) return false;
    candidato = null;
    const duracao = e.timeStamp - toque.timeStamp;
    if (ativos.size || duracao < 0 || duracao > limites.duracaoMaxima) {
      anterior = null;
      return false;
    }
    const primeiro = anterior;
    anterior = { inicio: toque, fim: e.timeStamp };
    if (!primeiro) return false;
    const intervalo = toque.timeStamp - primeiro.fim;
    if (intervalo < limites.intervaloMinimo) {
      anterior = null; // Guarda contra repique e eventos repetidos quase simultâneos.
      return false;
    }
    const distancia = Math.hypot(toque.clientX - primeiro.inicio.clientX, toque.clientY - primeiro.inicio.clientY);
    if (intervalo > limites.intervaloMaximo || distancia > limites.distanciaMaxima
      || e.timeStamp - primeiro.inicio.timeStamp > limites.duracaoTotalMaxima) return false;
    anterior = null; // O terceiro toque inicia outra sequência.
    return true;
  }
  function cancelar(pointerId: number) {
    if (!ativos.delete(pointerId)) return;
    candidato = anterior = null;
  }
  return { baixar, mover, subir, cancelar, limpar };
}
