import { expect, test } from 'vitest';
import { midia } from './midia';

test('foto do JSON vira o WebP do tamanho pedido', () => {
  expect(midia('marcos/clube/01.jpg', 'mini')).toBe('dados/marcos/clube/01-mini.webp');
  expect(midia('marcos/estande/planta.jpg', 'cheia')).toBe('dados/marcos/estande/planta.webp');
});
