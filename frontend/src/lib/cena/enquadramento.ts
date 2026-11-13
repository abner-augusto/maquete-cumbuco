import * as THREE from 'three';

// Rumo em graus do norte, horário. No glTF, norte é −z e leste é +x.
export function vistaDeFrente(alvo: THREE.Vector3, rumo: number, distancia: number, elevacao: number): THREE.Vector3 {
  const az = THREE.MathUtils.degToRad(rumo);
  const el = THREE.MathUtils.degToRad(elevacao);
  const dir = new THREE.Vector3(Math.sin(az) * Math.cos(el), Math.sin(el), -Math.cos(az) * Math.cos(el));
  return alvo.clone().addScaledVector(dir, distancia);
}

export interface Pose { posicao: THREE.Vector3; alvo: THREE.Vector3 }

const DURACAO = { minima: 600, maxima: 1400, porMetro: 0.5 };

export function duracaoDoVoo(de: Pose, para: Pose): number {
  const caminho = de.posicao.distanceTo(para.posicao) + de.alvo.distanceTo(para.alvo);
  return THREE.MathUtils.clamp(DURACAO.minima + caminho * DURACAO.porMetro, DURACAO.minima, DURACAO.maxima);
}

export function poseDoVoo(de: Pose, para: Pose, t: number): Pose {
  const s = THREE.MathUtils.smoothstep(t, 0, 1);
  const a = new THREE.Spherical().setFromVector3(de.posicao.clone().sub(de.alvo));
  const b = new THREE.Spherical().setFromVector3(para.posicao.clone().sub(para.alvo));
  let giro = b.theta - a.theta;
  if (giro > Math.PI) giro -= 2 * Math.PI;
  if (giro < -Math.PI) giro += 2 * Math.PI;
  const esf = new THREE.Spherical(
    THREE.MathUtils.lerp(a.radius, b.radius, s),
    THREE.MathUtils.lerp(a.phi, b.phi, s),
    a.theta + giro * s,
  );
  const alvo = de.alvo.clone().lerp(para.alvo, s);
  return { posicao: alvo.clone().add(new THREE.Vector3().setFromSpherical(esf)), alvo };
}
