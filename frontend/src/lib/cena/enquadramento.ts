import * as THREE from 'three';

/**
 * Posição da câmera que olha o lote de frente: do lado da rua (`rumo`, graus do norte, horário),
 * à `distancia` do alvo e `elevacao` graus acima do horizonte. No glTF, norte é −z e leste é +x.
 */
export function vistaDeFrente(alvo: THREE.Vector3, rumo: number, distancia: number, elevacao: number): THREE.Vector3 {
  const az = THREE.MathUtils.degToRad(rumo);
  const el = THREE.MathUtils.degToRad(elevacao);
  const dir = new THREE.Vector3(Math.sin(az) * Math.cos(el), Math.sin(el), -Math.cos(az) * Math.cos(el));
  return alvo.clone().addScaledVector(dir, distancia);
}
