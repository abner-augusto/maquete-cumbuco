import { describe, expect, test } from 'vitest';
import { cameraDaUrl, linkDaCamera, modoDev } from './dev';

describe('modo dev', () => {
  test('liga com ?dev', () => {
    expect(modoDev('?dev')).toBe(true);
    expect(modoDev('?lote=Q07L04&dev=1')).toBe(true);
    expect(modoDev('?lote=Q07L04')).toBe(false);
  });

  test('o link da câmera volta como a mesma câmera', () => {
    const c = { posicao: [120.04, 85.5, -340.26], alvo: [10, 21, -30.5], entorno: true };
    const link = linkDaCamera('http://127.0.0.1:4173/?lote=Q07L04', c);
    expect(link).toBe('http://127.0.0.1:4173/?dev&entorno=1&cam=120,85.5,-340.3,10,21,-30.5');
    expect(cameraDaUrl(new URL(link).search)).toEqual({ posicao: [120, 85.5, -340.3], alvo: [10, 21, -30.5], entorno: true });
  });

  test('cam inválida é ignorada', () => {
    expect(cameraDaUrl('?cam=1,2,3')).toBeNull();
    expect(cameraDaUrl('?cam=a,b,c,d,e,f')).toBeNull();
    expect(cameraDaUrl('?dev')).toBeNull();
  });
});
