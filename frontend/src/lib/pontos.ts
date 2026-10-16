import type { PontoBruto } from './dados';

export interface Ponto extends PontoBruto { id: number; distante: boolean; maps: string }

export const ROTULO_CATEGORIA: Record<string, string> = {
  compras: 'Compras', hotel: 'Hotel', kitesurf: 'Kitesurf', lagoa: 'Lagoa', lazer: 'Lazer',
  natureza: 'Natureza', orla: 'Orla', porto: 'Porto', praia: 'Praia', saude: 'Saúde',
};

export function prepararPontos(pontos: PontoBruto[]): Ponto[] {
  return [...pontos].sort((a, b) => a.km - b.km).map((p, id) => ({
    ...p, id, distante: p.faixa === 'distante', maps: `https://www.google.com/maps/search/?api=1&query=${p.lat},${p.lon}`,
  }));
}

const um = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 });
export const rotuloKm = (km: number) => `${um.format(km)} km`;
