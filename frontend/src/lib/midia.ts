/** Foto citada no JSON (relativa a dados/) → WebP gerado pelo copiar-assets. */
export const midia = (foto: string, tamanho: 'mini' | 'cheia') =>
  `dados/${foto.replace(/\.[^.]+$/, '')}${tamanho === 'mini' ? '-mini' : ''}.webp`;
