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

/** Câmera e ponto que ela olha, em metros da cena. */
export interface Pose { posicao: THREE.Vector3; alvo: THREE.Vector3 }

const DURACAO = { minima: 600, maxima: 1400, porMetro: 0.5 };

/** Quanto dura o voo de uma pose à outra, em ms: cresce com o caminho, entre o piso e o teto. */
export function duracaoDoVoo(de: Pose, para: Pose): number {
  const caminho = de.posicao.distanceTo(para.posicao) + de.alvo.distanceTo(para.alvo);
  return THREE.MathUtils.clamp(DURACAO.minima + caminho * DURACAO.porMetro, DURACAO.minima, DURACAO.maxima);
}

/**
 * Pose no instante `t` (0 a 1) do voo de `de` a `para`. O alvo anda em linha reta; a câmera gira
 * em volta dele pelo arco menor, com a elevação e a distância interpoladas: lê-se como uma órbita,
 * e a reta entre as duas posições (que podia mergulhar no terreno) nunca é percorrida. O avanço é
 * um smoothstep: parte e chega devagar.
 */
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
