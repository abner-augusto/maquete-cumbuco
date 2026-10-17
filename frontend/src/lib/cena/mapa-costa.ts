// Distância de cada ponto do mar à terra mais próxima, para a água clarear perto da praia e ter
// espuma na costa. O mapa sai do próprio terreno do entorno: uma vista de cima, uma vez, marca o
// que está acima do nível do mar; a distância vem de um chanfro de duas passadas na CPU.
import * as THREE from 'three';

/** Além desta distância (m) a água é funda: o mapa não precisa guardar mais. */
export const ALCANCE_COSTA = 6000;
const LADO = 2048;
const CAMADA = 7;
const RAIZ2 = Math.SQRT2;

/**
 * Distância, em metros, de cada célula à terra mais próxima (0 na própria terra). Chanfro 1/√2
 * em duas passadas: erro de poucos por cento, de sobra para uma faixa de água de centenas de metros.
 * Sem terra nenhuma, tudo fica em `Infinity`.
 */
export function distanciaAteATerra(terra: Uint8Array, n: number, passo: number): Float32Array {
  const d = new Float32Array(n * n);
  for (let i = 0; i < d.length; i++) d[i] = terra[i] ? 0 : Infinity;
  const ve = (x: number, y: number, custo: number, i: number) => {
    if (x < 0 || y < 0 || x >= n || y >= n) return;
    const c = d[y * n + x]! + custo;
    if (c < d[i]!) d[i] = c;
  };
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      const i = y * n + x;
      ve(x - 1, y, 1, i); ve(x - 1, y - 1, RAIZ2, i); ve(x, y - 1, 1, i); ve(x + 1, y - 1, RAIZ2, i);
    }
  }
  for (let y = n - 1; y >= 0; y--) {
    for (let x = n - 1; x >= 0; x--) {
      const i = y * n + x;
      ve(x + 1, y, 1, i); ve(x + 1, y + 1, RAIZ2, i); ve(x, y + 1, 1, i); ve(x - 1, y + 1, RAIZ2, i);
    }
  }
  for (let i = 0; i < d.length; i++) d[i] = d[i]! * passo;
  return d;
}

/** Um byte por célula, em raiz da distância: fino na praia, onde a espuma precisa, e filtrável pela GPU. */
export function codificarDistancia(d: Float32Array, max: number): Uint8Array {
  const out = new Uint8Array(d.length);
  for (let i = 0; i < d.length; i++) out[i] = Math.round(Math.sqrt(Math.min(d[i]! / max, 1)) * 255);
  return out;
}

export interface MapaCosta {
  textura: THREE.DataTexture;
  /** Centro (x, z do mundo) e meio lado do quadrado coberto, em metros. */
  caixa: THREE.Vector3;
  max: number;
}

const alturaVert = /* glsl */ `
  varying float vAltura;
  void main() {
    vec4 mundo = modelMatrix * vec4(position, 1.0);
    vAltura = mundo.y;
    gl_Position = projectionMatrix * viewMatrix * mundo;
  }
`;
const alturaFrag = /* glsl */ `
  uniform float uNivel;
  varying float vAltura;
  void main() { gl_FragColor = vec4(vec3(step(uNivel, vAltura)), 1.0); }
`;

/**
 * Uma vista de cima, ortográfica, do `terreno` num quadrado de lado `2 * meio` em volta de `centro`,
 * com `material` no lugar do de cada malha. Devolve os pixels RGBA, a linha 0 ao sul (+z).
 */
function vistaDeCima(renderer: THREE.WebGLRenderer, cena: THREE.Scene, terreno: THREE.Object3D[], centro: THREE.Vector3, nivel: number, meio: number, material: THREE.ShaderMaterial): Uint8Array {
  const alvo = new THREE.WebGLRenderTarget(LADO, LADO, { minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter });
  const camera = new THREE.OrthographicCamera(-meio, meio, meio, -meio, 1, 20000);
  // De cima, com o norte (−z) para cima na imagem: x do mundo vai para a direita, z para baixo.
  camera.up.set(0, 0, -1);
  camera.position.set(centro.x, nivel + 10000, centro.z);
  camera.lookAt(centro.x, nivel, centro.z);
  camera.layers.set(CAMADA);
  for (const t of terreno) t.traverse(o => o.layers.enable(CAMADA));

  const antes = { alvo: renderer.getRenderTarget(), cor: renderer.getClearColor(new THREE.Color()), alfa: renderer.getClearAlpha(), sobre: cena.overrideMaterial, nevoa: cena.fog };
  renderer.setRenderTarget(alvo);
  renderer.setClearColor(0x000000, 1);
  cena.overrideMaterial = material;
  cena.fog = null;
  renderer.clear();
  renderer.render(cena, camera);
  cena.overrideMaterial = antes.sobre;
  cena.fog = antes.nevoa;
  renderer.setRenderTarget(antes.alvo);
  renderer.setClearColor(antes.cor, antes.alfa);

  const pixels = new Uint8Array(LADO * LADO * 4);
  renderer.readRenderTargetPixels(alvo, 0, 0, LADO, LADO, pixels);
  alvo.dispose();
  material.dispose();
  for (const t of terreno) t.traverse(o => o.layers.disable(CAMADA));
  return pixels;
}

const cotaFrag = /* glsl */ `
  varying float vAltura;
  void main() {
    float cm = floor(clamp(vAltura, 0.0, 655.0) * 100.0 + 0.5);
    gl_FragColor = vec4(floor(cm / 256.0) / 255.0, mod(cm, 256.0) / 255.0, 0.0, 1.0);
  }
`;

/**
 * Cota do terreno (m, ao menos 0) em (x, z do mundo), lida de uma vista de cima feita uma vez; vale
 * dentro do quadrado de meio lado `meio` em volta de `centro` e devolve a maior cota de um raio de
 * `folga` pixels. Barata o bastante para amostrar os anéis de distância de 16 em 16 metros.
 */
export function mapaDeCotas(renderer: THREE.WebGLRenderer, cena: THREE.Scene, terreno: THREE.Object3D[], centro: THREE.Vector3, meio: number, folga = 3): (x: number, z: number) => number {
  const material = new THREE.ShaderMaterial({ vertexShader: alturaVert, fragmentShader: cotaFrag, side: THREE.DoubleSide });
  const pixels = vistaDeCima(renderer, cena, terreno, centro, 0, meio, material);
  return (x, z) => {
    const c = Math.round(((x - centro.x + meio) / (2 * meio)) * LADO - 0.5);
    const l = Math.round(((centro.z + meio - z) / (2 * meio)) * LADO - 0.5);
    let topo = 0;
    for (let dl = -folga; dl <= folga; dl++) {
      for (let dc = -folga; dc <= folga; dc++) {
        const cc = Math.min(Math.max(c + dc, 0), LADO - 1);
        const ll = Math.min(Math.max(l + dl, 0), LADO - 1);
        const i = (ll * LADO + cc) * 4;
        topo = Math.max(topo, (pixels[i]! * 256 + pixels[i + 1]!) / 100);
      }
    }
    return topo;
  };
}

/**
 * Mapa da costa num quadrado de lado `2 * meio` em volta de `centro`. `terreno` são as malhas do
 * entorno detalhado; `nivel` é a cota do mar. Renderiza uma vez e devolve a textura.
 */
export function mapaDaCosta(renderer: THREE.WebGLRenderer, cena: THREE.Scene, terreno: THREE.Object3D[], centro: THREE.Vector3, nivel: number, meio: number): MapaCosta {
  const material = new THREE.ShaderMaterial({ uniforms: { uNivel: { value: nivel + 0.1 } }, vertexShader: alturaVert, fragmentShader: alturaFrag, side: THREE.DoubleSide });
  const pixels = vistaDeCima(renderer, cena, terreno, centro, nivel, meio, material);

  const terra = new Uint8Array(LADO * LADO);
  for (let i = 0; i < terra.length; i++) terra[i] = pixels[i * 4]! > 127 ? 1 : 0;
  if (!terra.includes(1)) console.warn('mapa da costa sem terra: nada acima do nível do mar', nivel);
  const dados = codificarDistancia(distanciaAteATerra(terra, LADO, (2 * meio) / LADO), ALCANCE_COSTA);
  const textura = new THREE.DataTexture(dados, LADO, LADO, THREE.RedFormat, THREE.UnsignedByteType);
  textura.minFilter = textura.magFilter = THREE.LinearFilter;
  textura.generateMipmaps = false;
  textura.unpackAlignment = 1;
  textura.needsUpdate = true;
  return { textura, caixa: new THREE.Vector3(centro.x, centro.z, meio), max: ALCANCE_COSTA };
}
