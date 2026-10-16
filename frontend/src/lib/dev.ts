// Modo dev (?dev): um botão copia o link com a câmera exata, para reproduzir e depurar o que se viu.
// O link abre o mesmo quadro: ?dev&entorno=1&cam=px,py,pz,ax,ay,az (posição e alvo, em metros da cena).

export interface CameraDev {
  posicao: number[];
  alvo: number[];
  entorno: boolean;
}

export const modoDev = (busca: string) => new URLSearchParams(busca).has('dev');

const dec = (n: number) => String(Math.round(n * 10) / 10);

export function linkDaCamera(href: string, c: CameraDev): string {
  const url = new URL(href);
  // Escrito à mão: URLSearchParams trocaria as vírgulas por %2C e o "dev" por "dev=".
  url.search = `?dev${c.entorno ? '&entorno=1' : ''}&cam=${[...c.posicao, ...c.alvo].map(dec).join(',')}`;
  return url.href;
}

export function cameraDaUrl(busca: string): CameraDev | null {
  const p = new URLSearchParams(busca);
  const n = (p.get('cam') ?? '').split(',').map(Number);
  if (n.length !== 6 || n.some(v => !Number.isFinite(v))) return null;
  return { posicao: n.slice(0, 3), alvo: n.slice(3), entorno: p.get('entorno') === '1' };
}
