// O mar do entorno: reflexo do céu pelo Fresnel, ondas por normais procedurais (o disco tem poucos
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
  #include <fog_pars_vertex>
  varying vec3 vMundo;
  void main() {
    vec4 mundo = modelMatrix * vec4(position, 1.0);
    vMundo = mundo.xyz;
    vec4 mvPosition = viewMatrix * mundo;
    gl_Position = projectionMatrix * mvPosition;
    #include <fog_vertex>
  }
`;

const fragmentShader = /* glsl */ `
  #include <fog_pars_fragment>
  uniform float uTempo;
  uniform vec3 uAgua;
  uniform vec3 uZenite;
  uniform vec3 uFaixa;
  uniform vec3 uHorizonte;
  uniform vec3 uSolDirecao;
  varying vec3 vMundo;

  // Uma onda: direção, comprimento (m), velocidade (m/s) e inclinação. Devolve a derivada da altura.
  vec2 onda(vec2 p, vec2 dir, float comp, float vel, float incl) {
    float k = 6.2831853 / comp;
    float fase = k * (dot(p, dir) - vel * uTempo);
    return dir * (incl * cos(fase));
  }

  void main() {
    vec2 p = vMundo.xz;
    float dist = length(cameraPosition - vMundo);
    // Ondas curtas somem com a distância: de longe viram ruído e cintilam.
    float perto = 1.0 - smoothstep(600.0, 3500.0, dist);
    vec2 d = onda(p, normalize(vec2(0.8, 0.6)), 61.0, 4.1, 0.10)
           + onda(p, normalize(vec2(0.3, 0.95)), 37.0, 3.2, 0.08)
           + perto * (onda(p, normalize(vec2(-0.6, 0.8)), 17.0, 2.2, 0.07)
                    + onda(p, normalize(vec2(0.95, -0.2)), 9.0, 1.6, 0.05));
    vec3 n = normalize(vec3(-d.x, 1.0, -d.y));
    vec3 v = normalize(cameraPosition - vMundo);
    float fresnel = 0.02 + 0.98 * pow(1.0 - max(dot(n, v), 0.0), 5.0);
    vec3 r = reflect(-v, n);
    float ry = max(r.y, 0.0);
    vec3 ceu = mix(uHorizonte, uFaixa, smoothstep(0.0, 0.07, ry));
    ceu = mix(ceu, uZenite, smoothstep(0.07, 0.32, ry));
    vec3 cor = mix(uAgua, ceu, clamp(fresnel * 0.85, 0.0, 0.85));
    // Brilho do sol nas cristas, contido: a luz de apresentação não é a simulação do sol.
    float brilho = pow(max(dot(r, normalize(uSolDirecao)), 0.0), 180.0);
    cor += vec3(1.0, 0.95, 0.85) * brilho * 0.6;
    gl_FragColor = vec4(cor, 1.0);
    #include <colorspace_fragment>
    #include <fog_fragment>
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
    fog: true,
    uniforms: {
      ...THREE.UniformsUtils.clone(THREE.UniformsLib.fog),
      uTempo: { value: 0 },
      uAgua: { value: new THREE.Color(COR_AGUA.claro) },
      // Mesmas instâncias do céu (sem clonar): trocar o modo de cor muda a água junto.
      uZenite: { value: ceu.zenite },
      uFaixa: { value: ceu.faixa },
      uHorizonte: { value: ceu.horizonte },
      uSolDirecao: { value: ceu.sol },
    },
    vertexShader,
    fragmentShader,
  }) as MaterialAgua;
}
