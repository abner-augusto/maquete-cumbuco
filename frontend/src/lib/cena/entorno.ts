// O entorno: terreno, mar, vias e prédios num GLB próprio, a vegetação instanciada por espécie e os
// anéis de distância. Carrega só quando pedido (botão de entorno).
import * as THREE from 'three';
import type { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { Line2 } from 'three/addons/lines/Line2.js';
import { LineGeometry } from 'three/addons/lines/LineGeometry.js';
import { LineMaterial } from 'three/addons/lines/LineMaterial.js';

/** Raios dos anéis de distância, em metros: 1, 2 e 4 km. */
export const RAIOS_ANEIS: readonly number[] = [1000, 2000, 4000];

/**
 * Rótulos de anel que cabem na tela: do anel de fora para dentro (o maior é o que mais informa),
 * fica o que está a `folga` px ou mais de todos os que já ficaram. De longe, os anéis se juntam.
 */
export function rotulosQueCabem<T extends { raio: number; tela: { x: number; y: number } | null }>(aneis: T[], folga: number): T[] {
  const ficam: T[] = [];
  for (const a of [...aneis].sort((p, q) => q.raio - p.raio)) {
    const t = a.tela;
    if (t && ficam.every(f => Math.hypot(f.tela!.x - t.x, f.tela!.y - t.y) >= folga)) ficam.push(a);
  }
  return ficam.sort((p, q) => p.raio - q.raio);
}

/** Altura dos anéis sobre o terreno: soltos do chão, acima das copas e dos telhados baixos. */
const ALTURA_ANEL = 14;
/** Espaçamento dos pontos de cada anel (m). */
const PASSO_ANEL = 16;

interface Vegetacao {
  /** `especies.<nome>.instancias`: [x_dm, y_dm, z_cm, escala_pct, rotacao_graus, …], x leste, y norte. */
  especies: Record<string, { n: number; instancias: number[] }>;
  /** A mata do OSM sob o masterplan, no mesmo formato: só aparece com a projeção desligada. */
  sem_masterplan?: { especies: Record<string, { n: number; instancias: number[] }> };
}

const CAMPOS = 5;

export class Entorno {
  readonly grupo = new THREE.Group();
  /** `extra`: a mata sob o masterplan, só à vista com a projeção desligada. */
  private readonly arvores: { malha: THREE.InstancedMesh; total: number; extra: boolean }[] = [];
  private semMasterplan = false;
  private fracao = 1;
  /** Malhas do terreno: o entorno detalhado e, quando chega, a orla. */
  readonly terreno: THREE.Object3D[];
  /** Malhas da orla regional, quando chegam (carregarOrla). */
  readonly orla: THREE.Mesh[] = [];
  /** Os anéis de distância, juntos: o modo cinema os esconde. */
  readonly aneis = new THREE.Group();
  private readonly raio = new THREE.Raycaster();
  private readonly centro: THREE.Vector3;
  private readonly raios: readonly number[];
  private readonly linhaAnel = new LineMaterial({ color: 0x2b2e1e, linewidth: 1.6, transparent: true, opacity: 0.7, depthWrite: false });

  private constructor(cenario: THREE.Group, modelos: THREE.Group, vegetacao: Vegetacao, centro: THREE.Vector3, raios: readonly number[], fracao: number) {
    this.grupo.name = 'ENTORNO';
    this.grupo.add(cenario);
    this.terreno = cenario.children.filter(o => o.name.startsWith('Entorno_'));
    cenario.updateMatrixWorld(true);
    modelos.updateMatrixWorld(true);

    const matriz = new THREE.Matrix4();
    const rotacao = new THREE.Quaternion();
    const eixo = new THREE.Vector3(0, 1, 0);
    const posicao = new THREE.Vector3();
    const escala = new THREE.Vector3();
    const plantios = [
      ...Object.entries(vegetacao.especies).map(([nome, v]) => ({ nome, instancias: v.instancias, extra: false })),
      ...Object.entries(vegetacao.sem_masterplan?.especies ?? {}).map(([nome, v]) => ({ nome, instancias: v.instancias, extra: true })),
    ];
    for (const { nome, instancias, extra } of plantios) {
      const modelo = modelos.getObjectByName(`VEG_${nome}`) as THREE.Mesh | undefined;
      if (!modelo) continue;
      // O GLB comprimido guarda a malha quantizada, com a escala no nó: a instância compõe as duas.
      const doModelo = modelo.matrixWorld.clone();
      const total = instancias.length / CAMPOS;
      const malha = new THREE.InstancedMesh(modelo.geometry, modelo.material, total);
      malha.name = extra ? `VEG_${nome}_sem_masterplan` : `VEG_${nome}`;
      for (let i = 0; i < total; i++) {
        const k = i * CAMPOS;
        posicao.set(instancias[k]! / 10, instancias[k + 2]! / 100, -instancias[k + 1]! / 10);
        escala.setScalar(instancias[k + 3]! / 100);
        rotacao.setFromAxisAngle(eixo, THREE.MathUtils.degToRad(instancias[k + 4]!));
        malha.setMatrixAt(i, matriz.compose(posicao, rotacao, escala).multiply(doModelo));
      }
      malha.instanceMatrix.needsUpdate = true;
      malha.computeBoundingSphere();
      this.arvores.push({ malha, total, extra });
      this.grupo.add(malha);
    }
    this.fracao = fracao;
    this.vegetacao(fracao);

    this.centro = centro.clone();
    this.raios = raios;
    this.grupo.add(this.aneis);
  }

  /**
   * Anéis de distância em volta dos lotes: linha fina (em pixels) solta acima do terreno, que acompanha
   * o relevo e não some atrás das dunas. `cota(x, z)` é a maior cota do terreno em volta do ponto
   * (mapaDeCotas): entre duas amostras o terreno sobe a um topo que a amostra não viu. Refeito quando
   * a orla chega, porque o anel de 4 km já cai além do entorno detalhado.
   */
  montarAneis(cota: (x: number, z: number) => number): void {
    for (const a of this.aneis.children as Line2[]) a.geometry.dispose();
    this.aneis.clear();
    for (const r of this.raios) {
      const n = Math.ceil((2 * Math.PI * r) / PASSO_ANEL);
      const posicoes: number[] = [];
      for (let i = 0; i <= n; i++) {
        const a = (i / n) * Math.PI * 2;
        const x = this.centro.x + Math.cos(a) * r;
        const z = this.centro.z + Math.sin(a) * r;
        posicoes.push(x, cota(x, z) + ALTURA_ANEL, z);
      }
      const anel = new Line2(new LineGeometry().setPositions(posicoes), this.linhaAnel);
      anel.computeLineDistances();
      anel.renderOrder = 2;
      this.aneis.add(anel);
    }
  }

  /** Tamanho da tela em pixels: a espessura dos anéis é medida nela. */
  tela(largura: number, altura: number): void {
    this.linhaAnel.resolution.set(largura, altura);
  }

  static async carregar(loader: GLTFLoader, base: URL, centro: THREE.Vector3, raios: readonly number[], fracao: number): Promise<Entorno> {
    const [cenario, modelos, resposta] = await Promise.all([
      loader.loadAsync(new URL('modelos/entorno.glb', base).href),
      loader.loadAsync(new URL('modelos/vegetacao.glb', base).href),
      fetch(new URL('modelos/vegetacao.json', base)),
    ]);
    if (!resposta.ok) throw Error('Não foi possível carregar a vegetação');
    return new Entorno(cenario.scene, modelos.scene, (await resposta.json()) as Vegetacao, centro, raios, fracao);
  }

  /** A orla regional (Pecém a Iracema), num GLB à parte: chega depois, e o entorno já está na tela. */
  static async carregarOrla(loader: GLTFLoader, base: URL): Promise<THREE.Group> {
    return (await loader.loadAsync(new URL('modelos/orla.glb', base).href)).scene;
  }

  /**
   * Põe a orla na cena. A borda de terra desbota pelo alfa dos vértices (COLOR_0): o que aparece
   * por trás é o céu, na cor do solo, a mesma da névoa. Sob o entorno detalhado ela fica abaixo.
   */
  adicionarOrla(cena: THREE.Group): void {
    cena.traverse(o => {
      const malha = o as THREE.Mesh;
      if (!malha.isMesh) return;
      for (const m of ([] as THREE.Material[]).concat(malha.material)) {
        m.transparent = true;
        (m as THREE.MeshStandardMaterial).vertexColors = true;
        m.needsUpdate = true;
      }
      this.orla.push(malha);
    });
    this.grupo.add(cena);
    this.terreno.push(cena);
    cena.updateMatrixWorld(true);
  }

  /** Cota do terreno do entorno em (x leste, y norte), por um raio vertical; 0 se não acertar. */
  cotaEm(x: number, y: number): number {
    this.raio.set(new THREE.Vector3(x, 5000, -y), new THREE.Vector3(0, -1, 0));
    return this.raio.intersectObjects(this.terreno, true)[0]?.point.y ?? 0;
  }

  /**
   * Fração de cada espécie que aparece. As instâncias vêm embaralhadas, então as N primeiras são
   * uma amostra uniforme e baixar a fração rareia a mata por igual, sem abrir clareiras.
   */
  vegetacao(fracao: number): void {
    this.fracao = fracao;
    for (const { malha, total, extra } of this.arvores) {
      malha.count = Math.round(total * THREE.MathUtils.clamp(fracao, 0, 1));
      malha.visible = malha.count > 0 && (!extra || this.semMasterplan);
    }
  }

  /**
   * Com a projeção do masterplan desligada o chão volta a ser o OSM, e a mata do OSM que o desenho
   * cobria aparece; ligada, ela some de novo.
   */
  masterplan(ligado: boolean): void {
    this.semMasterplan = !ligado;
    this.vegetacao(this.fracao);
  }

  descartar(): void {
    this.grupo.traverse(o => {
      const malha = o as THREE.Mesh;
      if (!malha.geometry) return;
      malha.geometry.dispose();
      for (const m of ([] as THREE.Material[]).concat(malha.material)) m.dispose();
    });
    for (const { malha } of this.arvores) malha.dispose();
  }
}
