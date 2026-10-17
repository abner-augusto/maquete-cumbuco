"""dados/marcos.json (contrato com o front) e fotos da galeria reduzidas.

Uso: uv run python -m scripts.marcos.dados
"""

import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

from PIL import Image
from shapely.geometry import Polygon

from scripts.comum.ambiente import RAIZ, terreno_dir
from scripts.entorno.osm import Projecao

from .encaixe import DESTINO as MARCOS_JSON
from .encaixe import MarcosCfg
from .estande import DESTINO as ESTANDE_JSON

CURADORIA = RAIZ / "scripts" / "marcos" / "curadoria.json"
DESTINO = RAIZ / "dados" / "marcos.json"
FOTOS = RAIZ / "dados" / "marcos"
PLANTA_KMZ = "files/planta_humanizada.jpg"
LADO_PLANTA = 2400  # a planta é ampliada na tela: mais lado que as fotos (1600)


def estande_do_kmz(kml: str) -> list[tuple[float, float]]:
    m = re.search(r"<name>Estande \(edificacao\)</name>.*?<coordinates>(.*?)</coordinates>", kml, re.S)
    if not m:
        raise SystemExit("KMZ do estande sem o polígono 'Estande (edificacao)'")
    pts = [tuple(float(v) for v in c.split(",")[:2]) for c in m.group(1).split()]
    return pts[:-1] if pts[0] == pts[-1] else pts


def reduzir(origem: Path, destino: Path, lado: int = 1600) -> None:
    Image.MAX_IMAGE_PIXELS = None
    img = Image.open(origem).convert("RGB")
    img.thumbnail((lado, lado))
    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino, quality=82)


def faltantes(curadoria: dict, raiz: Path) -> list[str]:
    arquivos = [a for m in curadoria.values() for a in [*(f["arquivo"] for f in m["fotos"]), m.get("planta")] if a]
    return [a for a in arquivos if not (raiz / a).exists()]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = MarcosCfg.carregar()
    raiz = terreno_dir()
    curadoria = json.loads(CURADORIA.read_text(encoding="utf-8"))
    if falta := faltantes(curadoria, raiz):
        raise SystemExit("fotos da curadoria que não existem:\n" + "\n".join(falta))
    georref = json.loads((RAIZ / "dados" / "georref.json").read_text(encoding="utf-8"))
    proj = Projecao(georref["origem"]["E"], georref["origem"]["N"])
    encaixe = json.loads(MARCOS_JSON.read_text(encoding="utf-8"))
    with zipfile.ZipFile(raiz / cfg.kmz_estande) as z:
        kml = z.read(next(n for n in z.namelist() if n.endswith(".kml"))).decode("utf-8")
        planta = z.read(PLANTA_KMZ)
    estande = Polygon([proj.xy(lon, lat) for lon, lat in estande_do_kmz(kml)])
    modelo_estande = json.loads(ESTANDE_JSON.read_text(encoding="utf-8")) if ESTANDE_JSON.exists() else None
    shutil.rmtree(FOTOS, ignore_errors=True)
    saida = []
    for id_, m in curadoria.items():
        if id_ == "estande" and modelo_estande:
            x, y, z = (modelo_estande[k] for k in ("x", "y", "z"))
        elif m["objeto"]:
            e = encaixe["marcos"][m["objeto"]]
            c = Polygon(e["pegada"]).centroid
            x, y, z = c.x, c.y, e["z"]
        else:
            c = estande.centroid
            x, y, z = c.x, c.y, encaixe["cota"]
        lon, lat = proj.lonlat(x, y)
        galeria = []
        for k, f in enumerate(m["fotos"], 1):
            nome = f"{id_}/{k:02d}.jpg"
            reduzir(raiz / f["arquivo"], FOTOS / nome)
            galeria.append({"foto": f"marcos/{nome}", "legenda": f["legenda"]})
        item = {"id": id_, "nome": m["nome"], "x": round(x, 2), "y": round(y, 2), "z": round(z, 2),
                "objeto": m["objeto"], "galeria": galeria, "planta": None,
                "lat": round(lat, 7), "lon": round(lon, 7)}
        if id_ == "estande":
            if modelo_estande:
                item["objeto"] = modelo_estande["objeto"]
            (FOTOS / "estande").mkdir(parents=True, exist_ok=True)
            if m.get("planta"):  # a planta humanizada da curadoria vale mais que a do KMZ
                reduzir(raiz / m["planta"], FOTOS / "estande" / "planta.jpg", LADO_PLANTA)
            else:
                (FOTOS / "estande" / "planta.jpg").write_bytes(planta)
                reduzir(FOTOS / "estande" / "planta.jpg", FOTOS / "estande" / "planta.jpg", LADO_PLANTA)
            item["planta"] = "marcos/estande/planta.jpg"
            item["pegada"] = (modelo_estande["pegada"] if modelo_estande else
                              [[round(px, 2), round(py, 2)] for px, py in estande.exterior.coords[:-1]])
        saida.append(item)
    DESTINO.write_text(json.dumps({"versao": 1, "marcos": saida}, ensure_ascii=False, indent=1), encoding="utf-8")
    mb = sum(p.stat().st_size for p in FOTOS.rglob("*.jpg")) / 1e6
    print(f"{len(saida)} marcos · {sum(len(m['galeria']) for m in saida)} fotos · {mb:.1f} MB em dados/marcos/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
