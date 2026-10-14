import math

import ezdxf
import pytest

from scripts.loteamento.extrair import MapaLayers
from scripts.loteamento.fontes import LinhaPreco

E0, N0 = 500_000.0, 9_600_000.0
BULGE_H1 = 0.2
_THETA = 4 * math.atan(BULGE_H1)
_R = 30 / (2 * math.sin(_THETA / 2))
AREA_H1 = 600 + _R * _R / 2 * (_THETA - math.sin(_THETA))


def _ret(x, y, w, h):
    return [(E0 + x, N0 + y), (E0 + x + w, N0 + y), (E0 + x + w, N0 + y + h), (E0 + x, N0 + y + h)]


@pytest.fixture
def mapa_sintetico():
    return MapaLayers(lotes="LOTES", rotulo_lote="NUM_LOTE", quadras="QUADRAS", rotulo_quadra="NUM_QUADRA", meio_fio="MEIO_FIO")


@pytest.fixture
def doc_sintetico():
    """Quadra 01 com dois lotes 10×20 e quadra H com um lote 30×20 de frente em arco; meio-fio ao sul."""
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_lwpolyline(_ret(-1, -1, 22, 22), close=True, dxfattribs={"layer": "QUADRAS"})
    msp.add_text("QUADRA 01", dxfattribs={"layer": "NUM_QUADRA", "insert": (E0 + 5, N0 + 15)})
    msp.add_lwpolyline(_ret(0, 0, 10, 20), close=True, dxfattribs={"layer": "LOTES"})
    msp.add_text("1", dxfattribs={"layer": "NUM_LOTE", "insert": (E0 + 5, N0 + 10)})
    msp.add_lwpolyline(_ret(10, 0, 10, 20), close=True, dxfattribs={"layer": "LOTES"})
    bloco = doc.blocks.new("NUMERO")
    bloco.add_attdef("N", (0, 0), dxfattribs={"layer": "NUM_LOTE"})
    ref = msp.add_blockref("NUMERO", (E0 + 15, N0 + 10), dxfattribs={"layer": "NUM_LOTE"})
    ref.add_auto_attribs({"N": "02"})
    for a in ref.attribs:  # garante a layer do ATTRIB, que é o que a extração lê
        a.dxf.layer = "NUM_LOTE"
    msp.add_lwpolyline(_ret(29, -6, 32, 27), close=True, dxfattribs={"layer": "QUADRAS"})
    msp.add_text("H", dxfattribs={"layer": "NUM_QUADRA", "insert": (E0 + 45, N0 + 18)})
    msp.add_lwpolyline(
        [(E0 + 30, N0, BULGE_H1), (E0 + 60, N0, 0), (E0 + 60, N0 + 20, 0), (E0 + 30, N0 + 20, 0)],
        format="xyb", close=True, dxfattribs={"layer": "LOTES"},
    )
    msp.add_text("LT 1", dxfattribs={"layer": "NUM_LOTE", "insert": (E0 + 45, N0 + 10)})
    msp.add_lwpolyline([(E0 - 5, N0 - 8), (E0 + 65, N0 - 8)], dxfattribs={"layer": "MEIO_FIO"})
    return doc


@pytest.fixture
def tabela_sintetica():
    return {
        "Q01L01": LinhaPreco(200.0, "A", 1380.0, 276000.0),
        "Q01L02": LinhaPreco(200.0, "A", 1380.0, 276000.0),
        "QHL01": LinhaPreco(round(AREA_H1, 2), "D", 990.0, round(AREA_H1 * 990, 2)),
    }


@pytest.fixture
def iptu_sintetico():
    return {"Q01L01": "138321-3", "Q01L02": "138339-6"}
