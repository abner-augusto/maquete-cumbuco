import { describe, expect, it } from 'vitest';
import { criarHistorico, estadoInicial, type EstadoNavegacao } from './historico';

function ambiente() {
  let estado = estadoInicial();
  let indice = 0;
  const entradas: { state: unknown; url: string }[] = [{ state: null, url: 'https://maquete.test/?precos=0&dev#vista' }];
  const historico = {
    get state() { return entradas[indice]!.state; },
    replaceState(state: unknown, _: string, url?: string | URL | null) {
      entradas[indice] = { state: structuredClone(state), url: url?.toString() ?? entradas[indice]!.url };
    },
    pushState(state: unknown, _: string, url?: string | URL | null) {
      entradas.splice(indice + 1);
      entradas.push({ state: structuredClone(state), url: url!.toString() });
      indice++;
    },
    go(delta: number) { indice += delta; nav.restaurar(historico.state); },
  };
  const nav = criarHistorico(historico, () => entradas[indice]!.url, () => estado, proximo => { estado = proximo; });
  nav.iniciar();
  const abrir = (parcial: Partial<EstadoNavegacao>) => nav.navegar({ ...estado, ...parcial });
  return { nav, historico, entradas, abrir, ler: () => estado, mudarConsulta: (consulta: string) => { estado.consulta = consulta; } };
}

describe('navegação da maquete', () => {
  it('restaura a ficha de destino mesmo quando a atual está cheia', () => {
    const a = ambiente();
    a.abrir({ conteudo: 'ficha', selecionado: 'A', batente: 'cheia' });
    a.abrir({ selecionado: 'B' });
    a.historico.go(-1);
    expect(a.ler().selecionado).toBe('A');
    expect(a.ler().batente).toBe('cheia');
    a.historico.go(1);
    expect(a.ler().selecionado).toBe('B');
    expect(a.entradas).toHaveLength(3);
  });
  it('preserva a ficha ao abrir galeria e desliga cinema ao voltar', () => {
    const a = ambiente();
    a.abrir({ conteudo: 'ficha', selecionado: 'A', batente: 'espiar' });
    a.abrir({ conteudo: 'marco', selecionado: null, marcoAberto: 'clube' });
    a.abrir({ cinema: true, batente: 'some' });
    a.nav.fechar();
    expect(a.ler()).toMatchObject({ cinema: false, conteudo: 'marco' });
    a.nav.fechar();
    expect(a.ler()).toMatchObject({ conteudo: 'ficha', selecionado: 'A' });
  });
  it('voltar e avançar restauram o batente; fechar pula só a expansão', () => {
    const a = ambiente();
    a.abrir({ conteudo: 'busca', batente: 'espiar' });
    a.mudarConsulta('7 4');
    a.abrir({ conteudo: 'ficha', selecionado: 'A' });
    a.nav.navegar({ ...a.ler(), batente: 'cheia' }, true);
    a.historico.go(-1);
    expect(a.ler().batente).toBe('espiar');
    a.historico.go(1);
    expect(a.ler().batente).toBe('cheia');
    a.nav.fechar();
    expect(a.ler()).toMatchObject({ conteudo: 'busca', consulta: '7 4' });
  });
  it('preserva preços, parâmetros e fragmento em todas as entradas', () => {
    const a = ambiente();
    a.abrir({ conteudo: 'ficha', selecionado: 'A' });
    a.abrir({ conteudo: 'marco', selecionado: null });
    for (const e of a.entradas) {
      const url = new URL(e.url);
      expect(url.searchParams.get('precos')).toBe('0');
      expect(url.searchParams.has('dev')).toBe(true);
      expect(url.hash).toBe('#vista');
    }
    expect(new URL(a.entradas[1]!.url).searchParams.get('lote')).toBe('A');
    expect(new URL(a.entradas[2]!.url).searchParams.has('lote')).toBe(false);
  });
  it('inicializa uma entrada base e não repete entradas ao recarregar', () => {
    const a = ambiente();
    a.abrir({ conteudo: 'ficha', selecionado: 'A' });
    expect(a.nav.iniciar()).toBe(true);
    expect(a.entradas).toHaveLength(2);
  });
});
