export interface Lote { id: string; quadra: string; lote: string; tipo: 'residencial' | 'uso_misto'; area_m2: number;
  lados_m: number[]; frente_m: number | null; frente_rumo?: number | null; poligono: [number, number][]; inscricao_iptu?: string;
  preco_total?: number; preco_m2?: number; status?: 'disponivel' | 'reservado' | 'vendido' }
export interface Config { mostrarPrecos: boolean; tabelaPrecos: { nome: string; referencia: string };
  vista: Partial<Record<'retrato' | 'paisagem', Vista>>; estande: { altura_m: number } }
export interface Vista { azimute: number; elevacao: number; distancia: number }
export interface Foto { foto: string; legenda: string }
export interface Marco { id: string; nome: string; x: number; y: number; z: number; objeto: string | null;
  galeria: Foto[]; planta: string | null; lat: number; lon: number; pegada?: [number, number][] }
export interface PontoBruto { nome: string; categoria: string; lat: number; lon: number; x: number; y: number;
  km: number; minutos_carro: number; faixa: 'proximo' | 'distante'; foto: string | null; credito: string | null;
  licenca: string | null; licenca_url: string | null; fonte_foto: string | null }
/** Uma fase do projeto: o centro dela, em metros da origem da maquete (x leste, y norte). */
export interface Fase { id: number; nome: string; x: number; y: number }
export interface Dados { lotes: Lote[]; marcos: Marco[]; pontos: PontoBruto[]; fontesPontos: string; fases: Fase[]; config: Config }

export async function carregarDados(base: URL): Promise<Dados> {
  const json = async <T>(n: string): Promise<T> => {
    const r = await fetch(new URL(`dados/${n}`, base));
    if (!r.ok) throw Error(`dados/${n}`);
    return r.json() as Promise<T>;
  };
  const [lotes, marcos, pontos, fases, config] = await Promise.all([
    json<{ lotes: Lote[] }>('lotes.json'), json<{ marcos: Marco[] }>('marcos.json'),
    json<{ pontos: PontoBruto[]; fontes: string }>('pontos.json'), json<{ fases: Fase[] }>('fases.json'), json<Config>('config.json'),
  ]);
  return { lotes: lotes.lotes, marcos: marcos.marcos, pontos: pontos.pontos, fontesPontos: pontos.fontes, fases: fases.fases, config };
}
