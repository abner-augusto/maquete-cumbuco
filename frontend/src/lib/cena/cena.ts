// A cena 3D atrás de uma interface pequena: a UI nunca entra no loop de render (ADR-0001 do espelho).
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { Dados, Lote, Vista } from '../dados';
import type { Ponto } from '../pontos';
import { Ceu } from './ceu';
import { Entorno } from './entorno';
import { vistaDeFrente } from './enquadramento';
import { COR_AGUA, materialDaAgua, quadroDaAgua } from './agua';

export type Tela = { x: number; y: number };
export type Formato = 'retrato' | 'paisagem';

/** Quanto um marcador pode sair da tela antes de sumir: é a faixa em que ele esmaece. */
export const MARGEM_FADE = 48;

/**
 * Onde cada coisa do entorno cai na tela, em pixels. Ponto perto: a posição, ou `null` além de
 * `MARGEM_FADE` fora da tela. Ponto distante: o rumo na tela (radianos, y para baixo) e a posição
 * real quando ela cai dentro da tela.
 */
export interface QuadroEntorno {
  origem: Tela;
  /** Distância da câmera ao alvo, em metros: de perto, as setas da borda saem. */
  alcance: number;
  pontos: (Tela | { angulo: number; tela: Tela | null } | null)[];
  aneis: { raio: number; tela: Tela | null }[];
}
export interface Cena {
  montar(el: HTMLElement): void;
  inicio(): void;
  enquadrar(id: string): void;              // lote
  enquadrarMarco(id: string): void;
  selecionar(id: string | null): void;      // realce de seleção
  aproximar(fator: number): void;
  /** Modo dev: posição e alvo da câmera (metros da cena), para copiar e para reabrir o mesmo quadro. */
  camera(): { posicao: number[]; alvo: number[] };
  irPara(posicao: number[], alvo: number[]): void;
  ceu(modo: 'claro' | 'escuro'): void;
  /** Liga o entorno (carrega na primeira vez) com os pontos de referência, ou desliga. */
  entorno(ativo: boolean, pontos: Ponto[]): Promise<void>;
  cores(): Record<Lote['tipo'], string>;    // cor de cada tipo, lida dos materiais do GLB (legenda)
  descartar(): void;
}
export interface Opcoes {
  base: URL; dados: Dados;
  aoEscolher(id: string | null): void;            // toque/clique sem arrasto num lote, ou no vazio
  aoPassar(rotulo: { id: string; tela: Tela } | null): void; // hover no desktop
  aoMoverEtiqueta(tela: Tela | null): void;       // topo do lote selecionado
  aoGirar(graus: number): void;                   // rumo da câmera, para a bússola
  aoMoverEntorno(q: QuadroEntorno | null): void;
  /** Fração da vegetação desenhada (0 a 1), pela faixa do aparelho. */
  vegetacao: number;
  aoMoverMarcos(telas: { id: string; tela: Tela | null }[]): void; // âncora do ícone de cada marco
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

  // Estande: não tem modelo; o volume simplificado é a pegada do KMZ extrudada (spec §7.1).
  const volumes = new THREE.Group();
  for (const m of o.dados.marcos) {
    if (m.objeto || !m.pegada) continue;
    const forma = new THREE.Shape(m.pegada.map(([x, y]) => new THREE.Vector2(x, y)));
    const g = new THREE.ExtrudeGeometry(forma, { depth: o.dados.config.estande.altura_m, bevelEnabled: false }).rotateX(-Math.PI / 2);
    const volume = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: 0xe9e2d6, roughness: 0.9 }));
    volume.position.y = m.z;
    volume.name = `Marco_${m.id}`;
    volumes.add(volume);
  }
  cena.add(volumes);
  // Ícone flutuante: 12 m acima do ponto do marco.
  const ancoras = o.dados.marcos.map(m => ({ id: m.id, p: new THREE.Vector3(m.x, m.z + 12, -m.y) }));

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
  // Lote: de frente para a rua, em ângulo fixo e a uma distância que mostra os vizinhos.
  const LOTE_ELEVACAO = 35;
  function enquadrar(id: string) {
    const m = lotes.get(id);
    if (!m) return;
    const alvo = new THREE.Box3().setFromObject(m).getCenter(new THREE.Vector3());
    const rumo = porId.get(id)?.frente_rumo;
    if (rumo == null) return mirar(alvo, camera.aspect < 1 ? 140 : 100);
    abertura = false;
    controles.target.copy(alvo);
    camera.position.copy(vistaDeFrente(alvo, rumo, camera.aspect < 1 ? 190 : 140, LOTE_ELEVACAO));
    controles.update();
  }
  function enquadrarMarco(id: string) {
    const m = o.dados.marcos.find(x => x.id === id);
    if (m) mirar(new THREE.Vector3(m.x, m.z, -m.y), 160);
  }
  /** Leva a câmera para perto do alvo, mantendo o rumo atual. */
  function mirar(alvo: THREE.Vector3, d: number) {
    abertura = false;
    const rumo = camera.position.clone().sub(controles.target).setY(0).normalize();
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
    const acerto = raio.intersectObjects([...alvos, mar.scene, volumes], true)[0];
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
  // O three refaz o contexto perdido (celular em segundo plano); a cena parada precisa redesenhar.
  el.addEventListener('webglcontextrestored', () => (sujo = true));

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
  /** Como `projetar`, mas atrás da câmera devolve um ponto bem fora da tela na direção certa (a UI prende à borda). */
  const projetarSempre = (p: THREE.Vector3): Tela => {
    const v = p.clone().project(camera);
    const k = v.z > 1 ? -1000 : 1;
    return { x: ((v.x * k + 1) / 2) * el.clientWidth, y: ((1 - v.y * k) / 2) * el.clientHeight };
  };
  // O mar do entorno anima as ondas: único caso em que a cena desenha sem pedido (a ~24 quadros/s).
  const agua = materialDaAgua(ceu.coresAgua());
  const movimentoReduzido = matchMedia('(prefers-reduced-motion: reduce)');
  movimentoReduzido.addEventListener('change', () => (sujo = true));
  let ultimaAgua = 0;
  let ultimaEtiqueta = '';
  let ultimoRumo = NaN;
  let ultimosMarcos = '';
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
    const agora = performance.now();
    if (quadroDaAgua({ entorno: entornoAtivo(), reduzido: movimentoReduzido.matches, agora, ultimo: ultimaAgua })) {
      ultimaAgua = agora;
      agua.uniforms.uTempo.value = agora / 1000;
      sujo = true;
    }
    if (!sujo) return;
    sujo = false;
    // near acompanha a altura: a placa a 0,25 m do terreno não briga na profundidade de longe.
    const perto = THREE.MathUtils.clamp((camera.position.y - centro.y) * 0.2, 1, 200);
    if (Math.abs(perto - camera.near) > 0.5) { camera.near = perto; camera.updateProjectionMatrix(); }
    if (entornoAtivo()) {
      // A borda do entorno some na névoa, na cor do solo do céu.
      const alcance = camera.position.distanceTo(controles.target);
      nevoa.near = alcance * 0.9 + 600;
      nevoa.far = alcance + 5000;
      nevoa.color.copy(ceu.corSolo());
    }
    ceu.malha.position.copy(camera.position);
    renderer.render(cena, camera);
    const m = selecionado ? lotes.get(selecionado) : undefined;
    const tela = m ? projetar(m.getWorldPosition(new THREE.Vector3())) : null;
    const chave = tela ? `${Math.round(tela.x)},${Math.round(tela.y)}` : '';
    if (chave !== ultimaEtiqueta) { ultimaEtiqueta = chave; o.aoMoverEtiqueta(tela); }
    const d = camera.position.clone().sub(controles.target);
    const rumo = Math.round((THREE.MathUtils.radToDeg(Math.atan2(d.x, -d.z)) + 360) % 360);
    if (rumo !== ultimoRumo) { ultimoRumo = rumo; o.aoGirar(rumo); }
    const marcos = ancoras.map(a => ({ id: a.id, tela: projetarSempre(a.p) }));
    const chaveMarcos = marcos.map(x => (x.tela ? `${Math.round(x.tela.x)},${Math.round(x.tela.y)}` : '-')).join(';');
    if (chaveMarcos !== ultimosMarcos) { ultimosMarcos = chaveMarcos; o.aoMoverMarcos(marcos); }
    if (entornoAtivo() && pontosEntorno.length) {
      const quadro = quadroEntorno();
      const chaveEntorno = JSON.stringify(quadro);
      if (chaveEntorno !== ultimoEntorno) { ultimoEntorno = chaveEntorno; o.aoMoverEntorno(quadro); }
    }
  });

  // ---- entorno ----
  const RAIOS = [1000, 3000];
  let entorno: Entorno | null = null;
  let carregandoEntorno: Promise<Entorno> | null = null;
  let pedidoEntorno = 0;
  let pontosEntorno: { p: Ponto; posicao: THREE.Vector3 }[] = [];
  let ultimoEntorno = '';
  const nevoa = new THREE.Fog(0xffffff, 1000, 6000);
  const entornoAtivo = () => entorno?.grupo.visible === true;

  async function mostrarEntorno(ativo: boolean, pontos: Ponto[]) {
    const pedido = ++pedidoEntorno;
    if (!ativo) {
      if (entorno) entorno.grupo.visible = false;
      pontosEntorno = [];
      cena.fog = null;
      controles.maxDistance = 2500;
      ultimoEntorno = '';
      o.aoMoverEntorno(null);
      abertura = true;
      inicio();
      sujo = true;
      return;
    }
    carregandoEntorno ??= Entorno.carregar(gltf, o.base, centro, RAIOS, o.vegetacao);
    try {
      entorno = await carregandoEntorno;
    } catch (erro) {
      carregandoEntorno = null;
      throw erro;
    }
    // Desligado enquanto carregava: fica carregado, mas escondido.
    if (pedido !== pedidoEntorno) return;
    if (!entorno.grupo.parent) {
      const mar = entorno.grupo.getObjectByName('Mar') as THREE.Mesh | undefined;
      if (mar) { (mar.material as THREE.Material).dispose(); mar.material = agua; }
      cena.add(entorno.grupo);
    }
    entorno.grupo.visible = true;
    // A cota de cada ponto vem do terreno do entorno, uma vez.
    const e = entorno;
    pontosEntorno = pontos.map(p => ({ p, posicao: new THREE.Vector3(p.x, e.cotaEm(p.x, p.y), -p.y) }));
    cena.fog = nevoa;
    controles.maxDistance = 9000;
    // Do alto, pelo mesmo rumo de agora, com o anel de 3 km inteiro na largura da tela.
    abertura = false;
    const rumo = camera.position.clone().sub(controles.target).setY(0);
    if (rumo.lengthSq() < 1e-6) rumo.set(0, 0, 1);
    rumo.normalize();
    const elevacao = THREE.MathUtils.degToRad(55);
    const meioFov = THREE.MathUtils.degToRad(camera.fov) / 2;
    const distancia = THREE.MathUtils.clamp(3000 / (Math.tan(meioFov) * Math.min(1, camera.aspect)), 3600, 9000);
    controles.target.copy(centro);
    camera.position.copy(centro).addScaledVector(rumo, Math.cos(elevacao) * distancia).setY(centro.y + Math.sin(elevacao) * distancia);
    controles.update();
    sujo = true;
  }

  const v = new THREE.Vector3();
  const lado = new THREE.Vector3();
  /**
   * Pixels da tela sem arredondar, ou `null` atrás da câmera. "Atrás" sai do espaço da câmera, não
   * da profundidade projetada: um ponto a 30 km passa do `far` e ainda está à vista no horizonte.
   */
  function projetarLonge(ponto: THREE.Vector3): Tela | null {
    v.copy(ponto).applyMatrix4(camera.matrixWorldInverse);
    if (v.z > -camera.near) return null;
    v.applyMatrix4(camera.projectionMatrix);
    return { x: ((v.x + 1) / 2) * el.clientWidth, y: ((1 - v.y) / 2) * el.clientHeight };
  }
  /** Pixels inteiros, ou `null` atrás da câmera ou a mais de `margem` px fora da tela. */
  function naTela(ponto: THREE.Vector3, margem = Infinity): Tela | null {
    const p = projetarLonge(ponto);
    if (!p || p.x < -margem || p.y < -margem || p.x > el.clientWidth + margem || p.y > el.clientHeight + margem) return null;
    return { x: Math.round(p.x), y: Math.round(p.y) };
  }
  function quadroEntorno(): QuadroEntorno {
    const origem = naTela(centro) ?? { x: el.clientWidth / 2, y: el.clientHeight / 2 };
    const pontos = pontosEntorno.map(({ p, posicao }) => {
      // Um pouco além da borda, para o marcador esmaecer ao sair da tela em vez de sumir.
      if (!p.distante) return naTela(posicao, MARGEM_FADE);
      // Distante: a posição real só se estiver na tela; o rumo da seta sai de um passo da origem
      // na direção dele (a reta projeta numa reta, e perto da origem a projeção não explode).
      const tela = naTela(posicao, 0);
      const rumoPonto = posicao.clone().sub(centro).setY(0);
      const c = projetarLonge(centro);
      const passo = projetarLonge(centro.clone().add(rumoPonto.clone().setLength(200)));
      let angulo: number;
      if (c && passo) angulo = Math.atan2(passo.y - c.y, passo.x - c.x);
      else {
        // Origem atrás da câmera: o rumo sai do espaço da câmera, sem perspectiva.
        v.copy(rumoPonto).transformDirection(camera.matrixWorldInverse);
        angulo = Math.atan2(-v.y, v.x);
      }
      return { angulo: Number(angulo.toFixed(3)), tela };
    });
    // O rótulo de cada anel fica à direita da origem, de quem olha.
    lado.setFromMatrixColumn(camera.matrixWorld, 0).setY(0).normalize();
    const aneis = RAIOS.map(raio => ({ raio, tela: naTela(centro.clone().addScaledVector(lado, raio), 0) }));
    const alcance = Math.round(camera.position.distanceTo(controles.target) / 10) * 10;
    return { origem, alcance, pontos, aneis };
  }

  const corDo = (tipo: Lote['tipo']) => {
    const exemplo = o.dados.lotes.find(l => l.tipo === tipo && !l.status);
    const m = exemplo && lotes.get(exemplo.id);
    return m ? `#${(m.userData.base as THREE.MeshStandardMaterial).color.getHexString()}` : 'transparent';
  };

  return {
    montar(e) { container = e; e.prepend(el); redimensionar.observe(e); sujo = true; },
    inicio() { abertura = true; inicio(); },
    enquadrar,
    enquadrarMarco,
    selecionar(id) { selecionado = id; aplicarRealces(); },
    aproximar(f) {
      abertura = false;
      const d = camera.position.clone().sub(controles.target).multiplyScalar(f);
      camera.position.copy(controles.target).add(d.setLength(THREE.MathUtils.clamp(d.length(), controles.minDistance, controles.maxDistance)));
      controles.update();
    },
    camera: () => ({ posicao: camera.position.toArray(), alvo: controles.target.toArray() }),
    irPara(posicao, alvo) {
      abertura = false;
      controles.target.fromArray(alvo);
      camera.position.fromArray(posicao);
      controles.update();
    },
    ceu(modo) { ceu.cor(modo); agua.uniforms.uAgua.value.set(COR_AGUA[modo]); sujo = true; },
    entorno: mostrarEntorno,
    cores: () => ({ residencial: corDo('residencial'), uso_misto: corDo('uso_misto') }),
    descartar() {
      redimensionar.disconnect();
      renderer.setAnimationLoop(null);
      controles.dispose();
      ceu.descartar();
      entorno?.descartar();
      agua.dispose();
      renderer.dispose();
      el.remove();
    },
  };
}
