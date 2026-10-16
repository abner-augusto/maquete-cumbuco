// O entorno: terreno, mar, vias e prédios num GLB próprio, a vegetação instanciada por espécie e os
// anéis de distância. Carrega só quando pedido (botão de entorno).
import * as THREE from 'three';
import type { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { Line2 } from 'three/addons/lines/Line2.js';
import { LineGeometry } from 'three/addons/lines/LineGeometry.js';
import { LineMaterial } from 'three/addons/lines/LineMaterial.js';

/** Raios dos anéis de distância: um a cada `passo` m, até `ate` m. */
export function raiosDosAneis(passo: number, ate: number): number[] {
  return Array.from({ length: Math.floor(ate / passo + 1e-9) }, (_, i) => (i + 1) * passo);
}

/** Altura dos anéis sobre o terreno: soltos do chão, acima das copas e dos telhados baixos. */
const ALTURA_ANEL = 12;

interface Vegetacao {
  /** `especies.<nome>.instancias`: [x_dm, y_dm, z_cm, escala_pct, rotacao_graus, …], x leste, y norte. */
  especies: Record<string, { n: number; instancias: number[] }>;
}

const CAMPOS = 5;

export class Entorno {
  readonly grupo = new THREE.Group();
  private readonly arvores: { malha: THREE.InstancedMesh; total: number }[] = [];
  private readonly terreno: THREE.Object3D[];
  private readonly raio = new THREE.Raycaster();
  private readonly linhaAnel = new LineMaterial({ color: 0x2b2e1e, linewidth: 1.6, transparent: true, opacity: 0.7, depthWrite: false });

  private constructor(cenario: THREE.Group, modelos: THREE.Group, vegetacao: Vegetacao, centro: THREE.Vector3, raios: number[], fracao: number) {
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
    for (const [nome, { instancias }] of Object.entries(vegetacao.especies)) {
      const modelo = modelos.getObjectByName(`VEG_${nome}`) as THREE.Mesh | undefined;
      if (!modelo) continue;
      // O GLB comprimido guarda a malha quantizada, com a escala no nó: a instância compõe as duas.
      const doModelo = modelo.matrixWorld.clone();
      const total = instancias.length / CAMPOS;
      const malha = new THREE.InstancedMesh(modelo.geometry, modelo.material, total);
      malha.name = `VEG_${nome}`;
      for (let i = 0; i < total; i++) {
        const k = i * CAMPOS;
        posicao.set(instancias[k]! / 10, instancias[k + 2]! / 100, -instancias[k + 1]! / 10);
        escala.setScalar(instancias[k + 3]! / 100);
        rotacao.setFromAxisAngle(eixo, THREE.MathUtils.degToRad(instancias[k + 4]!));
        malha.setMatrixAt(i, matriz.compose(posicao, rotacao, escala).multiply(doModelo));
      }
      malha.instanceMatrix.needsUpdate = true;
      malha.computeBoundingSphere();
      this.arvores.push({ malha, total });
      this.grupo.add(malha);
    }
    this.vegetacao(fracao);

    // Anéis de distância em volta dos lotes: linha fina (em pixels) solta acima do terreno, que
    // acompanha o relevo e não some atrás das dunas.
    for (const r of raios) {
      const posicoes: number[] = [];
      for (let i = 0; i <= 256; i++) {
        const a = (i / 256) * Math.PI * 2;
        const x = centro.x + Math.cos(a) * r;
        const z = centro.z + Math.sin(a) * r;
        posicoes.push(x, Math.max(this.cotaEm(x, -z), 0) + ALTURA_ANEL, z);
      }
      const anel = new Line2(new LineGeometry().setPositions(posicoes), this.linhaAnel);
      anel.computeLineDistances();
      anel.renderOrder = 2;
      this.grupo.add(anel);
    }
  }

  /** Tamanho da tela em pixels: a espessura dos anéis é medida nela. */
  tela(largura: number, altura: number): void {
    this.linhaAnel.resolution.set(largura, altura);
  }

  static async carregar(loader: GLTFLoader, base: URL, centro: THREE.Vector3, raios: number[], fracao: number): Promise<Entorno> {
    const [cenario, modelos, resposta] = await Promise.all([
      loader.loadAsync(new URL('modelos/entorno.glb', base).href),
      loader.loadAsync(new URL('modelos/vegetacao.glb', base).href),
      fetch(new URL('modelos/vegetacao.json', base)),
    ]);
    if (!resposta.ok) throw Error('Não foi possível carregar a vegetação');
    return new Entorno(cenario.scene, modelos.scene, (await resposta.json()) as Vegetacao, centro, raios, fracao);
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
    for (const { malha, total } of this.arvores) {
      malha.count = Math.round(total * THREE.MathUtils.clamp(fracao, 0, 1));
      malha.visible = malha.count > 0;
    }
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
