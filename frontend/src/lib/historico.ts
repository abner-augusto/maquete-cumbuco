export type Batente = 'some' | 'espiar' | 'cheia';
export type Conteudo = 'busca' | 'ficha' | 'boas-vindas' | 'marco' | 'entorno' | 'ponto';

export interface ImagemAmpliada { src: string; alt: string }

export interface EstadoNavegacao {
  conteudo: Conteudo;
  batente: Batente;
  selecionado: string | null;
  marcoAberto: string | null;
  pontoSelecionado: number | null;
  consulta: string;
  cinema: boolean;
  rolagem: number;
  imagem: ImagemAmpliada | null;
}
interface Entrada {
  maquete: 1;
  indice: number;
  fecharEm: number;
  expansao?: boolean;
  estado: EstadoNavegacao;
}
type Historico = Pick<History, 'state' | 'pushState' | 'replaceState' | 'go'>;

export function estadoInicial(): EstadoNavegacao {
  return { conteudo: 'busca', batente: 'some', selecionado: null, marcoAberto: null,
    pontoSelecionado: null, consulta: '', cinema: false, rolagem: 0, imagem: null };
}

function entrada(valor: unknown): valor is Entrada {
  const e = valor as Entrada | null;
  return e?.maquete === 1 && Number.isInteger(e.indice) && Number.isInteger(e.fecharEm)
    && e.indice >= 0 && e.fecharEm >= 0 && e.fecharEm <= e.indice
    && !!e.estado && ['busca', 'ficha', 'boas-vindas', 'marco', 'entorno', 'ponto'].includes(e.estado.conteudo)
    && ['some', 'espiar', 'cheia'].includes(e.estado.batente);
}

/** A restauração aplica o retrato completo e nunca escreve no histórico. */
export function criarHistorico(historico: Historico, endereco: () => string,
  ler: () => EstadoNavegacao, aplicar: (estado: EstadoNavegacao) => void) {
  let pendente = false;
  function url(estado: EstadoNavegacao) {
    const u = new URL(endereco());
    if (estado.conteudo === 'ficha' && estado.selecionado) u.searchParams.set('lote', estado.selecionado);
    else u.searchParams.delete('lote');
    return u.href;
  }
  function restaurar(valor: unknown) {
    pendente = false;
    aplicar(structuredClone(entrada(valor) ? { ...estadoInicial(), ...valor.estado } : estadoInicial()));
  }
  function iniciar() {
    if (entrada(historico.state)) {
      restaurar(historico.state);
      return true;
    }
    const estado = ler();
    historico.replaceState({ maquete: 1, indice: 0, fecharEm: 0, estado }, '', url(estado));
    return false;
  }
  function navegar(estado: EstadoNavegacao, expansao = false) {
    if (pendente) return;
    const atual = historico.state as Entrada;
    // Salva consulta e rolagem no ponto de saída, sem criar uma entrada por tecla ou pixel.
    historico.replaceState({ ...atual, estado: ler() }, '', endereco());
    const proxima: Entrada = { maquete: 1, indice: atual.indice + 1,
      fecharEm: expansao ? atual.fecharEm : atual.indice, expansao, estado };
    historico.pushState(proxima, '', url(estado));
    aplicar(structuredClone(estado));
  }
  function substituir(estado: EstadoNavegacao) {
    if (pendente || !entrada(historico.state)) return;
    historico.replaceState({ ...historico.state, estado }, '', url(estado));
    aplicar(structuredClone(estado));
  }
  function voltar() {
    if (pendente || !entrada(historico.state) || historico.state.indice === 0) return;
    pendente = true;
    historico.go(-1);
  }
  function fechar() {
    if (pendente || !entrada(historico.state)) return;
    const { indice, fecharEm } = historico.state;
    if (indice > fecharEm) {
      pendente = true;
      historico.go(fecharEm - indice);
    }
  }
  return { iniciar, navegar, substituir, restaurar, voltar, fechar };
}
