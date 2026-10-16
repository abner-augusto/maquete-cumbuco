"""Cena 3D do loteamento em JSON (malhas prontas). O Blender só constrói o que está aqui.

Uso: uv run python -m scripts.loteamento.cena
"""

import json
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

import ezdxf
from ezdxf import path as ezpath
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from scripts.comum.ambiente import RAIZ
from scripts.entorno.tiles import Ext, ext_da_grade, janelas

from .acesso import Acesso, AcessoCfg, montar_acesso, pecas_acesso
from .chao import malha_perto
from .geometria import Ponto, area, contem, poligono_fechado, pontos_de
from .malha import simplificar
from .placa import PlacaCfg, altura, montar_placa, particionar, poligonos
from .relevo import Grade

DXF = RAIZ / "cache" / "dxf" / "planta-venda.dxf"
CFG_TOML = RAIZ / "scripts" / "loteamento" / "cena.toml"
DESTINO = RAIZ / "cache" / "cena" / "loteamento.json"
TERRENO_JSON = RAIZ / "cache" / "cena" / "terreno.json"  # platô, morro e transição (terreno.py)
MARCOS_JSON = RAIZ / "cache" / "cena" / "marcos.json"  # pegadas dos marcos (scripts/marcos/encaixe.py)


@dataclass(frozen=True)
class CenaCfg:
    camadas: dict[str, list[str]]
    lagoa_camadas: list[str]
    lagoa_texto: str
    tolerancia: float

    @classmethod
    def carregar(cls, caminho: Path) -> "CenaCfg":
        d = tomllib.loads(caminho.read_text(encoding="utf-8"))
        return cls(**{k: d[k] for k in ("camadas", "lagoa_camadas", "lagoa_texto", "tolerancia")})


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


def pecas_da_placa(msp, lotes: list[dict], cfg: CenaCfg, placa_cfg: PlacaCfg, plato_aneis: list[list[Ponto]],
                   e0: float, n0: float) -> tuple[dict[str, BaseGeometry], BaseGeometry]:
    """Peças da placa (sem malhas) e o platô; o encaixe dos marcos usa a quadra central daqui."""
    # união, não aninhamento: os anéis do platô (poligonal, áreas, lotes) se sobrepõem, nenhum é furo
    plato = unary_union([Polygon(a).buffer(0) for a in plato_aneis if len(a) >= 3])
    lagoa = achar_lagoa(msp, cfg, e0, n0)
    papeis = {}
    for papel, layers in cfg.camadas.items():
        aneis = [a for a in aneis_da_layer(msp, layers, e0, n0) if a != lagoa]  # a lagoa é peça própria
        if aneis:
            papeis[papel] = poligonos(aneis, cfg.tolerancia)
    agua = None
    if lagoa:
        # a ilha (anel da layer da lagoa dentro dela) é APP; a APP que contém a lagoa perde para a água pela prioridade
        ilhas = [Polygon(a).buffer(0) for a in aneis_da_layer(msp, cfg.lagoa_camadas, e0, n0)
                 if a != lagoa and contem(lagoa, a[0]) and area(a) < area(lagoa)]
        agua = Polygon(simplificar(lagoa, cfg.tolerancia)).buffer(0).difference(unary_union(ilhas))
    lotes_g = {l["id"]: Polygon(l["poligono"]).buffer(0) for l in lotes}
    return particionar(plato, papeis, lotes_g, agua, placa_cfg), plato


def pegadas_dos_marcos() -> BaseGeometry | None:
    if not MARCOS_JSON.exists():
        print("cena: sem marcos (cache/cena/marcos.json): placa sem furos")
        return None
    marcos = json.loads(MARCOS_JSON.read_text(encoding="utf-8"))["marcos"]
    # o furo (chão de baixo do modelo dentro da pegada), não a pegada: onde o modelo não tem chão, a placa fica
    return unary_union([Polygon(p[0], p[1:]).buffer(0) for m in marcos.values() for p in m["furo"]])


def acesso_da_cena() -> "tuple[Acesso, AcessoCfg] | None":
    a = Acesso.carregar()
    if a is None:
        print("cena: sem acesso (cache/cena/acesso.json): a faixa do DWG fica no platô")
        return None
    return a, AcessoCfg.carregar(CFG_TOML)


def montar(msp, grade: Grade, lotes: list[dict], cfg: CenaCfg, placa_cfg: PlacaCfg,
           plato_aneis: list[list[Ponto]], janelas_: dict[str, Ext], e0: float, n0: float,
           pegadas: BaseGeometry | None = None, acesso: "tuple[Acesso, AcessoCfg] | None" = None) -> dict:
    pecas, plato = pecas_da_placa(msp, lotes, cfg, placa_cfg, plato_aneis, e0, n0)
    pecas_ac: dict[str, BaseGeometry] = {}
    if acesso is not None:
        a, acfg = acesso
        ce = unary_union([Polygon(r[0], r[1:]) for r in a.ce]) if a.ce else Polygon()
        pecas_ac = pecas_acesso(a, ce, acfg)
        area = unary_union(list(pecas_ac.values()))
        invadidos = [k for k, g in pecas.items() if k.startswith("Q") and g.intersection(area).area > 0.5]
        if invadidos:
            raise ValueError(f"acesso sobre lote: {', '.join(invadidos)}")
        pecas = {k: g.difference(area) for k, g in pecas.items()}
        pecas = {k: g for k, g in pecas.items() if not g.is_empty}
        plano = plato.difference(area)  # a cota sai do platô que ficou plano
        plato = plato.union(area)  # o terreno perde o corredor também
    else:
        plano = plato
    if pegadas is not None and not pegadas.is_empty:
        invadidos = [k for k, g in pecas.items() if k.startswith("Q") and g.intersection(pegadas).area > 0.5]
        if invadidos:
            raise ValueError(f"pegada de marco sobre lote: {', '.join(invadidos)}")
        pecas = {k: (g if k.startswith("Q") else g.difference(pegadas)) for k, g in pecas.items()}
        pecas = {k: g for k, g in pecas.items() if not g.is_empty}
    cota = grade.cota_malha(*plano.representative_point().coords[0])  # o platô é plano
    objetos = montar_placa(pecas, placa_cfg, cota, {l["id"]: f"lote_{l['tipo']}" for l in lotes})
    if pecas_ac:
        vizinhos = {k: (g, altura(k, placa_cfg)) for k, g in pecas.items()}
        objetos += montar_acesso(acesso[0], pecas_ac, vizinhos, cota, placa_cfg.fundo, acesso[1])
    for k, jan in janelas_.items():
        v, f = malha_perto(grade, plato, jan)
        if f:
            objetos.append({"nome": f"Terreno_{k}", "material": "terreno", "vertices": v, "faces": f})
    return {"objetos": objetos}


def main() -> int:
    from .terreno import DESTINO_LONGE, TerrenoCfg, aneis_do_plato  # terreno importa cena: import local

    sys.stdout.reconfigure(encoding="utf-8")
    georref = json.loads((RAIZ / "dados" / "georref.json").read_text(encoding="utf-8"))
    e0, n0 = georref["origem"]["E"], georref["origem"]["N"]
    lotes = json.loads((RAIZ / "dados" / "lotes.json").read_text(encoding="utf-8"))["lotes"]
    grade = Grade.de_json(json.loads(TERRENO_JSON.read_text(encoding="utf-8")))
    longe = Grade.de_json(json.loads(DESTINO_LONGE.read_text(encoding="utf-8")))
    msp = ezdxf.readfile(DXF).modelspace()
    plato = aneis_do_plato(msp, TerrenoCfg.carregar(CFG_TOML), lotes, e0, n0)
    cena = montar(msp, grade, lotes, CenaCfg.carregar(CFG_TOML), PlacaCfg.carregar(CFG_TOML), plato,
                  janelas(ext_da_grade(longe), longe.passo), e0, n0, pegadas=pegadas_dos_marcos(),
                  acesso=acesso_da_cena())
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(cena), encoding="utf-8")
    tris = {o["nome"]: len(o["faces"]) for o in cena["objetos"]}
    lotes_n = sum(1 for n in tris if n.startswith("Q"))
    print(f"{len(tris)} objetos ({lotes_n} lotes) · {sum(tris.values())} triângulos · "
          + ", ".join(f"{n} {t}" for n, t in tris.items() if not n.startswith("Q")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
