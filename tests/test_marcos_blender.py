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
    dados = rodar_extracao(BLENDER_PADRAO, {glb: ["PORTARIA_"]}, tmp_path / "fonte.json")
    d = dados["p.glb"]
    assert d["objetos"]["PORTARIA_LAJE"] == pytest.approx([2, 2, 3, 4, 4, 3], abs=1e-4)
    assert len(d["chao"]["PORTARIA_PISO"]) == 2 and "PORTARIA_LAJE" not in d["chao"]  # laje a 3 m não é chão
    assert len(d["topo"]["PORTARIA_LAJE"]) == 1 and len(d["topo"]["PORTARIA_PISO"]) == 2  # topo: qualquer altura
    assert "PORTARIA_PISO" in d["baixo"] and "PORTARIA_LAJE" not in d["baixo"]  # baixo: até 0,6 m, o que fura a placa


@pytest.mark.skipif(not BLENDER_PADRAO.exists(), reason="Blender 5.2 ausente")
def test_prefixo_ausente_falha_nomeando(tmp_path):
    glb = _glb(tmp_path, "p", [PISO])
    with pytest.raises(RuntimeError, match="CLUBE_.*p.glb"):
        rodar_extracao(BLENDER_PADRAO, {glb: ["PORTARIA_", "CLUBE_"]}, tmp_path / "fonte.json")


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
    # fica só a face com todos os vértices dentro: a laje; os dois triângulos do piso cruzam a borda
    assert resumo["Portaria"]["triangulos"] == 1
    assert resumo["Portaria"]["x"] == pytest.approx([102.0, 104.0], abs=0.01)  # transladado
    assert resumo["Portaria"]["z"] == pytest.approx([24.0, 24.0], abs=0.01)  # a laje, 3 m acima da cota 21


@pytest.mark.skipif(not BLENDER_PADRAO.exists(), reason="Blender 5.2 ausente")
def test_prefixo_no_arquivo_errado_falha(tmp_path):
    a = _glb(tmp_path, "a", [PISO])
    b = _glb(tmp_path, "b", [dict(PISO, nome="CLUBE_PISO")])
    with pytest.raises(RuntimeError, match="CLUBE_.*a.glb"):
        rodar_extracao(BLENDER_PADRAO, {a: ["CLUBE_"], b: []}, tmp_path / "fonte.json")


@pytest.mark.skipif(not BLENDER_PADRAO.exists(), reason="Blender 5.2 ausente")
def test_geracao_sem_o_prefixo_falha_nomeando(tmp_path):
    glb = _glb(tmp_path, "p", [PISO])
    marcos = {"cota": 0.0, "marcos": {"Clube": {
        "fonte": str(glb), "prefixo": "CLUBE_", "giro": None, "transf": {"s": 1.0, "theta": 0.0, "tx": 0.0, "ty": 0.0},
        "z": 0.0, "pegada": [[0, 0], [10, 0], [10, 10], [0, 10]]}}}
    (tmp_path / "m.json").write_text(json.dumps(marcos), encoding="utf-8")
    with pytest.raises(RuntimeError, match="CLUBE_.*p.glb"):
        rodar_geracao(BLENDER_PADRAO, tmp_path / "m.json", tmp_path / "m.glb")
