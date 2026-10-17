// O mar do entorno: reflexo do céu pelo Fresnel, ondas por normais analíticas (o plano tem poucos
// vértices; nada se desloca), água que clareia perto da costa e o brilho do sol. As cores do céu
// são as mesmas instâncias do Ceu, então o modo claro/escuro chega aqui sem cópia.
import * as THREE from 'three';
import type { MapaCosta } from './mapa-costa';

const QUADRO_MS = 1000 / 24;

/** Pede um quadro novo para a água? Só no entorno, sem movimento reduzido, a ~24 quadros/s. */
export function quadroDaAgua(o: { entorno: boolean; reduzido: boolean; agora: number; ultimo: number }): boolean {
  return o.entorno && !o.reduzido && o.agora - o.ultimo >= QUADRO_MS;
}

export interface CoresCeu {
  zenite: THREE.Color;
  faixa: THREE.Color;
  horizonte: THREE.Color;
  /** Solo abaixo do horizonte: a água de longe desbota para o que o céu mostra naquela direção. */
  chao: THREE.Color;
  /** Horizonte do lado do sol, como no Ceu: o fim do mar emenda nele sem aresta. */
  horizonteQuente: THREE.Color;
  sol: THREE.Vector3;
}

/**
 * Até onde o plano da água vai, em metros do `centro` (dos lotes): lido da malha, não de um número.
 * No mundo: o GLB quantizado guarda a posição normalizada e a escala no nó.
 */
export function alcanceDaAgua(malha: THREE.Mesh, centro: THREE.Vector3): number {
  const p = malha.geometry.getAttribute('position');
  const v = new THREE.Vector3();
  let r2 = 0;
  for (let i = 0; i < p.count; i++) {
    v.fromBufferAttribute(p, i).applyMatrix4(malha.matrixWorld);
    const dx = v.x - centro.x, dz = v.z - centro.z;
    r2 = Math.max(r2, dx * dx + dz * dz);
  }
  return Math.sqrt(r2);
}

/** Cota do mar (y do mundo), lida de um vértice do plano da água. */
export function nivelDaAgua(malha: THREE.Mesh): number {
  return new THREE.Vector3().fromBufferAttribute(malha.geometry.getAttribute('position'), 0).applyMatrix4(malha.matrixWorld).y;
}

const vertexShader = /* glsl */ `
  varying vec3 vMundo;
  void main() {
    vec4 mundo = modelMatrix * vec4(position, 1.0);
    vMundo = mundo.xyz;
    gl_Position = projectionMatrix * viewMatrix * mundo;
  }
`;

/** Um parâmetro numérico da água: vira uniform do shader e slider do painel do modo dev. */
export interface ParametroAgua {
  uniforme: string;
  nome: string;
  min: number;
  max: number;
  passo: number;
  valor: number;
}

/** Valores do laboratório costeiro, ajustados à costa do Cumbuco (raso/espuma). */
export const PARAMETROS_AGUA: readonly ParametroAgua[] = [
  { uniforme: 'uOndaAmp', nome: 'Ondulação: amplitude', min: 0, max: 2.5, passo: 0.01, valor: 0.75 },
  { uniforme: 'uOndaFreq', nome: 'Ondulação: frequência', min: 0.0005, max: 0.012, passo: 0.0001, valor: 0.006 },
  { uniforme: 'uOndaVel', nome: 'Ondulação: velocidade', min: 0, max: 3, passo: 0.01, valor: 0.39 },
  { uniforme: 'uMarolaAmp', nome: 'Marola: amplitude', min: 0, max: 0.5, passo: 0.01, valor: 0.38 },
  { uniforme: 'uMarolaFreq', nome: 'Marola: frequência', min: 0.002, max: 0.085, passo: 0.0005, valor: 0.0085 },
  { uniforme: 'uForcaNormal', nome: 'Intensidade das ondas', min: 1, max: 40, passo: 0.1, valor: 16.7 },
  { uniforme: 'uFresnel', nome: 'Fresnel (reflexo do céu)', min: 0, max: 2, passo: 0.01, valor: 0.38 },
  { uniforme: 'uBrilho', nome: 'Brilho do sol: faíscas', min: 0, max: 1.5, passo: 0.01, valor: 0.44 },
  { uniforme: 'uBrilhoFechado', nome: 'Brilho do sol: foco', min: 10, max: 300, passo: 1, valor: 31 },
  { uniforme: 'uTrilha', nome: 'Brilho do sol: trilha', min: 0, max: 2, passo: 0.01, valor: 0.64 },
  { uniforme: 'uRaso', nome: 'Raso: fim do turquesa (m)', min: 0, max: 3000, passo: 5, valor: 555 },
  { uniforme: 'uMistura', nome: 'Raso: meia-largura da transição (m)', min: 10, max: 2000, passo: 5, valor: 745 },
  { uniforme: 'uClareza', nome: 'Raso: clareza de areia', min: 0, max: 0.8, passo: 0.01, valor: 0.42 },
  { uniforme: 'uEspumaForca', nome: 'Espuma: força', min: 0, max: 2, passo: 0.01, valor: 0.69 },
  { uniforme: 'uEspumaLargura', nome: 'Espuma: largura (m)', min: 2, max: 300, passo: 1, valor: 94 },
  { uniforme: 'uEspumaQuebra', nome: 'Espuma: quebra', min: 0.1, max: 2, passo: 0.01, valor: 0.69 },
];

// Porte do shader do laboratório costeiro tropical (ocean_tropical_coastal_lab_revisado.html): três
// ondulações longas e três marolas por normais analíticas, água que clareia para turquesa perto da
// praia, espuma na linha d'água e o brilho do sol em trilha. Do laboratório para cá mudou o que a cena
// tem: o céu vem do Ceu (modo claro/escuro e horizonte quente), a distância à costa vem do mapa
// do terreno (mapa-costa.ts) e, longe, a água desbota sozinha para a cor do horizonte.
const fragmentShader = /* glsl */ `
  uniform float uTempo;
  uniform vec2 uDesbotar;  // metros da câmera: onde começa e onde acaba o desbotar para o céu
  uniform vec3 uRasa;
  uniform vec3 uFunda;
  uniform vec3 uEspuma;
  uniform vec3 uZenite;
  uniform vec3 uFaixa;
  uniform vec3 uHorizonte;
  uniform vec3 uChao;
  uniform vec3 uHorizonteQuente;
  uniform vec3 uSolDirecao;
  // Raiz da distância à terra, 1 byte (mapa-costa.ts): um mapa fino em volta do loteamento e um largo,
  // com a orla. Cada caixa é x, z do centro e meio lado do quadrado coberto (m).
  uniform sampler2D uCostaFina;
  uniform vec3 uCostaFinaCaixa;
  uniform sampler2D uCostaLonge;
  uniform vec3 uCostaLongeCaixa;
  uniform float uCostaMax;
  varying vec3 vMundo;

  // Os parâmetros ajustáveis (PARAMETROS_AGUA), um uniform cada.
  ${PARAMETROS_AGUA.map(p => `uniform float ${p.uniforme};`).join('\n  ')}

  float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
  }

  float ruido(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
  }

  // Inclinação analítica por pixel, sem deslocar o plano. Direções oblíquas evitam o xadrez dos
  // senos ortogonais; a marola some quando fica menor que ~2 px, para não cintilar de longe.
  vec2 inclinacao(vec2 p) {
    float t = uTempo * uOndaVel;
    vec2 d1 = vec2(0.86, 0.51);
    vec2 d2 = vec2(-0.33, 0.94);
    vec2 d3 = vec2(0.61, -0.79);
    vec2 g = uOndaAmp * (
        0.65 * uOndaFreq * d1 * cos(dot(p, d1) * uOndaFreq + 1.3 * t)
      + 0.42 * (uOndaFreq * 1.19) * d2 * cos(dot(p, d2) * uOndaFreq * 1.19 - 0.91 * t)
      + 0.28 * (uOndaFreq * 0.68) * d3 * cos(dot(p, d3) * uOndaFreq * 0.68 + 0.73 * t)
    );
    vec2 r1 = vec2(0.95, 0.31);
    vec2 r2 = vec2(-0.58, 0.81);
    vec2 r3 = vec2(0.19, -0.98);
    float rt = uTempo * (uOndaVel * 1.8 + 0.02);
    float pixel = max(length(dFdx(p)), length(dFdy(p)));
    float marola = 1.0 - smoothstep(0.55, 1.35, pixel * uMarolaFreq);
    g += marola * uMarolaAmp * uMarolaFreq * (
        0.48 * r1 * cos(dot(p, r1) * uMarolaFreq + rt * 2.2)
      + 0.32 * 1.31 * r2 * cos(dot(p, r2) * uMarolaFreq * 1.31 - rt * 1.8)
      + 0.20 * 0.74 * r3 * cos(dot(p, r3) * uMarolaFreq * 0.74 + rt * 1.4)
    );
    return g;
  }

  // Distância à terra (m) num mapa: ele guarda a raiz, e a GPU interpola. -1 fora dele; as bordas
  // ficam de fora porque a terra que o mapa não viu faz a distância parecer maior ali.
  float lerCosta(sampler2D mapa, vec3 caixa, vec2 p) {
    vec2 uv = vec2((p.x - caixa.x) / (2.0 * caixa.z) + 0.5, 0.5 - (p.y - caixa.y) / (2.0 * caixa.z));
    if (uv.x < 0.04 || uv.y < 0.04 || uv.x > 0.96 || uv.y > 0.96) return -1.0;
    float t = texture2D(mapa, uv).r;
    return t * t * uCostaMax;
  }

  float distanciaDaCosta(vec2 p) {
    float d = lerCosta(uCostaFina, uCostaFinaCaixa, p);
    if (d < 0.0) d = lerCosta(uCostaLonge, uCostaLongeCaixa, p);
    return d < 0.0 ? uCostaMax : d;  // d == uCostaMax: água funda, sem terra por perto
  }

  // Horizonte na direção d (a mesma conta do Ceu): quente de frente para o sol.
  vec3 horizonteEm(vec3 d) {
    vec3 sol = normalize(uSolDirecao);
    float ladoSol = 0.5 + 0.5 * dot(normalize(d.xz + 1e-5), normalize(sol.xz + 1e-5));
    return mix(uHorizonte, uHorizonteQuente, ladoSol * ladoSol);
  }

  vec3 ceuEm(vec3 r) {
    float y = max(r.y, 0.0);
    vec3 c = mix(horizonteEm(r), uFaixa, smoothstep(0.0, 0.07, y));
    return mix(c, uZenite, smoothstep(0.07, 0.32, y));
  }

  void main() {
    vec2 grad = inclinacao(vMundo.xz) * uForcaNormal;
    vec3 n = normalize(vec3(-grad.x, 1.0, -grad.y));
    vec3 v = normalize(cameraPosition - vMundo);
    vec3 sol = normalize(uSolDirecao);
    vec3 h = normalize(v + sol);

    float costa = distanciaDaCosta(vMundo.xz);
    float raso = 1.0 - smoothstep(max(0.0, uRaso - uMistura), uRaso + uMistura, costa);
    vec3 base = mix(uFunda, uRasa, raso);
    base = mix(base, vec3(0.92, 0.85, 0.64) * 0.95 + base * 0.45, raso * uClareza);

    float nv = max(dot(n, v), 0.0);
    float nl = max(dot(n, sol), 0.0);
    float nh = max(dot(n, h), 0.0);

    float fresnel = clamp(pow(1.0 - nv, 3.0) * uFresnel, 0.0, 1.0);
    vec3 r = reflect(-v, n);
    r.y = abs(r.y);

    // Brilho do sol: faíscas com quebra por ruído e a trilha larga que o sol baixo deixa no mar.
    float miolo = pow(nh, uBrilhoFechado);
    float faisca = ruido(vMundo.xz * 0.012 + vec2(uTempo * 0.12, -uTempo * 0.09));
    faisca += ruido(vMundo.xz * 0.048 - vec2(uTempo * 0.20, uTempo * 0.18)) * 0.5;
    faisca /= 1.5;
    float mascara = smoothstep(0.42, 0.92, faisca + (1.0 - nv) * 0.18);
    float brilho = miolo * mascara * uBrilho;
    float trilha = pow(max(dot(reflect(-sol, n), v), 0.0), 28.0) * uTrilha;

    // Espuma colada à costa, com quebra por ruído.
    float faixa = 1.0 - smoothstep(0.0, uEspumaLargura * 1.35, costa);
    float quebra = ruido(vMundo.xz * 0.03 + vec2(uTempo * 0.06, uTempo * 0.04));
    float espuma = clamp(faixa * smoothstep(0.34, 0.86, quebra * uEspumaQuebra + 0.32) * uEspumaForca, 0.0, 1.0);

    vec3 cor = base * (0.42 + nl * 0.58);
    cor = mix(cor, ceuEm(r), clamp(fresnel * 0.58, 0.0, 1.0));
    cor += vec3(1.0, 0.88, 0.62) * (brilho + trilha);
    cor = mix(cor, uEspuma, espuma);

    // Longe, a água vira a cor que o céu tem nessa direção (a mesma conta do solo do Ceu, logo
    // abaixo da linha): o plano vai ao horizonte e acaba sem faixa, como se fosse infinito; a
    // borda reta do polígono do mar, além da terra do entorno, some no céu do mesmo jeito.
    float dist = length(cameraPosition.xz - vMundo.xz);
    vec3 fundo = mix(horizonteEm(-v), uChao, smoothstep(0.0, 0.05, v.y));
    cor = mix(cor, fundo, smoothstep(uDesbotar.x, uDesbotar.y, dist));
    gl_FragColor = vec4(cor, 1.0);
    #include <colorspace_fragment>
  }
`;

/**
 * Onde a água começa e acaba de desbotar para o céu, em metros da câmera, pelo `raio` da terra do
 * entorno. O polígono do mar prolonga a costa em linha reta logo depois da terra: o desbotar tem de
 * estar completo a dois raios, senão essa aresta se lê contra o céu.
 */
export function desbotarDaAgua(raio: number): THREE.Vector2 {
  return new THREE.Vector2(raio * 0.75, raio * 2);
}

export type ModoCor = 'claro' | 'escuro';
export type CorDaAgua = { rasa: string; funda: string; espuma: string };

/** Cores da água nos modos claro e escuro: turquesa rasa, azul funda e espuma (o reflexo do céu vem por cima). */
export const COR_AGUA_PADRAO: Readonly<Record<ModoCor, Readonly<CorDaAgua>>> = {
  claro: { rasa: '#70E1DF', funda: '#3196AF', espuma: '#A6BFC4' },
  escuro: { rasa: '#1C5A6A', funda: '#0E2A44', espuma: '#46646E' },
};

/** As cores em uso: o painel do modo dev as muda, e trocar de modo não as perde. */
export const COR_AGUA: Record<ModoCor, CorDaAgua> = { claro: { ...COR_AGUA_PADRAO.claro }, escuro: { ...COR_AGUA_PADRAO.escuro } };

export type MaterialAgua = THREE.ShaderMaterial & {
  uniforms: Record<string, THREE.IUniform> & {
    uTempo: THREE.IUniform<number>;
    uDesbotar: THREE.IUniform<THREE.Vector2>;
    uRasa: THREE.IUniform<THREE.Color>;
    uFunda: THREE.IUniform<THREE.Color>;
    uEspuma: THREE.IUniform<THREE.Color>;
    uCostaFina: THREE.IUniform<THREE.Texture>;
    uCostaFinaCaixa: THREE.IUniform<THREE.Vector3>;
    uCostaLonge: THREE.IUniform<THREE.Texture>;
    uCostaLongeCaixa: THREE.IUniform<THREE.Vector3>;
    uCostaMax: THREE.IUniform<number>;
  };
};

/** Põe as cores do modo claro ou escuro na água. */
export function corDaAgua(m: MaterialAgua, modo: ModoCor): void {
  const c = COR_AGUA[modo];
  m.uniforms.uRasa.value.set(c.rasa);
  m.uniforms.uFunda.value.set(c.funda);
  m.uniforms.uEspuma.value.set(c.espuma);
}

/** Entrega à água o mapa da costa, fino (em volta do loteamento) ou largo: a faixa rasa e a espuma passam a seguir a praia. */
export function costaDaAgua(m: MaterialAgua, mapa: MapaCosta, alcance: 'fina' | 'longe'): void {
  const [textura, caixa] = alcance === 'fina' ? [m.uniforms.uCostaFina, m.uniforms.uCostaFinaCaixa] : [m.uniforms.uCostaLonge, m.uniforms.uCostaLongeCaixa];
  textura.value.dispose();
  textura.value = mapa.textura;
  caixa.value.copy(mapa.caixa);
  m.uniforms.uCostaMax.value = mapa.max;
}

export function materialDaAgua(ceu: CoresCeu): MaterialAgua {
  // Antes dos mapas da costa: caixas minúsculas, então toda a água é funda.
  const semCosta = new THREE.DataTexture(new Uint8Array([255]), 1, 1, THREE.RedFormat, THREE.UnsignedByteType);
  semCosta.needsUpdate = true;
  const m = new THREE.ShaderMaterial({
    name: 'agua',
    uniforms: {
      uTempo: { value: 0 },
      ...Object.fromEntries(PARAMETROS_AGUA.map(p => [p.uniforme, { value: p.valor }])),
      uDesbotar: { value: new THREE.Vector2(0, 1) },  // a cena põe o valor pelo raio do entorno
      uRasa: { value: new THREE.Color() },
      uFunda: { value: new THREE.Color() },
      uEspuma: { value: new THREE.Color() },
      uCostaFina: { value: semCosta },
      uCostaFinaCaixa: { value: new THREE.Vector3(0, 0, 0.001) },
      uCostaLonge: { value: semCosta.clone() },
      uCostaLongeCaixa: { value: new THREE.Vector3(0, 0, 0.001) },
      uCostaMax: { value: 1 },
      // Mesmas instâncias do céu (sem clonar): trocar o modo de cor muda a água junto.
      uZenite: { value: ceu.zenite },
      uFaixa: { value: ceu.faixa },
      uHorizonte: { value: ceu.horizonte },
      uChao: { value: ceu.chao },
      uHorizonteQuente: { value: ceu.horizonteQuente },
      uSolDirecao: { value: ceu.sol },
    },
    vertexShader,
    fragmentShader,
    // O plano passa sob toda a terra do entorno, a centímetros dela nas baixadas e nas margens:
    // empurrado para trás na profundidade, o terreno ganha onde os dois quase coincidem e nada pisca.
    // Só o termo constante: o fator pela inclinação cresce sem limite na água rasante de longe e
    // jogava os fragmentos além do plano distante (serrilhado no fim do mar).
    polygonOffset: true,
    polygonOffsetFactor: 0,
    polygonOffsetUnits: 2,
  }) as MaterialAgua;
  corDaAgua(m, 'claro');
  return m;
}
