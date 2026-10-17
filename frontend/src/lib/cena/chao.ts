// O chão pintado: cada tile do mapa vem no GLB com o masterplan por cima do OSM. Desligado o
// masterplan, a textura de cada tile troca pela imagem só com OSM (mesma janela, mesmas UVs).
import * as THREE from 'three';

/** `chao_mapa_<k>`: o material de cada tile, no loteamento e no entorno. */
const MATERIAL_DO_TILE = /^chao_mapa_(\d{2})$/;

interface Tile {
  material: THREE.MeshStandardMaterial;
  masterplan: THREE.Texture;
}

export class Chao {
  private readonly tiles = new Map<string, Tile[]>();
  private readonly osm = new Map<string, THREE.Texture>();
  private readonly pedidos = new Map<string, Promise<void>>();
  private masterplanLigado = true;

  constructor(private readonly base: URL) {}

  /** Passa a cuidar dos tiles que houver sob `raiz` (um GLB que acabou de chegar). */
  adicionar(raiz: THREE.Object3D): void {
    raiz.traverse(o => {
      const malha = o as THREE.Mesh;
      if (!malha.isMesh) return;
      for (const m of ([] as THREE.Material[]).concat(malha.material)) {
        const k = MATERIAL_DO_TILE.exec(m.name)?.[1];
        const material = m as THREE.MeshStandardMaterial;
        if (!k || !material.map) continue;
        const lista = this.tiles.get(k) ?? [];
        if (!lista.some(t => t.material === material)) lista.push({ material, masterplan: material.map });
        this.tiles.set(k, lista);
      }
    });
    if (this.masterplanLigado) return;
    void this.carregarOsm().then(() => this.aplicar());
  }

  /** Liga ou desliga o masterplan. `false` se faltou a imagem do OSM: o chão fica como estava. */
  async masterplan(ligado: boolean): Promise<boolean> {
    this.masterplanLigado = ligado;
    if (!ligado && !(await this.carregarOsm())) {
      this.masterplanLigado = true;
      return false;
    }
    if (this.masterplanLigado === ligado) this.aplicar();
    return true;
  }

  private aplicar(): void {
    for (const [k, lista] of this.tiles) {
      const osm = this.osm.get(k);
      for (const t of lista) {
        const textura = this.masterplanLigado || !osm ? t.masterplan : osm;
        if (t.material.map === textura) continue;
        t.material.map = textura;
        t.material.needsUpdate = true;
      }
    }
  }

  /** Baixa a imagem do OSM de cada tile que ainda não veio (uma só vez por tile). */
  private async carregarOsm(): Promise<boolean> {
    try {
      await Promise.all([...this.tiles].map(([k, [primeiro]]) => this.imagemOsm(k, primeiro!.masterplan)));
      return true;
    } catch (erro) {
      console.warn('o chão só com OSM não carregou', erro);
      return false;
    }
  }

  private imagemOsm(k: string, doGlb: THREE.Texture): Promise<void> {
    let pedido = this.pedidos.get(k);
    if (!pedido) {
      pedido = new THREE.TextureLoader().loadAsync(new URL(`modelos/mapa-osm_${k}.jpg`, this.base).href).then(textura => {
        // Como a textura do GLB: sem inverter o eixo (as UVs do glTF) e com o mesmo filtro.
        textura.flipY = false;
        textura.colorSpace = THREE.SRGBColorSpace;
        textura.wrapS = doGlb.wrapS;
        textura.wrapT = doGlb.wrapT;
        textura.minFilter = doGlb.minFilter;
        textura.magFilter = doGlb.magFilter;
        textura.anisotropy = doGlb.anisotropy;
        this.osm.set(k, textura);
      });
      this.pedidos.set(k, pedido);
      pedido.catch(() => this.pedidos.delete(k)); // falhou: a próxima tentativa baixa de novo
    }
    return pedido;
  }

  descartar(): void {
    for (const t of this.osm.values()) t.dispose();
    this.osm.clear();
  }
}
