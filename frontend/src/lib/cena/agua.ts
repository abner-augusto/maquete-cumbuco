// O mar do entorno: reflexo do céu pelo Fresnel, ondas por normais procedurais (o plano tem poucos
// vértices; nada se desloca) e o brilho do sol. As cores do céu são as mesmas instâncias do Ceu,
// então o modo claro/escuro chega aqui sem cópia.
import * as THREE from 'three';

const QUADRO_MS = 1000 / 24;

/** Pede um quadro novo para a água? Só no entorno, sem movimento reduzido, a ~24 quadros/s. */
export function quadroDaAgua(o: { entorno: boolean; reduzido: boolean; agora: number; ultimo: number }): boolean {
  return o.entorno && !o.reduzido && o.agora - o.ultimo >= QUADRO_MS;
}

export interface CoresCeu {
  zenite: THREE.Color;
  faixa: THREE.Color;
  horizonte: THREE.Color;
  sol: THREE.Vector3;
}

const vertexShader = /* glsl */ `
  varying vec3 vMundo;
  void main() {
    vec4 mundo = modelMatrix * vec4(position, 1.0);
    vMundo = mundo.xyz;
    gl_Position = projectionMatrix * viewMatrix * mundo;
  }
`;

// Ondas por ruído fractal (sete escalas, de 64 m a 1 m; a mais longa ainda se lê de longe), cada uma girada e andando para um lado.
// Cada escala some quando fica menor que ~3 px na tela (fwidth): de longe e rente não há faixas
// nem cintilação, e o mar vira espelho do horizonte, como no real. Sem névoa da cena: a água
// desbota sozinha para a cor do horizonte até o fim do plano.
const fragmentShader = /* glsl */ `
  uniform float uTempo;
  uniform float uAlcance;
  uniform vec3 uAgua;
  uniform vec3 uZenite;
  uniform vec3 uFaixa;
  uniform vec3 uHorizonte;
  uniform vec3 uSolDirecao;
  varying vec3 vMundo;

  float hash(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
  }

  // Ruído de valor com derivadas analíticas (valor, d/dx, d/dy).
  vec3 ruido(vec2 x) {
    vec2 i = floor(x);
    vec2 f = fract(x);
    vec2 u = f * f * (3.0 - 2.0 * f);
    vec2 du = 6.0 * f * (1.0 - f);
    float a = hash(i), b = hash(i + vec2(1.0, 0.0)), c = hash(i + vec2(0.0, 1.0)), d = hash(i + vec2(1.0, 1.0));
    float k = a - b - c + d;
    return vec3(a + (b - a) * u.x + (c - a) * u.y + k * u.x * u.y, du * (vec2(b - a, c - a) + k * u.yx));
  }

  vec3 ceuEm(vec3 r) {
    float y = max(r.y, 0.0);
    vec3 c = mix(uHorizonte, uFaixa, smoothstep(0.0, 0.07, y));
    return mix(c, uZenite, smoothstep(0.07, 0.32, y));
  }

  void main() {
    vec2 p = vMundo.xz;
    float pixel = max(length(fwidth(p)), 1e-3);  // metros por pixel
    vec2 inclinacao = vec2(0.0);
    float amp = 1.0;
    float freq = 1.0 / 64.0;
    mat2 gira = mat2(0.8, -0.6, 0.6, 0.8);
    vec2 dir = vec2(0.71, 0.71);
    for (int i = 0; i < 7; i++) {
      float vel = 1.4 / sqrt(freq * 48.0);  // ondas longas andam mais rápido
      vec3 n = ruido(p * freq + dir * uTempo * vel * freq * 6.0);
      float some = 1.0 - smoothstep(0.08, 0.33, pixel * freq);
      inclinacao += amp * some * n.yz * freq;
      amp *= 0.55;
      freq *= 2.0;
      p = gira * p;
      dir = gira * dir;
    }
    vec3 n = normalize(vec3(-inclinacao.x * 7.0, 1.0, -inclinacao.y * 7.0));
    vec3 v = normalize(cameraPosition - vMundo);
    float fresnel = 0.02 + 0.98 * pow(1.0 - max(dot(n, v), 0.0), 5.0);
    vec3 r = reflect(-v, n);
    r.y = abs(r.y);
    // Corpo da água: mais claro na face da onda voltada para quem olha.
    vec3 corpo = uAgua * (0.85 + 0.35 * max(dot(n, v), 0.0));
    vec3 cor = mix(corpo, ceuEm(r), fresnel);
    vec3 sol = normalize(uSolDirecao);
    float s = max(dot(r, sol), 0.0);
    cor += vec3(1.0, 0.94, 0.82) * (pow(s, 700.0) * 1.6 + pow(s, 50.0) * 0.12);
    // Longe, a água vira a cor do horizonte até o fim do plano: sem faixa entre mar e céu.
    float dist = length(cameraPosition.xz - vMundo.xz);
    cor = mix(cor, uHorizonte, smoothstep(uAlcance * 0.35, uAlcance * 0.85, dist));
    gl_FragColor = vec4(cor, 1.0);
    #include <colorspace_fragment>
  }
`;

/** Cor da água funda nos modos claro e escuro (o reflexo do céu vem por cima). */
export const COR_AGUA = { claro: '#1F4C60', escuro: '#0E2430' } as const;

export type MaterialAgua = THREE.ShaderMaterial & {
  uniforms: { uTempo: THREE.IUniform<number>; uAgua: THREE.IUniform<THREE.Color> };
};

export function materialDaAgua(ceu: CoresCeu): MaterialAgua {
  return new THREE.ShaderMaterial({
    name: 'agua',
    uniforms: {
      uTempo: { value: 0 },
      uAlcance: { value: 16000 },
      uAgua: { value: new THREE.Color(COR_AGUA.claro) },
      // Mesmas instâncias do céu (sem clonar): trocar o modo de cor muda a água junto.
      uZenite: { value: ceu.zenite },
      uFaixa: { value: ceu.faixa },
      uHorizonte: { value: ceu.horizonte },
      uSolDirecao: { value: ceu.sol },
    },
    vertexShader,
    fragmentShader,
    // O plano passa sob toda a terra do entorno, a centímetros dela nas baixadas e nas margens:
    // empurrado para trás na profundidade, o terreno ganha onde os dois quase coincidem e nada pisca.
    polygonOffset: true,
    polygonOffsetFactor: 1,
    polygonOffsetUnits: 1,
  }) as MaterialAgua;
}
