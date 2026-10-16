// Céu em gradiente: azul com horizonte quente de dia, horizonte alaranjado quando o sol está
// baixo (08h/16h), e um crepúsculo contido no modo escuro. A esfera acompanha a câmera.
import * as THREE from 'three';

/**
 * Três faixas acima do horizonte: a linha do horizonte (quente), uma faixa azul-névoa logo
 * acima e o zênite. A faixa azul separa o céu do solo, que é areia.
 */
interface Paleta {
  zenite: string;
  faixa: string;
  /** Linha do horizonte de costas para o sol. */
  horizonte: string;
  /** Linha do horizonte do lado do sol. */
  horizonteQuente: string;
  chao: string;
}

const PALETA: Record<'claro' | 'escuro', { dia: Paleta; baixo: Paleta }> = {
  claro: {
    dia: { zenite: '#4F8BD0', faixa: '#BFD5EC', horizonte: '#E8E4DA', horizonteQuente: '#EFDCC2', chao: '#D6CAB8' },
    baixo: { zenite: '#6A88C2', faixa: '#B9C6E2', horizonte: '#EDB98F', horizonteQuente: '#F0884A', chao: '#D2BDA6' },
  },
  escuro: {
    dia: { zenite: '#141C2E', faixa: '#26324C', horizonte: '#3A3A48', horizonteQuente: '#44404E', chao: '#22211C' },
    baixo: { zenite: '#161B30', faixa: '#2C3352', horizonte: '#5A4048', horizonteQuente: '#7A4A35', chao: '#26221D' },
  },
};

const vertexShader = /* glsl */ `
  varying vec3 vDirecao;
  void main() {
    vDirecao = normalize(position);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const fragmentShader = /* glsl */ `
  uniform vec3 uZenite;
  uniform vec3 uFaixa;
  uniform vec3 uHorizonte;
  uniform vec3 uHorizonteQuente;
  uniform vec3 uChao;
  uniform vec3 uSolDirecao;
  uniform vec3 uSolCor;
  uniform vec3 uSolNucleo;
  uniform float uBrilhoSol;
  varying vec3 vDirecao;

  void main() {
    vec3 d = normalize(vDirecao);
    vec3 sol = normalize(uSolDirecao);
    // Lado do sol no horizonte: 1 de frente para ele, 0 de costas.
    float ladoSol = 0.5 + 0.5 * dot(normalize(d.xz + 1e-5), normalize(sol.xz + 1e-5));
    vec3 horizonte = mix(uHorizonte, uHorizonteQuente, ladoSol * ladoSol);
    // Acima: linha quente do horizonte → faixa azul-névoa (~4°) → zênite (~18°). Curvas suaves,
    // sem degrau; a câmera do espelho olha para baixo e só enxerga a parte baixa do céu.
    vec3 ceu = mix(horizonte, uFaixa, smoothstep(0.0, 0.07, d.y));
    ceu = mix(ceu, uZenite, smoothstep(0.07, 0.32, d.y));
    // Abaixo: logo sob a linha, a cor do horizonte (o mar chega até ela e emenda sem faixa);
    // mais para baixo, onde a borda da terra some na névoa, o solo (areia).
    vec3 solo = mix(horizonte, uChao, smoothstep(0.0, 0.05, -d.y));
    vec3 cor = d.y >= 0.0 ? ceu : solo;
    // Sol na posição do horário: disco com borda escurecida, coroa curta e um brilho largo que
    // tinge o céu em volta. O disco é ~4× o real para ser lido de longe; some sob o horizonte.
    float ang = acos(clamp(dot(d, sol), -1.0, 1.0));
    float raio = 0.02;
    float disco = (1.0 - smoothstep(raio * 0.8, raio, ang)) * smoothstep(-0.004, 0.004, d.y);
    float borda = mix(1.0, 0.72, pow(clamp(ang / raio, 0.0, 1.0), 2.0));
    float coroa = exp(-ang / 0.035) * 0.55;
    float brilho = exp(-ang / 0.3) * 0.22;
    cor = mix(cor, cor + uSolCor * (coroa + brilho), uBrilhoSol);
    cor = mix(cor, uSolNucleo * borda, disco * uBrilhoSol);
    gl_FragColor = vec4(cor, 1.0);
    #include <colorspace_fragment>
  }
`;

export class Ceu {
  readonly malha: THREE.Mesh;
  private readonly uniforms = {
    uZenite: { value: new THREE.Color() },
    uFaixa: { value: new THREE.Color() },
    uHorizonte: { value: new THREE.Color() },
    uHorizonteQuente: { value: new THREE.Color() },
    uChao: { value: new THREE.Color() },
    uSolDirecao: { value: new THREE.Vector3(0, 1, 0) },
    uSolCor: { value: new THREE.Color() },
    uSolNucleo: { value: new THREE.Color() },
    uBrilhoSol: { value: 0 },
  };
  private modo: 'claro' | 'escuro' = 'claro';
  private calor = 0;
  private brilho = 0;

  constructor(raio: number) {
    const material = new THREE.ShaderMaterial({
      uniforms: this.uniforms,
      vertexShader,
      fragmentShader,
      side: THREE.BackSide,
      depthWrite: false,
      depthTest: false,
    });
    this.malha = new THREE.Mesh(new THREE.SphereGeometry(raio, 48, 24), material);
    this.malha.name = 'CEU';
    this.malha.renderOrder = -1;
    this.malha.frustumCulled = false;
    this.atualizar();
  }

  /**
   * `calor` vai de 0 (sol alto) a 1 (sol baixo, horizonte laranja); `brilho` liga o halo do sol,
   * que só aparece na simulação: a luz de apresentação não afirma onde o sol está.
   */
  sol(direcao: THREE.Vector3, calor: number, brilho: number): void {
    this.uniforms.uSolDirecao.value.copy(direcao);
    this.brilho = brilho;
    this.calor = calor;
    this.atualizar();
  }

  cor(modo: 'claro' | 'escuro'): void {
    this.modo = modo;
    this.atualizar();
  }

  /** As cores e o sol que a água reflete: as próprias instâncias dos uniforms, sem cópia. */
  coresAgua(): { zenite: THREE.Color; faixa: THREE.Color; horizonte: THREE.Color; sol: THREE.Vector3 } {
    const u = this.uniforms;
    return { zenite: u.uZenite.value, faixa: u.uFaixa.value, horizonte: u.uHorizonte.value, sol: u.uSolDirecao.value };
  }

  /** Cor do solo abaixo do horizonte: a névoa do entorno usa a mesma, para a borda sumir no céu. */
  corSolo(): THREE.Color {
    return this.uniforms.uChao.value;
  }

  private atualizar(): void {
    const { dia, baixo } = PALETA[this.modo];
    const t = this.calor;
    const mistura = (a: string, b: string, alvo: THREE.Color) => alvo.set(a).lerp(new THREE.Color(b), t);
    mistura(dia.zenite, baixo.zenite, this.uniforms.uZenite.value);
    mistura(dia.faixa, baixo.faixa, this.uniforms.uFaixa.value);
    mistura(dia.horizonte, baixo.horizonte, this.uniforms.uHorizonte.value);
    mistura(dia.horizonteQuente, baixo.horizonteQuente, this.uniforms.uHorizonteQuente.value);
    mistura(dia.chao, baixo.chao, this.uniforms.uChao.value);
    // Sol alto: branco-creme; sol baixo: dourado, com coroa alaranjada.
    mistura('#FFFBF0', '#FFD9A0', this.uniforms.uSolNucleo.value);
    mistura('#FFE8C4', '#FF9F55', this.uniforms.uSolCor.value);
    this.uniforms.uBrilhoSol.value = this.brilho * (this.modo === 'escuro' ? 0.7 : 1);
  }

  descartar(): void {
    this.malha.geometry.dispose();
    (this.malha.material as THREE.Material).dispose();
  }
}
