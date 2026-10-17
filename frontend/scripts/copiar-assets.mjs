// Monta o public/ a partir das fontes de verdade (spec §3): dados/, marca/ e os GLBs da pasta do
// terreno. Nada daqui é editado à mão; rode de novo depois de regerar o pipeline Python.
import { copyFile, cp, mkdir, readdir, rm, writeFile } from 'node:fs/promises';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const FRONT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const RAIZ = path.resolve(FRONT, '..');
const PUBLIC = path.join(FRONT, 'public');
const LARGURAS = { '-mini': 480, '': 1920 };

export function fotosCitadas(marcos, pontos) {
  const todas = [
    ...marcos.marcos.flatMap(m => [...m.galeria.map(g => g.foto), m.planta]),
    ...pontos.pontos.map(p => p.foto),
  ];
  return [...new Set(todas.filter(Boolean))];
}

export const ativa = caminho => caminho.replaceAll('\\', '/').includes('/svg/americas/');

function terrenoDir() {
  const env = readFileSyncTexto(path.join(RAIZ, '.env'));
  const linha = env.split(/\r?\n/).find(l => l.startsWith('TERRENO_DIR='));
  if (!linha) throw Error('TERRENO_DIR ausente no .env da raiz');
  return linha.slice('TERRENO_DIR='.length).trim().replace(/^"|"$/g, '');
}

const readFileSyncTexto = p => readFileSync(p, 'utf8');

/**
 * Meshopt com as posições em 16 bits (o padrão, 14, dá passos de 24 cm numa janela de 4 km do
 * entorno: a terra baixa, a 20 cm da água, caía no plano dela e piscava; em 16 bits o passo é de 6 cm).
 */
export async function comprimirDocumento(doc) {
  const { meshopt } = await import('@gltf-transform/functions');
  const { MeshoptEncoder } = await import('meshoptimizer');
  await MeshoptEncoder.ready;
  await doc.transform(meshopt({ encoder: MeshoptEncoder, level: 'medium', quantizePosition: 16 }));
}

async function comprimir(origem, destino) {
  const { NodeIO } = await import('@gltf-transform/core');
  const { ALL_EXTENSIONS } = await import('@gltf-transform/extensions');
  const { MeshoptEncoder, MeshoptDecoder } = await import('meshoptimizer');
  const io = new NodeIO().registerExtensions(ALL_EXTENSIONS)
    .registerDependencies({ 'meshopt.encoder': MeshoptEncoder, 'meshopt.decoder': MeshoptDecoder });
  const doc = await io.read(origem);
  await comprimirDocumento(doc);
  await io.write(destino, doc);
}

async function webp(origem, base) {
  const sharp = (await import('sharp')).default;
  for (const [sufixo, largura] of Object.entries(LARGURAS))
    await sharp(origem).rotate().resize({ width: largura, withoutEnlargement: true }).webp({ quality: 80 }).toFile(`${base}${sufixo}.webp`);
}

async function main() {
  const maquete = path.join(terrenoDir(), '6-PROJETOS', '10-MAQUETE INTERATIVA');
  // Só as pastas geradas: o _headers do public/ é versionado e fica.
  for (const pasta of ['dados', 'modelos', 'draco', 'marca']) {
    await rm(path.join(PUBLIC, pasta), { recursive: true, force: true });
    await mkdir(path.join(PUBLIC, pasta), { recursive: true });
  }

  const json = n => JSON.parse(readFileSyncTexto(path.join(RAIZ, 'dados', n)));
  for (const n of ['lotes.json', 'marcos.json', 'pontos.json', 'fases.json', 'config.json'])
    await copyFile(path.join(RAIZ, 'dados', n), path.join(PUBLIC, 'dados', n));
  for (const foto of fotosCitadas(json('marcos.json'), json('pontos.json'))) {
    const origem = path.join(RAIZ, 'dados', foto);
    if (!existsSync(origem)) throw Error(`foto citada e ausente: dados/${foto}`);
    const base = path.join(PUBLIC, 'dados', foto.replace(/\.[^.]+$/, ''));
    await mkdir(path.dirname(base), { recursive: true });
    await webp(origem, base);
  }

  for (const n of ['loteamento', 'entorno', 'vegetacao', 'orla'])
    await comprimir(path.join(maquete, `${n}.glb`), path.join(PUBLIC, 'modelos', `${n}.glb`));
  await copyFile(path.join(maquete, 'marcos.glb'), path.join(PUBLIC, 'modelos', 'marcos.glb'));
  await copyFile(path.join(maquete, 'vegetacao.json'), path.join(PUBLIC, 'modelos', 'vegetacao.json'));
  // O chão só com OSM, para o botão do masterplan: um JPEG por tile do mapa.
  for (const k of ['00', '01', '10', '11'])
    await copyFile(path.join(maquete, `mapa-osm_${k}.jpg`), path.join(PUBLIC, 'modelos', `mapa-osm_${k}.jpg`));
  await cp(path.join(FRONT, 'node_modules/three/examples/jsm/libs/draco/gltf'), path.join(PUBLIC, 'draco'), { recursive: true });

  const svgs = path.join(RAIZ, 'marca', 'svg', 'americas');
  for (const n of await readdir(svgs)) if (ativa(path.join(svgs, n))) await copyFile(path.join(svgs, n), path.join(PUBLIC, 'marca', n));
  await mkdir(path.join(FRONT, 'src', 'estilos', 'temas'), { recursive: true });
  await writeFile(path.join(FRONT, 'src', 'estilos', 'temas', 'americas.css'), readFileSyncTexto(path.join(RAIZ, 'marca', 'tokens.css')));
  console.log('public/ montado');
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) await main();
