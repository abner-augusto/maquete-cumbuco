// A cena 3D atrás de uma interface pequena: a UI nunca entra no loop de render (ADR-0001 do espelho).
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { Dados, Lote, Vista } from '../dados';
import { Ceu } from './ceu';

export type Tela = { x: number; y: number };
export type Formato = 'retrato' | 'paisagem';
export interface Cena {
  montar(el: HTMLElement): void;
  inicio(): void;
  enquadrar(id: string): void;              // lote
  selecionar(id: string | null): void;      // realce de seleção
  aproximar(fator: number): void;
  ceu(modo: 'claro' | 'escuro'): void;
  cores(): Record<Lote['tipo'], string>;    // cor de cada tipo, lida dos materiais do GLB (legenda)
  descartar(): void;
}
export interface Opcoes {
  base: URL; dados: Dados;
  aoEscolher(id: string | null): void;            // toque/clique sem arrasto num lote, ou no vazio
  aoPassar(rotulo: { id: string; tela: Tela } | null): void; // hover no desktop
  aoMoverEtiqueta(tela: Tela | null): void;       // topo do lote selecionado
  aoGirar(graus: number): void;                   // rumo da câmera, para a bússola
}

const LOTE = /^Q(\d{2}|[A-Z])L\d{2}$/;
const STATUS: Record<NonNullable<Lote['status']>, string> = { disponivel: '#2E9E5B', reservado: '#E2B021', vendido: '#B0625A' };
// Luz fixa de fim de tarde (spec §5): sol baixo a oeste-noroeste, quente.
const SOL = { azimute: 285, altitude: 24 };

export function loader(base: URL): GLTFLoader {
  const draco = new DRACOLoader().setDecoderPath(new URL('draco/', base).href);
  return new GLTFLoader().setDRACOLoader(draco).setMeshoptDecoder(MeshoptDecoder);
}

/** Direção a partir de azimute (graus do norte, horário) e altura: norte = −Z, leste = +X. */
export function direcao(azimute: number, altura: number): THREE.Vector3 {
  const az = THREE.MathUtils.degToRad(azimute);
  const alt = THREE.MathUtils.degToRad(altura);
  return new THREE.Vector3(Math.sin(az) * Math.cos(alt), Math.sin(alt), -Math.cos(az) * Math.cos(alt));
}

export async function criarCena(o: Opcoes): Promise<Cena> {
  const gltf = loader(o.base);
  const [lot, mar] = await Promise.all([
    gltf.loadAsync(new URL('modelos/loteamento.glb', o.base).href),
    gltf.loadAsync(new URL('modelos/marcos.glb', o.base).href),
  ]);
  const cena = new THREE.Scene();
  cena.add(lot.scene, mar.scene);

  const lotes = new Map<string, THREE.Mesh>();
  lot.scene.traverse(x => { if ((x as THREE.Mesh).isMesh && LOTE.test(x.name)) lotes.set(x.name, x as THREE.Mesh); });
  const porId = new Map(o.dados.lotes.map(l => [l.id, l]));
  // Status, quando o JSON trouxer, pinta o lote com a cor fixa; senão fica a cor do tipo do GLB.
  for (const [id, malha] of lotes) {
    const s = porId.get(id)?.status;
    const m = (malha.material as THREE.MeshStandardMaterial).clone();
    if (s) m.color.set(STATUS[s]);
    malha.material = m;
    malha.userData.base = m;
  }

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  const el = renderer.domElement;
  el.setAttribute('role', 'img');
  el.setAttribute('aria-label', 'Maquete 3D do loteamento; arraste para girar e pince para aproximar');

  const camera = new THREE.PerspectiveCamera(40, 1, 1, 20000);
  const controles = new OrbitControls(camera, el);
  controles.enableDamping = true;
  controles.minDistance = 25;
  controles.maxDistance = 2500;
  controles.maxPolarAngle = Math.PI * 0.47;
  // Toque como no UFCIM-FRONT3D: um dedo gira, dois aproximam e arrastam.
  controles.touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN };

  const ceuLuz = new THREE.HemisphereLight(0xfff3e2, 0x6f6a5c, 1.6);
  const sol = new THREE.DirectionalLight(0xffd2a0, 2.6);
  sol.position.copy(direcao(SOL.azimute, SOL.altitude).multiplyScalar(1000));
  const ceu = new Ceu(15000);
  ceu.sol(direcao(SOL.azimute, SOL.altitude), 0.55, 0);
  cena.add(ceuLuz, sol, ceu.malha);

  // Caixa dos lotes: centro e distância justa da vista inicial.
  const caixa = new THREE.Box3();
  for (const m of lotes.values()) caixa.expandByObject(m);
  const centro = caixa.getCenter(new THREE.Vector3());
  const tamanho = caixa.getSize(new THREE.Vector3());
  const formato = (): 'retrato' | 'paisagem' => (camera.aspect < 1 ? 'retrato' : 'paisagem');
  const PADRAO: Vista = { azimute: 200, elevacao: 35, distancia: 1.1 };
  function distanciaJusta() {
    const v = THREE.MathUtils.degToRad(camera.fov) / 2;
    return Math.max(tamanho.z / (2 * Math.tan(v)), tamanho.x / (2 * Math.tan(v) * camera.aspect));
  }
  function inicio() {
    const { azimute, elevacao, distancia } = o.dados.config.vista?.[formato()] ?? PADRAO;
    controles.target.copy(centro);
    camera.position.copy(centro).addScaledVector(direcao(azimute, elevacao), distanciaJusta() * distancia);
    controles.update();
  }
  function enquadrar(id: string) {
    const m = lotes.get(id);
    if (!m) return;
    abertura = false;
    const alvo = m.getWorldPosition(new THREE.Vector3());
    const rumo = camera.position.clone().sub(controles.target).setY(0).normalize();
    const d = camera.aspect < 1 ? 140 : 100;
    controles.target.copy(alvo);
    camera.position.copy(alvo).addScaledVector(rumo, d * 0.75).setY(alvo.y + d * 0.66);
    controles.update();
  }

  // Realce: hover clareia; seleção pinta com o acento. Material próprio por estado, sem tocar o original.
  const realce = (m: THREE.Mesh, cor: number, forca: number) => {
    const novo = (m.userData.base as THREE.MeshStandardMaterial).clone();
    novo.emissive.set(cor);
    novo.emissiveIntensity = forca;
    m.material = novo;
  };
  const restaurar = (m: THREE.Mesh) => {
    if (m.material !== m.userData.base) (m.material as THREE.Material).dispose();
    m.material = m.userData.base;
  };
  // Desenha só quando algo mudou (câmera, realce, tamanho, céu): parada, a cena não gasta CPU nem bateria.
  let sujo = true;
  let selecionado: string | null = null;
  let passando: string | null = null;
  function aplicarRealces() {
    sujo = true;
    for (const [id, m] of lotes) {
      if (id === selecionado) realce(m, 0x64461d, 0.55);
      else if (id === passando) realce(m, 0xe4c89b, 0.35);
      else restaurar(m);
    }
  }

  const raio = new THREE.Raycaster();
  const alvos = [...lotes.values()];
  function loteEm(x: number, y: number): string | null {
    const r = el.getBoundingClientRect();
    raio.setFromCamera(new THREE.Vector2(((x - r.left) / r.width) * 2 - 1, 1 - ((y - r.top) / r.height) * 2), camera);
    // Só o que está na frente vale: um marco ou o terreno à frente do lote bloqueia.
    const acerto = raio.intersectObjects([...alvos, mar.scene], true)[0];
    return acerto && LOTE.test(acerto.object.name) ? acerto.object.name : null;
  }

  // Toque sem arrasto escolhe; arrasto é câmera (como no espelho).
  let gesto: { id: number; x: number; y: number; moveu: boolean } | null = null;
  const ponteiros = new Set<number>();
  el.addEventListener('pointerdown', e => {
    ponteiros.add(e.pointerId);
    gesto = ponteiros.size === 1 ? { id: e.pointerId, x: e.clientX, y: e.clientY, moveu: false } : null;
  });
  let pendente: PointerEvent | null = null;
  el.addEventListener('pointermove', e => {
    if (gesto && Math.hypot(e.clientX - gesto.x, e.clientY - gesto.y) > 6) gesto.moveu = true;
    if (e.pointerType === 'mouse' && !ponteiros.size) pendente = e; // hover: resolvido no quadro
  });
  el.addEventListener('pointerleave', () => { pendente = null; if (passando) { passando = null; aplicarRealces(); o.aoPassar(null); } });
  el.addEventListener('pointerup', e => {
    ponteiros.delete(e.pointerId);
    const g = gesto;
    gesto = null;
    if (ponteiros.size || !g || g.id !== e.pointerId || g.moveu) return;
    o.aoEscolher(loteEm(e.clientX, e.clientY));
  });
  el.addEventListener('pointercancel', e => { ponteiros.delete(e.pointerId); gesto = null; });
  let abertura = true;
  controles.addEventListener('start', () => (abertura = false));
  controles.addEventListener('change', () => (sujo = true));

  let container: HTMLElement | null = null;
  const redimensionar = new ResizeObserver(() => {
    if (!container) return;
    const { clientWidth: w, clientHeight: h } = container;
    if (!w || !h) return;
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    if (abertura) inicio();
    sujo = true;
  });

  const projetar = (p: THREE.Vector3): Tela | null => {
    const v = p.clone().project(camera);
    if (v.z > 1) return null;
    return { x: ((v.x + 1) / 2) * el.clientWidth, y: ((1 - v.y) / 2) * el.clientHeight };
  };
  let ultimaEtiqueta = '';
  let ultimoRumo = NaN;
  renderer.setAnimationLoop(() => {
    if (!container) return;
    controles.update();
    if (pendente) {
      const e = pendente;
      pendente = null;
      const id = loteEm(e.clientX, e.clientY);
      if (id !== passando) {
        passando = id;
        aplicarRealces();
        const r = el.getBoundingClientRect();
        o.aoPassar(id ? { id, tela: { x: e.clientX - r.left, y: e.clientY - r.top } } : null);
      }
      el.style.cursor = id ? 'pointer' : '';
    }
    if (!sujo) return;
    sujo = false;
    // near acompanha a altura: a placa a 0,25 m do terreno não briga na profundidade de longe.
    const perto = THREE.MathUtils.clamp((camera.position.y - centro.y) * 0.2, 1, 200);
    if (Math.abs(perto - camera.near) > 0.5) { camera.near = perto; camera.updateProjectionMatrix(); }
    ceu.malha.position.copy(camera.position);
    renderer.render(cena, camera);
    const m = selecionado ? lotes.get(selecionado) : undefined;
    const tela = m ? projetar(m.getWorldPosition(new THREE.Vector3())) : null;
    const chave = tela ? `${Math.round(tela.x)},${Math.round(tela.y)}` : '';
    if (chave !== ultimaEtiqueta) { ultimaEtiqueta = chave; o.aoMoverEtiqueta(tela); }
    const d = camera.position.clone().sub(controles.target);
    const rumo = Math.round((THREE.MathUtils.radToDeg(Math.atan2(d.x, -d.z)) + 360) % 360);
    if (rumo !== ultimoRumo) { ultimoRumo = rumo; o.aoGirar(rumo); }
  });

  const corDo = (tipo: Lote['tipo']) => {
    const exemplo = o.dados.lotes.find(l => l.tipo === tipo && !l.status);
    const m = exemplo && lotes.get(exemplo.id);
    return m ? `#${(m.userData.base as THREE.MeshStandardMaterial).color.getHexString()}` : 'transparent';
  };

  return {
    montar(e) { container = e; e.prepend(el); redimensionar.observe(e); sujo = true; },
    inicio() { abertura = true; inicio(); },
    enquadrar,
    selecionar(id) { selecionado = id; aplicarRealces(); },
    aproximar(f) {
      abertura = false;
      const d = camera.position.clone().sub(controles.target).multiplyScalar(f);
      camera.position.copy(controles.target).add(d.setLength(THREE.MathUtils.clamp(d.length(), controles.minDistance, controles.maxDistance)));
      controles.update();
    },
    ceu(modo) { ceu.cor(modo); sujo = true; },
    cores: () => ({ residencial: corDo('residencial'), uso_misto: corDo('uso_misto') }),
    descartar() {
      redimensionar.disconnect();
      renderer.setAnimationLoop(null);
      controles.dispose();
      ceu.descartar();
      renderer.dispose();
      el.remove();
    },
  };
}
