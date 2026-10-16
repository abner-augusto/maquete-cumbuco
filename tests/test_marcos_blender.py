import json

import pytest

from scripts.loteamento.blender import BLENDER_PADRAO, SCRIPT, rodar_blender
from scripts.marcos.blender import rodar_extracao


def _glb(tmp_path, nome, objetos):
    (tmp_path / f"{nome}.json").write_text(json.dumps({"objetos": objetos}), encoding="utf-8")
    rodar_blender(BLENDER_PADRAO, SCRIPT, str(tmp_path / f"{nome}.json"), str(tmp_path / f"{nome}.blend"),
                  str(tmp_path / f"{nome}.glb"))
    return tmp_path / f"{nome}.glb"


PISO = {"nome": "PORTARIA_PISO", "material": "terreno", "vertices": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0]],
        "faces": [[0, 1, 2], [0, 2, 3]]}
LAJE = {"nome": "PORTARIA_LAJE", "material": "terreno", "vertices": [[2, 2, 3], [4, 2, 3], [4, 4, 3]], "faces": [[0, 1, 2]]}


@pytest.mark.skipif(not BLENDER_PADRAO.exists(), reason="Blender 5.2 ausente")
def test_extrai_caixas_e_chao(tmp_path):
    glb = _glb(tmp_path, "p", [PISO, LAJE])
    dados = rodar_extracao(BLENDER_PADRAO, [glb], tmp_path / "fonte.json", ["PORTARIA_"])
    d = dados["p.glb"]
    assert d["objetos"]["PORTARIA_LAJE"] == pytest.approx([2, 2, 3, 4, 4, 3], abs=1e-4)
    assert len(d["chao"]["PORTARIA_PISO"]) == 2 and "PORTARIA_LAJE" not in d["chao"]  # laje a 3 m não é chão


@pytest.mark.skipif(not BLENDER_PADRAO.exists(), reason="Blender 5.2 ausente")
def test_prefixo_ausente_falha_nomeando(tmp_path):
    glb = _glb(tmp_path, "p", [PISO])
    with pytest.raises(RuntimeError, match="CLUBE_"):
        rodar_extracao(BLENDER_PADRAO, [glb], tmp_path / "fonte.json", ["PORTARIA_", "CLUBE_"])
