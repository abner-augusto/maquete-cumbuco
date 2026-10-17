"""Gera o estande da planta v10c e o implanta pelo lote do KMZ.

Uso: uv run python -m scripts.marcos.estande
O DWG é convertido em cache; nenhum desenho de origem é alterado.
"""

import ast
import hashlib
import json
import math
import re
import shutil
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import ezdxf
import numpy as np
from ezdxf import path
from shapely import affinity, make_valid, voronoi_polygons
from shapely.geometry import LineString, MultiPoint, Point, Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

from scripts.comum.ambiente import RAIZ, ler_env, terreno_dir
from scripts.entorno.osm import Projecao
from scripts.loteamento.blender import BLENDER_PADRAO, PASTA_MAQUETE, rodar_blender
from scripts.loteamento.cena import CFG_TOML
from scripts.loteamento.converter_dwg import ACCORE_PADRAO, converter
from scripts.loteamento.geometria import pontos_de
from scripts.loteamento.malha import aninhar, triangular
from scripts.loteamento.placa import PlacaCfg
from scripts.loteamento.terreno import Relevo

CACHE = RAIZ / "cache" / "estande"
DESTINO = RAIZ / "dados" / "estande.json"
FONTE = "2026-10-09 estande - estudo de partido Abner v10c.dwg"
KMZ = "2026-10-07 estande - implantacao georreferenciada.kmz"
# As plantas não têm cortes executivos: estes acabamentos e alturas são interpretação dos renders.
ALTURA_FACHADA = 6.0
ALTURA_DIVISORIA = 2.8
BEIRAL = 1.0
LIMITE_BRUTO_MB = 4.0  # O build aplica Meshopt; o GLB editável do Blender é maior.


def partes(g):
    if g.is_empty:
        return []
    return list(g.geoms) if hasattr(g, "geoms") else [g]


def poligono(e):
    return make_valid(Polygon(pontos_de(e)))


def hachura(e):
    aneis = []
    for p in path.from_hatch(e):
        pts = [(v.x, v.y) for v in p.flattening(.01)]
        if len(pts) > 1 and math.dist(pts[0], pts[-1]) < 1e-6:
            pts.pop()
        if len(pts) >= 3:
            aneis.append(pts)
    return unary_union([make_valid(Polygon(a, furos)) for a, furos in aninhar(aneis)])


def implantacao(doc, arquivo_kmz):
    """Encaixe rígido pelo segmento de frente do lote, sem escalar a edificação."""
    ns = {"k": "http://www.opengis.net/kml/2.2"}
    with zipfile.ZipFile(arquivo_kmz) as z:
        kml = ET.fromstring(z.read(next(n for n in z.namelist() if n.endswith(".kml"))))
    lote_kmz = next(p for p in kml.findall(".//k:Placemark", ns)
                    if p.findtext("k:name", "", ns).startswith("Lote Multifamiliar"))
    coords = lote_kmz.find(".//k:coordinates", ns).text
    ll = [tuple(map(float, p.split(",")[:2])) for p in coords.split()]
    if ll[0] == ll[-1]:
        ll.pop()
    geo = json.loads((RAIZ / "dados/georref.json").read_text(encoding="utf-8"))
    proj = Projecao(geo["origem"]["E"], geo["origem"]["N"])
    destino = [proj.xy(lon, lat) for lon, lat in ll]
    lote = poligono(next(e for e in doc.modelspace() if e.dxf.layer == "TER-LOTE"))
    src = list(lote.exterior.coords)[:-1]
    if len(src) != len(destino):
        raise ValueError("Os lotes do DWG e do KMZ têm quantidades diferentes de vértices.")
    pares = list(zip(src, src[1:] + src[:1]))
    a, b = max(pares, key=lambda p: math.dist(*p))
    i = src.index(a)
    c, d = destino[i], destino[(i + 1) % len(destino)]
    if abs(math.dist(a, b) - math.dist(c, d)) > .15:
        raise ValueError("A frente do lote no DWG diverge do KMZ em mais de 15 cm.")
    theta = math.atan2(d[1]-c[1], d[0]-c[0]) - math.atan2(b[1]-a[1], b[0]-a[0])
    co, si = math.cos(theta), math.sin(theta)
    tx, ty = c[0] - co*a[0] + si*a[1], c[1] - si*a[0] - co*a[1]
    transf = [co, -si, si, co, tx, ty]
    ajustado = affinity.affine_transform(lote, transf)
    residuo = max(math.dist(affinity.affine_transform(Point(p), transf).coords[0], q)
                  for p, q in zip(src, destino))
    if residuo > .2:
        raise ValueError(f"Implantação do estande diverge do lote do KMZ: {residuo:.3f} m.")
    return lote, transf, residuo, ajustado


class Cena:
    """Extrusões agrupadas por componente e acabamento, mantendo os furos do CAD."""

    def __init__(self):
        self.objetos = {}

    def adicionar(self, nome, g, z0, z1, material, *, laterais=True):
        for p in partes(make_valid(g)):
            if p.geom_type != "Polygon" or p.area < 1e-6:
                continue
            p = orient(p)
            aneis = [list(r.coords)[:-1] for r in (p.exterior, *p.interiors)]
            xy, tris = triangular(aneis[0], aneis[1:])
            n = len(xy)
            vertices = [[x, y, z(x, y) if callable(z) else z] for z in (z0, z1) for x, y in xy]
            faces = [list(reversed(t)) for t in tris] + [[i+n for i in t] for t in tris]
            if laterais:
                inicio = 0
                for anel in aneis:
                    for i in range(len(anel)):
                        a, b = inicio+i, inicio+(i+1) % len(anel)
                        faces.append([a, b, b+n, a+n])
                    inicio += len(anel)
            self.malha(nome, vertices, faces, material)

    def malha(self, nome, vertices, faces, material):
        o = self.objetos.setdefault((nome, material), {"nome": nome, "material": material,
                                                     "vertices": [], "faces": []})
        inicio = len(o["vertices"])
        o["vertices"].extend(vertices)
        o["faces"].extend([[i+inicio for i in face] for face in faces])

    def linha(self, nome, pts, z0, z1, largura, mat):
        self.adicionar(nome, LineString(pts).buffer(largura/2, cap_style=2, join_style=2), z0, z1, mat)

    def coqueiro(self, x, y, raio, z):
        altura = raio*3.2
        self.adicionar("Paisagismo_troncos", Point(x,y).buffer(.13, quad_segs=6), z, z+altura, "tronco")
        for k in range(9):
            a = 2*math.pi*k/9 + x
            vertices = []
            for t in (0, .35, .7, 1):
                r, w = t*raio*1.2, math.sin(t*math.pi)*.2
                h = altura + .65*math.sin(t*math.pi) - t*.5
                for lado in (-1, 1):
                    vertices.append([x+r*math.cos(a)-lado*w*math.sin(a),
                                     y+r*math.sin(a)+lado*w*math.cos(a), z+h])
            self.malha("Paisagismo_folhas", vertices, [(0,1,3,2),(2,3,5,4),(4,5,7,6)], "folhagem")


def espreguicadeira(cena, g, piso):
    """Estrutura vazada e almofada com encosto inclinado, na pegada do CAD."""
    x0, y0, x1, y1 = g.bounds
    juncao = y0 + (y1-y0)*.36
    encosto = lambda x,y: piso+.42+.48*(juncao-y)/(juncao-y0)
    for x in (x0+.045, x1-.09):
        cena.adicionar("Espreguicadeiras_estrutura", box(x,y0+.08,x+.045,y1-.06),
                       piso+.32, piso+.4, "madeira")
        cena.adicionar("Espreguicadeiras_encostos_estrutura", box(x,y0+.04,x+.045,juncao),
                       lambda x,y: encosto(x,y)-.05, encosto, "madeira")
        for y in (y0+.3, y1-.3):
            cena.adicionar("Espreguicadeiras_pes", box(x,y,x+.045,y+.055),
                           piso, piso+.32, "madeira")
    cena.adicionar("Espreguicadeiras_assentos", box(x0+.035,juncao,x1-.035,y1-.04),
                   piso+.41, piso+.47, "tecido")
    cena.adicionar("Espreguicadeiras_encostos", box(x0+.035,y0+.035,x1-.035,juncao),
                   encosto, lambda x,y: encosto(x,y)+.06, "tecido")


def preparar(doc, pasta):
    msp = doc.modelspace()
    lote, transf, residuo, _ = implantacao(doc, pasta / KMZ)
    volumes = [poligono(e) for e in msp if e.dxf.layer == "A-VOLUME"]
    if len(volumes) != 2:
        raise ValueError("A planta do estande deve ter dois volumes na camada A-VOLUME.")
    edificio = unary_union(volumes)
    deck = unary_union([poligono(e) for e in msp if e.dxf.layer == "A-DECK"])
    dominio = box(*lote.bounds)
    cena = Cena()
    textos = " ".join(e.dxf.text for e in msp.query("TEXT"))
    mezz = float(re.search(r"MEZANINO\s*\+(\d+[.,]\d+)", textos).group(1).replace(",", "."))
    piso = float(re.search(r"\+0,(\d+)", textos).group(0).replace(",", "."))
    # O deslocamento da planta do mezanino vem do script que gerou o desenho.
    arvore = ast.parse((pasta / "build_v10.py").read_text(encoding="utf-8-sig"))
    off = next(ast.literal_eval(n.value) for n in arvore.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == "MEZ_OFF" for t in n.targets))
    exterior = edificio.boundary.buffer(.3)
    hatches = [(e, hachura(e)) for e in msp.query("HATCH")
               if e.dxf.layer in {"A-PAREDE", "A-ESQUADRIA", "A-BRISE", "A-VEGETACAO"}]
    cena.adicionar("Piso_gramado", lote, -.05, .025, "gramado")
    cena.adicionar("Piso_terreo", edificio, -.08, piso, "piso")
    for e in msp.query("LWPOLYLINE"):
        if (not e.closed and e.dxf.layer != "A-VAGAS") or len(e) < 3:
            continue
        g = poligono(e)
        if not dominio.covers(g):
            continue
        lay = e.dxf.layer
        if lay == "A-DECK":
            cena.adicionar("Deck", g, .03, piso, "madeira")
            for y in np.arange(g.bounds[1], g.bounds[3], .22):
                junta = box(g.bounds[0], y, g.bounds[2], y+.012).intersection(g)
                cena.adicionar("Deck_juntas", junta, piso, piso+.004, "madeira_escura")
        elif lay == "A-ESPELHO-AGUA":
            cena.adicionar("Espelho_bordas", g.buffer(.12).difference(g), .03, piso-.07, "pedra")
            cena.adicionar("Espelho_agua", g, .08, piso-.14, "agua")
        elif lay == "A-VAGAS":
            cena.adicionar("Estacionamento", g, .025, .07, "asfalto")
            cena.adicionar("Estacionamento_faixas", g.boundary.buffer(.035), .071, .075, "piso")
        elif lay == "A-CAMINHO":
            cena.adicionar("Caminhos", g, .03, .12, "piso")
        elif lay == "A-RAMPA":
            y0, y1 = g.bounds[1], g.bounds[3]
            cena.adicionar("Rampa", g, .02, lambda x,y: .12+(piso-.12)*(y-y0)/(y1-y0), "piso")
        elif lay == "A-PEDRA":
            cena.adicionar("Fachada_pedra", g, piso, piso+ALTURA_FACHADA-.25, "pedra")
            # Placas irregulares em relevo, sem texturas ou inscrições das imagens de referência.
            x0, y0, x1, _ = g.bounds
            rng = np.random.default_rng(17)
            sementes = MultiPoint([(x,z) for x in np.arange(x0-.5,x1+.5,.55)
                                   for z in np.arange(piso-.5,piso+ALTURA_FACHADA,.5)]
                                  + [(float(rng.uniform(x0,x1)),float(rng.uniform(piso,piso+5.7)))
                                     for _ in range(35)])
            for cell in voronoi_polygons(sementes).geoms:
                cell = cell.intersection(box(x0,piso,x1,piso+ALTURA_FACHADA-.25)).buffer(-.018)
                for p in partes(cell):
                    if p.geom_type != "Polygon" or p.area < .002:
                        continue
                    xy, tris = triangular(list(p.exterior.coords)[:-1], [])
                    cena.malha("Fachada_pedra_relevo", [[x,y0-.025,z] for x,z in xy], tris, "pedra_relevo")
        elif lay == "A-COBERTURA":
            cena.adicionar("Cobertura_marquisinha", g, piso+3.1, piso+3.26, "madeira")
    for e, g in hatches:
        if not dominio.covers(g):
            # A planta do mezanino foi deslocada no DWG para não sobrepor o térreo.
            local = affinity.translate(g, -off[0], -off[1])
            if not edificio.buffer(.3).covers(local) or g.centroid.y >= 0:
                continue
            if e.dxf.layer == "A-PAREDE":
                cena.adicionar("Mezanino_paredes", local, piso+mezz, piso+5.8, "parede")
            elif e.dxf.layer == "A-ESQUADRIA":
                baixo = local.area < .25
                cena.adicionar("Mezanino_vidros", local, piso+mezz, piso+mezz+(1.1 if baixo else 2.5), "vidro")
            continue
        lay = e.dxf.layer
        if lay == "A-PAREDE" and e.rgb and e.rgb.r < 80:
            cena.adicionar("Paredes_internas", g.difference(exterior), piso, piso+ALTURA_DIVISORIA, "parede")
            cena.adicionar("Paredes_externas", g.intersection(exterior), piso, piso+ALTURA_FACHADA, "parede")
        elif lay == "A-ESQUADRIA":
            fora = g.intersection(exterior)
            dentro = g.difference(exterior)
            cena.adicionar("Vidros_internos", dentro, piso, piso+2.75, "vidro")
            alto = fora.centroid.x > 42 if not fora.is_empty else False
            if alto or (not fora.is_empty and fora.centroid.y > 26):
                cena.adicionar("Vidros_servico", fora, piso+1.4, piso+2.5, "vidro")
                cena.adicionar("Paredes_peitoris", fora, piso, piso+1.4, "parede")
                cena.adicionar("Paredes_vergas", fora, piso+2.5, piso+ALTURA_FACHADA, "parede")
            else:
                cena.adicionar("Fachada_vidro", fora, piso, piso+ALTURA_FACHADA, "vidro")
        elif lay == "A-BRISE":
            if e.rgb and e.rgb.r < 120:
                # As ripas seguem a posição e a orientação do CAD; a borda inferior ondula como nos renders.
                altura = .6 + .75*(1+math.sin(g.centroid.x*.55))/2
                cena.adicionar("Brises", g, piso+ALTURA_FACHADA-altura,
                               piso+ALTURA_FACHADA-.05, "madeira")
            else:
                cena.adicionar("Brises_trilhos", g, piso+ALTURA_FACHADA-.12, piso+ALTURA_FACHADA, "madeira_escura")
        elif lay == "A-VEGETACAO":
            if e.dxf.color == 92:
                cena.coqueiro(g.centroid.x, g.centroid.y, math.sqrt(g.area/math.pi), .03)
            elif g.area > .08:
                if deck.covers(g) and g.area > 4:
                    cena.adicionar("Deck_grama_pet", g, piso+.004, piso+.014, "gramado")
                    continue
                z = piso if edificio.buffer(.5).covers(g.centroid) else .04
                if z == piso:
                    cena.adicionar("Vasos", g.buffer(.06), z, z+.5, "pedra")
                cena.adicionar("Paisagismo_arbustos", g, z+.1, z+.6, "folhagem")
    # Montantes e travessas acompanham os trechos envidraçados do perímetro real.
    vidros = unary_union([g for e,g in hatches if e.dxf.layer == "A-ESQUADRIA" and dominio.covers(g)])
    for linha in partes(edificio.boundary.intersection(vidros.buffer(.06))):
        if linha.geom_type != "LineString" or linha.length < .2:
            continue
        for z in (piso+.04, piso+3.25, piso+ALTURA_FACHADA-.04):
            cena.adicionar("Esquadrias_travessas", linha.buffer(.035, cap_style=2), z, z+.07, "metal")
        for d in np.linspace(0, linha.length, max(2, math.ceil(linha.length/1.3)+1)):
            p = linha.interpolate(d)
            cena.adicionar("Esquadrias_montantes", box(p.x-.045,p.y-.045,p.x+.045,p.y+.045),
                           piso, piso+ALTURA_FACHADA, "metal")
    # Lajes do mezanino: união dos ambientes da planta deslocada.
    salas_mezz = [affinity.translate(poligono(e), -off[0], -off[1]) for e in msp.query("LWPOLYLINE")
                  if e.closed and e.dxf.layer in {"A-SETOR-CLIENTE", "A-SETOR-CORRETOR"}
                  and all(y < 0 for _,y,*_ in e.get_points())]
    cena.adicionar("Mezanino_laje", unary_union(salas_mezz), piso+mezz-.16, piso+mezz, "piso")
    # Mobiliário dos contornos do CAD, sem textos, cotas ou desenhos de abertura de portas.
    chaises = []
    for e in msp.query("LWPOLYLINE"):
        if e.dxf.layer != "A-MOB-H" or not e.closed:
            continue
        g = poligono(e)
        x0,y0,x1,y1 = g.bounds
        if deck.covers(g) and .5 < x1-x0 < 1 and 1.6 < y1-y0 < 2.3 and g.area > .95*(x1-x0)*(y1-y0):
            chaises.append(g)
            espreguicadeira(cena, g, piso)
    for e in msp.query("LWPOLYLINE"):
        if e.dxf.layer not in {"A-MOB-H", "A-MOBILIARIO", "A-PORTA-H", "A-HOLOBOX"} or not e.closed:
            continue
        g = poligono(e)
        if not dominio.covers(g) or not .015 < g.area < 20:
            continue
        if deck.covers(g):
            # Contornos de pergolado e área pet são marcações de planta, não blocos de mobiliário.
            if g.area > 6 or any(c.buffer(.001).covers(g) for c in chaises):
                continue
        if e.dxf.layer == "A-PORTA-H":
            cena.adicionar("Portas", g, piso, piso+2.2, "madeira")
            continue
        if e.dxf.layer == "A-HOLOBOX":
            cena.adicionar("Holobox", g, piso, piso+2.06, "metal")
            continue
        circular = 4*math.pi*g.area/(g.length*g.length) > .9
        if circular:
            h = .76 if g.area > .22 else .46
            cena.adicionar("Mobiliario_tampos", g, piso+h-.08, piso+h, "madeira")
            cena.adicionar("Mobiliario_pes", g.buffer(-math.sqrt(g.area/math.pi)*.75), piso, piso+h-.08, "metal")
        elif g.area < .32:
            cena.adicionar("Mobiliario_assentos", g, piso+.4, piso+.5, "tecido")
            if g.area < .06:
                cena.adicionar("Mobiliario_encostos", g, piso+.5, piso+.85, "tecido")
        else:
            h = 1.05 if g.area > 2 else .74
            cena.adicionar("Mobiliario", g, piso, piso+h, "madeira")
    # Degraus da escada curva: os riscos de piso já estão ordenados na camada de mobiliário.
    degraus = []
    for e in msp.query("LWPOLYLINE"):
        pts = pontos_de(e)
        if e.dxf.layer == "A-MOB-H" and len(pts) == 2 and all(33 < x < 37 and 10 < y < 14.5 for x,y in pts):
            degraus.append(pts)
    for i,(a,b) in enumerate(zip(degraus,degraus[1:])):
        cena.adicionar("Escada_curva", Polygon([a[0],a[1],b[1],b[0]]),
                       piso+mezz*i/max(1,len(degraus)-1), piso+mezz*(i+1)/max(1,len(degraus)-1), "madeira")
    cobertura = edificio.buffer(BEIRAL, join_style=1)
    # O arremate fecha a borda inteira; forro e laje não repetem suas faces laterais.
    cena.adicionar("Cobertura_forro", cobertura, piso+ALTURA_FACHADA, piso+ALTURA_FACHADA+.12,
                   "madeira", laterais=False)
    cena.adicionar("Cobertura_laje", cobertura, piso+ALTURA_FACHADA+.12, piso+ALTURA_FACHADA+.36,
                   "cobertura", laterais=False)
    cena.adicionar("Cobertura_fascia", cobertura.difference(cobertura.buffer(-.15)),
                   piso+ALTURA_FACHADA-.12, piso+ALTURA_FACHADA+.38, "madeira_escura")
    cena.adicionar("Cobertura_luz", cobertura.boundary.buffer(.018),
                   piso+ALTURA_FACHADA-.13, piso+ALTURA_FACHADA-.10, "luz")
    # Centro e pegada atuais vêm da v10c, e não do volume antigo contido no KMZ.
    implantado = affinity.affine_transform(edificio, transf)
    relevo = Relevo.carregar()
    # O estande assenta no topo do lote (a placa o ergue acima do platô); na cota do platô, o
    # estacionamento e a rampa, de poucos centímetros, ficavam enterrados.
    z = relevo.cota(implantado.centroid.x, implantado.centroid.y) + PlacaCfg.carregar(CFG_TOML).alturas["lote"]
    meta = {"versao": 1, "objeto": "Estande", "modelo": "estande.glb", "fonte": FONTE,
            "sha256_dwg": hashlib.sha256((pasta/FONTE).read_bytes()).hexdigest(),
            "implantacao": KMZ, "residuo_implantacao_m": round(residuo,4),
            "transformacao": transf, "x": round(implantado.centroid.x,2),
            "y": round(implantado.centroid.y,2), "z": round(z,3),
            "pegada": [[round(x,3),round(y,3)] for x,y in list(implantado.exterior.coords)[:-1]],
            "area_edificacao_m2": round(edificio.area,2), "piso_terreo_m": piso,
            "mezanino_m": mezz, "altura_fachada_m": ALTURA_FACHADA,
            "observacao": "Alturas de fachada e cobertura interpretadas dos renders; dimensões em planta extraídas do DWG."}
    return {"objetos": list(cena.objetos.values()), "implantacao": meta}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    pasta = terreno_dir() / "6-PROJETOS/08-ESTANDE"
    CACHE.mkdir(parents=True, exist_ok=True)
    dxf = CACHE / "estande.dxf"
    if not dxf.exists() or dxf.stat().st_mtime < (pasta/FONTE).stat().st_mtime:
        copia = CACHE / "estande.dwg"
        shutil.copy2(pasta/FONTE, copia)
        converter(copia, dxf, Path(ler_env(RAIZ/".env").get("ACCORE", ACCORE_PADRAO)))
    cena = preparar(ezdxf.readfile(dxf), pasta)
    arquivo = CACHE / "cena.json"
    arquivo.write_text(json.dumps(cena), encoding="utf-8")
    destino = terreno_dir() / PASTA_MAQUETE / "estande.glb"
    resumo = rodar_blender(Path(ler_env(RAIZ/".env").get("BLENDER", BLENDER_PADRAO)),
                           RAIZ/"scripts/blender/gerar_estande.py", str(arquivo), str(destino), str(CACHE))
    if resumo["glb_mb"] > LIMITE_BRUTO_MB:
        raise ValueError(f"O estande ultrapassou o orçamento bruto de {LIMITE_BRUTO_MB} MB.")
    DESTINO.write_text(json.dumps(cena["implantacao"], ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(resumo, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
