export const midia = (foto: string, tamanho: 'mini' | 'cheia') =>
  `dados/${foto.replace(/\.[^.]+$/, '')}${tamanho === 'mini' ? '-mini' : ''}.webp`;
