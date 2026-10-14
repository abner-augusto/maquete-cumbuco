"""Cena 3D do loteamento em JSON (malhas prontas). O Blender só constrói o que está aqui.

Uso: uv run python -m scripts.loteamento.cena
"""

import json
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import ezdxf
from ezdxf import path as ezpath

from scripts.comum.ambiente import RAIZ

from .geometria import Ponto, area, contem, poligono_fechado, pontos_de
from .malha import aninhar, drapear, refinar, simplificar, triangular
from .relevo import DESTINO as RELEVO_JSON
from .relevo import Grade, mascara, suavizar_dentro

DXF = RAIZ / "cache" / "dxf" / "planta-venda.dxf"
CFG_TOML = RAIZ / "scripts" / "loteamento" / "cena.toml"
DESTINO = RAIZ / "cache" / "cena" / "loteamento.json"


@dataclass(frozen=True)
class CenaCfg:
    camadas: dict[str, list[str]]
    lagoa_camadas: list[str]
    lagoa_texto: str
    offsets: dict[str, float]
    tolerancia: float
    max_aresta: float
    poligonal: list[str] = field(default_factory=list)  # loteamento terraplenado: relevo suave dentro
    sigma: float = 8.0
    transicao: float = 20.0
    rebaixo: float = 0.6  # terreno escondido sob as áreas desce, para não furar

    @classmethod
    def carregar(cls, caminho: Path) -> "CenaCfg":
        return cls(**tomllib.loads(caminho.read_text(encoding="utf-8")))


def aneis_da_layer(msp, layers: list[str], e0: float, n0: float) -> list[list[Ponto]]:
    aneis = []
    for e in msp:
        if e.dxf.layer not in layers:
            continue
        if e.dxftype() == "LWPOLYLINE" and poligono_fechado(e):
            pts = pontos_de(e, 0.1)
        elif e.dxftype() == "CIRCLE":
            pts = [(v.x, v.y) for v in ezpath.make_path(e).flattening(distance=0.02)][:-1]  # ilha de rotatória: fiel à área
        else:
            continue
        aneis.append([(x - e0, y - n0) for x, y in pts])
    return aneis


def achar_lagoa(msp, cfg: CenaCfg, e0: float, n0: float) -> list[Ponto] | None:
    alvos = [
        (t.dxf.insert.x - e0, t.dxf.insert.y - n0)
        for t in msp.query("TEXT MTEXT")
        if cfg.lagoa_texto in (t.dxf.text if t.dxftype() == "TEXT" else t.plain_text()).upper()
    ]
    candidatos = [a for a in aneis_da_layer(msp, cfg.lagoa_camadas, e0, n0) if any(contem(a, p) for p in alvos)]
    return min(candidatos, key=area) if candidatos else None


def _malha(grupos, grade: Grade, offset: float, cfg: CenaCfg) -> tuple[list[list[float]], list[list[int]]]:
    vertices, faces = [], []
    for externo, furos in grupos:
        v, t = triangular(simplificar(externo, cfg.tolerancia), [simplificar(f, cfg.tolerancia) for f in furos])
        v, t = refinar(v, t, cfg.max_aresta)
        base = len(vertices)
        vertices += drapear(v, grade, offset)
        faces += [[base + a, base + b, base + c] for a, b, c in t]
    return vertices, faces


def _terreno(grade: Grade, sob: list[list[Ponto]] | None = None, rebaixo: float = 0.0) -> dict:
    """Grade do relevo; dentro dos anéis `sob` (coberto pelas áreas) o terreno desce `rebaixo`."""
    baixo = mascara(grade, sob) if sob else None
    vs = [[round(grade.x0 + i * grade.passo, 2), round(grade.y0 + j * grade.passo, 2),
           round(grade.z[j][i] - (rebaixo if baixo is not None and baixo[j, i] else 0.0), 2)]
          for j in range(grade.ny) for i in range(grade.nx)]
    fs = []
    for j in range(grade.ny - 1):
        for i in range(grade.nx - 1):
            a = j * grade.nx + i
            fs += [[a, a + 1, a + grade.nx + 1], [a, a + grade.nx + 1, a + grade.nx]]
    return {"nome": "Terreno", "material": "terreno", "vertices": vs, "faces": fs}


def montar(msp, grade: Grade, lotes: list[dict], cfg: CenaCfg, e0: float, n0: float) -> dict:
    poligonal = aneis_da_layer(msp, cfg.poligonal, e0, n0)
    if poligonal:
        grade = suavizar_dentro(grade, poligonal, cfg.sigma, cfg.transicao)
    objetos = [_terreno(grade, poligonal, cfg.rebaixo)]
    lagoa = achar_lagoa(msp, cfg, e0, n0)
    for papel, layers in cfg.camadas.items():
        aneis = aneis_da_layer(msp, layers, e0, n0)
        if not aneis:
            continue
        if lagoa and lagoa not in aneis and any(contem(a, lagoa[0]) for a in aneis):
            aneis = aneis + [lagoa]  # a água fura a área que a contém
        v, f = _malha(aninhar(aneis), grade, cfg.offsets[papel], cfg)
        objetos.append({"nome": papel, "material": papel.lower(), "vertices": v, "faces": f})
    if lagoa:
        nivel = sum(grade.cota(x, y) for x, y in lagoa) / len(lagoa)  # nível médio da margem
        v, t = triangular(simplificar(lagoa, cfg.tolerancia), [])
        objetos.append({"nome": "Lagoa", "material": "agua",
                        "vertices": [[round(x, 2), round(y, 2), round(nivel, 2)] for x, y in v],
                        "faces": [list(f) for f in t]})
    for l in lotes:
        anel = [(x, y) for x, y in l["poligono"]]
        v, f = _malha([(anel, [])], grade, cfg.offsets["lote"], cfg)
        objetos.append({"nome": l["id"], "material": f"lote_{l['tipo']}", "vertices": v, "faces": f})
    return {"objetos": objetos}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    georref = json.loads((RAIZ / "dados" / "georref.json").read_text(encoding="utf-8"))
    e0, n0 = georref["origem"]["E"], georref["origem"]["N"]
    lotes = json.loads((RAIZ / "dados" / "lotes.json").read_text(encoding="utf-8"))["lotes"]
    grade = Grade.de_json(json.loads(RELEVO_JSON.read_text(encoding="utf-8")))
    cena = montar(ezdxf.readfile(DXF).modelspace(), grade, lotes, CenaCfg.carregar(CFG_TOML), e0, n0)
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(cena), encoding="utf-8")
    tris = {o["nome"]: len(o["faces"]) for o in cena["objetos"]}
    lotes_n = sum(1 for n in tris if n.startswith("Q"))
    print(f"{len(tris)} objetos ({lotes_n} lotes) · {sum(tris.values())} triângulos · "
          + ", ".join(f"{n} {t}" for n, t in tris.items() if not n.startswith("Q")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
