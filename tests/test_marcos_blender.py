import json

import pytest

from scripts.loteamento.blender import BLENDER_PADRAO, SCRIPT, rodar_blender
from scripts.loteamento.blender import nos_do_glb
from scripts.marcos.blender import conferir_marcos, rodar_extracao, rodar_geracao


def _glb(tmp_path, nome, objetos):
    (tmp_path / f"{nome}.json").write_text(json.dumps({"objetos": objetos}), encoding="utf-8")
    rodar_blender(BLENDER_PADRAO, SCRIPT, str(tmp_path / f"{nome}.json"), str(tmp_path / f"{nome}.blend"),
                  str(tmp_path / f"{nome}.glb"))
    return tmp_path / f"{nome}.glb"


def _json_do_glb(caminho):
    import struct

    b = caminho.read_bytes()
    n = struct.unpack_from("<I", b, 12)[0]
    return json.loads(b[20:20 + n])


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
    assert len(d["topo"]["PORTARIA_LAJE"]) == 1 and len(d["topo"]["PORTARIA_PISO"]) == 2  # topo: qualquer altura


@pytest.mark.skipif(not BLENDER_PADRAO.exists(), reason="Blender 5.2 ausente")
def test_prefixo_ausente_falha_nomeando(tmp_path):
    glb = _glb(tmp_path, "p", [PISO])
    with pytest.raises(RuntimeError, match="CLUBE_"):
        rodar_extracao(BLENDER_PADRAO, [glb], tmp_path / "fonte.json", ["PORTARIA_", "CLUBE_"])


def test_conferir_marcos():
    assert conferir_marcos(["Clube", "Portaria", "Rotatoria"], 4.0) == []
    assert conferir_marcos(["Clube"], 7.0) == ["objeto faltando no marcos.glb: Portaria",
                                               "objeto faltando no marcos.glb: Rotatoria",
                                               "marcos.glb com 7.0 MB (alvo 6.0 MB)"]


@pytest.mark.skipif(not BLENDER_PADRAO.exists(), reason="Blender 5.2 ausente")
def test_gera_marco_recortado_e_no_lugar(tmp_path):
    glb = _glb(tmp_path, "p", [PISO, LAJE])
    marcos = {"cota": 21.0, "marcos": {"Portaria": {
        "fonte": str(glb), "prefixo": "PORTARIA_", "giro": None,
        "transf": {"s": 1.0, "theta": 0.0, "tx": 100.0, "ty": 0.0}, "z": 21.0,
        "pegada": [[100, 0], [105, 0], [105, 10], [100, 10]]}}}  # só a metade oeste do piso
    (tmp_path / "m.json").write_text(json.dumps(marcos), encoding="utf-8")
    resumo = rodar_geracao(BLENDER_PADRAO, tmp_path / "m.json", tmp_path / "m.glb", tmp_path / "m.png")
    assert nos_do_glb(tmp_path / "m.glb") == ["Portaria"]
    assert "KHR_draco_mesh_compression" in _json_do_glb(tmp_path / "m.glb").get("extensionsUsed", [])
    # recorte pelo centro da face: fica a laje e o triângulo oeste do piso (centro x = 3,3), que vai até x = 10
    assert resumo["Portaria"]["triangulos"] == 2
    assert resumo["Portaria"]["x"] == pytest.approx([100.0, 110.0], abs=0.01)  # transladado
    assert resumo["Portaria"]["z"] == pytest.approx([21.0, 24.0], abs=0.01)
