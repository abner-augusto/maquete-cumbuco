"""Lotes do DXF de venda: polígono, quadra, número, lados e frente."""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .geometria import Ponto, centroide, contem, indice_frente, poligono_fechado, pontos_de, segmentos
from .ids import id_lote, normalizar_lote, normalizar_quadra

_RE_LOTE = re.compile(r"^(?:LOTE|LT\.?|L)?\s*-?\s*(\d{1,3})$", re.IGNORECASE)
_RE_QUADRA = re.compile(r"^(?:QUADRA|QD\.?|Q)?\s*-?\s*(\d{1,3}|[A-Z])$", re.IGNORECASE)
_RE_AREA = re.compile(r"^(\d+(?:[.,]\d+)?)$")
_RE_ID = re.compile(r"^Q([A-Z]|\d{2})L(\d{2})$")
_TIPOS_VIA = ("LWPOLYLINE", "POLYLINE", "LINE", "ARC")


@dataclass(frozen=True)
class MapaLayers:
    lotes: str
    rotulo_lote: str
    quadras: str
    rotulo_quadra: str
    meio_fio: str
    area_lote: str | None = None
    # (id, layer do polígono, texto dentro dele) dos lotes sem bloco de número
    uso_misto: tuple[tuple[str, str, str], ...] = ()

    @classmethod
    def carregar(cls, caminho: Path) -> "MapaLayers":
        dados = tomllib.loads(caminho.read_text(encoding="utf-8"))
        uso_misto = tuple((i, v["layer"], v["texto"]) for i, v in dados.pop("uso_misto", {}).items())
        return cls(**dados, uso_misto=uso_misto)


@dataclass(frozen=True)
class LoteBruto:
    id: str
    quadra: str
    lote: str
    handle: str
    pontos: list[Ponto]
    lados_m: list[float]
    frente_m: float | None
    area_cad: float | None = None  # área escrita no desenho (bloco de área), quando há


class ExtracaoErro(Exception):
    def __init__(self, erros: list[str]):
        super().__init__(f"{len(erros)} erro(s) na extração")
        self.erros = erros


def textos_da_layer(msp, layer: str) -> list[tuple[Ponto, str]]:
    """TEXT, MTEXT e ATTRIB da layer. Bloco na layer conta inteiro, no ponto de inserção do bloco."""
    saida = []
    for e in msp:
        t = e.dxftype()
        if t == "TEXT" and e.dxf.layer == layer:
            saida.append(((e.dxf.insert.x, e.dxf.insert.y), e.dxf.text.strip()))
        elif t == "MTEXT" and e.dxf.layer == layer:
            saida.append(((e.dxf.insert.x, e.dxf.insert.y), e.plain_text().strip()))
        elif t == "INSERT":
            no_bloco = e.dxf.layer == layer
            for a in e.attribs:
                if no_bloco:
                    saida.append(((e.dxf.insert.x, e.dxf.insert.y), a.dxf.text.strip()))
                elif a.dxf.layer == layer:
                    saida.append(((a.dxf.insert.x, a.dxf.insert.y), a.dxf.text.strip()))
    return saida


def _rotulos(msp, layer: str, regex: re.Pattern) -> list[tuple[Ponto, str]]:
    return [(p, m.group(1)) for p, t in textos_da_layer(msp, layer) if (m := regex.match(t))]


def _textos_soltos(msp) -> list[tuple[Ponto, str]]:
    saida = []
    for e in msp.query("TEXT MTEXT"):
        texto = e.dxf.text if e.dxftype() == "TEXT" else e.plain_text()
        saida.append(((e.dxf.insert.x, e.dxf.insert.y), texto.strip().upper()))
    return saida


def _frente(e, vias) -> float | None:
    segs = segmentos(e)
    return round(segs[indice_frente(segs, vias)][2], 2) if vias else None


def _lados(e) -> list[float]:
    return [round(s[2], 2) for s in segmentos(e)]


def _uso_misto(msp, mapa: MapaLayers, vias, erros: list[str]) -> dict[str, LoteBruto]:
    textos = _textos_soltos(msp) if mapa.uso_misto else []
    lotes: dict[str, LoteBruto] = {}
    for i, layer, texto in mapa.uso_misto:
        alvo = texto.strip().upper()
        pontos_texto = [p for p, t in textos if t.startswith(alvo)]
        achados = []
        for e in msp.query(f'LWPOLYLINE[layer=="{layer}"]'):
            if poligono_fechado(e):
                pts = pontos_de(e)
                if any(contem(pts, p) for p in pontos_texto):
                    achados.append((e, pts))
        if len(achados) != 1:
            handles = [e.dxf.handle for e, _ in achados]
            erros.append(f"{i}: {len(achados)} polígonos na layer {layer} com o texto {texto!r} {handles}")
            continue
        m = _RE_ID.match(i)
        if not m:
            erros.append(f"{i}: id de uso misto fora do formato Q<quadra>L<lote>")
            continue
        e, pts = achados[0]
        lotes[i] = LoteBruto(i, m.group(1), m.group(2), e.dxf.handle, pts, _lados(e), _frente(e, vias))
    return lotes


def extrair_lotes(doc, mapa: MapaLayers) -> dict[str, LoteBruto]:
    msp = doc.modelspace()
    erros: list[str] = []

    rotulos_quadra = _rotulos(msp, mapa.rotulo_quadra, _RE_QUADRA)
    quadras: list[tuple[list[Ponto], str]] = []
    for e in msp.query(f'LWPOLYLINE[layer=="{mapa.quadras}"]'):
        if not poligono_fechado(e):
            continue
        pts = pontos_de(e)
        dentro = [r for p, r in rotulos_quadra if contem(pts, p)]
        # Quadra sem rótulo (institucional, administrativo, uso misto) não recebe lote;
        # um lote dentro dela acusa "0 quadras" abaixo.
        if len(dentro) > 1:
            erros.append(f"quadra handle {e.dxf.handle}: {len(dentro)} rótulos {dentro}")
        if len(dentro) == 1:
            quadras.append((pts, dentro[0]))

    rotulos_lote = _rotulos(msp, mapa.rotulo_lote, _RE_LOTE)
    areas = _rotulos(msp, mapa.area_lote, _RE_AREA) if mapa.area_lote else []
    vias = []
    for e in msp:
        if e.dxf.layer == mapa.meio_fio and e.dxftype() in _TIPOS_VIA:
            pts = pontos_de(e)
            # pontos_de tira o ponto de fechamento; a aresta último → primeiro também é meio-fio
            if getattr(e, "closed", False) or poligono_fechado(e):
                pts = pts + pts[:1]
            vias.append(pts)

    lotes: dict[str, LoteBruto] = {}
    poligonos_lote: list[list[Ponto]] = []
    for e in msp.query(f'LWPOLYLINE[layer=="{mapa.lotes}"]'):
        h = e.dxf.handle
        if not poligono_fechado(e):
            erros.append(f"lote handle {h}: polilinha aberta na layer {mapa.lotes}")
            continue
        pts = pontos_de(e)
        poligonos_lote.append(pts)
        dentro = [r for p, r in rotulos_lote if contem(pts, p)]
        if len(dentro) != 1:
            erros.append(f"lote handle {h}: {len(dentro)} rótulos {dentro}")
            continue
        c = centroide(pts)
        qs = [r for qpts, r in quadras if contem(qpts, c)]
        if len(qs) != 1:
            erros.append(f"lote handle {h} (nº {dentro[0]}): dentro de {len(qs)} quadras {qs}")
            continue
        q, l = normalizar_quadra(qs[0]), normalizar_lote(dentro[0])
        i = id_lote(q, l)
        if i in lotes:
            erros.append(f"{i} repetido (handles {lotes[i].handle} e {h})")
            continue
        area_cad = [float(a.replace(",", ".")) for p, a in areas if contem(pts, p)]
        lotes[i] = LoteBruto(
            i, q, l, h, pts, _lados(e), _frente(e, vias),
            area_cad[0] if len(area_cad) == 1 else None,
        )

    for p, r in rotulos_lote:
        if not any(contem(pts, p) for pts in poligonos_lote):
            erros.append(f"rótulo de lote {r!r} em ({p[0]:.2f}, {p[1]:.2f}) fora de qualquer lote")

    for i, lote in _uso_misto(msp, mapa, vias, erros).items():
        if i in lotes:
            erros.append(f"{i} repetido (handles {lotes[i].handle} e {lote.handle})")
            continue
        lotes[i] = lote

    if erros:
        raise ExtracaoErro(erros)
    return lotes
