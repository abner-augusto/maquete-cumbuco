import json
import struct
from pathlib import Path

import pytest

from scripts.loteamento.blender import BLENDER_PADRAO, SCRIPT, conferir_glb, nos_do_glb, rodar_blender


def _glb(caminho: Path, nomes: list[str]) -> None:
    js = json.dumps({"asset": {"version": "2.0"}, "nodes": [{"name": n} for n in nomes]}).encode()
    js += b" " * (-len(js) % 4)
    caminho.write_bytes(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js)) + struct.pack("<II", len(js), 0x4E4F534A) + js)


def test_nos_do_glb(tmp_path):
    _glb(tmp_path / "a.glb", ["Terreno", "Q01L01"])
    assert nos_do_glb(tmp_path / "a.glb") == ["Terreno", "Q01L01"]


def test_conferir_glb_acusa_falta_e_sobra():
    erros = conferir_glb(["Terreno", "Q01L01", "Q09L09"], ["Q01L01", "Q01L02"])
    assert erros == ["lote sem objeto no GLB: Q01L02", "objeto de lote sem linha no lotes.json: Q09L09"]


@pytest.mark.skipif(not BLENDER_PADRAO.exists(), reason="Blender 5.2 ausente")
def test_blender_constroi_e_exporta_com_os_nomes(tmp_path):
    cena = {"objetos": [
        {"nome": "Terreno", "material": "terreno", "vertices": [[0, 0, 0], [10, 0, 0], [0, 10, 1]], "faces": [[0, 1, 2]]},
        {"nome": "Q01L01", "material": "lote_residencial", "vertices": [[0, 0, 1], [5, 0, 1], [0, 5, 1]], "faces": [[0, 1, 2]]},
    ]}
    (tmp_path / "cena.json").write_text(json.dumps(cena), encoding="utf-8")
    resumo = rodar_blender(BLENDER_PADRAO, SCRIPT, str(tmp_path / "cena.json"), str(tmp_path / "l.blend"), str(tmp_path / "l.glb"))
    assert set(nos_do_glb(tmp_path / "l.glb")) == {"Terreno", "Q01L01"}
    assert (tmp_path / "l.blend").exists() and resumo["objetos"] == 2


@pytest.mark.skipif(not BLENDER_PADRAO.exists(), reason="Blender 5.2 ausente")
def test_regerar_nao_deixa_blend1_na_pasta_do_terreno(tmp_path):
    # revisão final: o .blend1 de backup ia junto para o Drive do cliente
    cena = {"objetos": [{"nome": "Q01L01", "material": "lote_residencial",
                         "vertices": [[0, 0, 1], [5, 0, 1], [0, 5, 1]], "faces": [[0, 1, 2]]}]}
    (tmp_path / "cena.json").write_text(json.dumps(cena), encoding="utf-8")
    for _ in range(2):
        rodar_blender(BLENDER_PADRAO, SCRIPT, str(tmp_path / "cena.json"), str(tmp_path / "l.blend"), str(tmp_path / "l.glb"))
    assert not (tmp_path / "l.blend1").exists()
