import type { Config, Lote } from './dados';

const norm = (s: string) => s.trim().toUpperCase();
/** "07" e "7" são a mesma quadra; "H" fica "H". */
const quadra = (s: string) => (/^\d+$/.test(s) ? s.padStart(2, '0') : s);

/** Quadra e lote em qualquer formato que o corretor digita: "7 4", "Q7L4", "q07 l04", "07-04". */
export function buscar(lotes: Lote[], termo: string): Lote[] {
  const m = norm(termo).match(/^Q?\s*([0-9]{1,2}|[A-Z])(?:\s*[-\s]\s*|\s*L\s*)?([0-9]{1,2})?$/);
  if (!m) return [];
  const q = quadra(m[1]!);
  const n = m[2]?.padStart(2, '0');
  return lotes.filter(l => l.quadra === q && (!n || l.lote === n)).sort((a, b) => a.id.localeCompare(b.id));
}

export function loteDaUrl(lotes: Lote[], busca: string): Lote | null {
  const id = new URLSearchParams(busca).get('lote');
  return id ? lotes.find(l => l.id === norm(id)) ?? null : null;
}

export function precosVisiveis(config: Pick<Config, 'mostrarPrecos'>, busca: string): boolean {
  return config.mostrarPrecos && new URLSearchParams(busca).get('precos') !== '0';
}

export const rotuloCurto = (l: Lote) => `Q${l.quadra} · L${l.lote}`;
export const rotuloLongo = (l: Lote) => `Quadra ${l.quadra} · Lote ${l.lote}`;
export const ROTULO_TIPO: Record<Lote['tipo'], string> = { residencial: 'Residencial', uso_misto: 'Uso misto' };

const n2 = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
export const metros = (n: number) => `${n2.format(n)} m`;
export const formatarArea = (n: number) => `${n2.format(n)} m²`;
export const reais = (n: number) => n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });
