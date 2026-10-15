import json
import struct
from pathlib import Path

import pytest

from scripts.loteamento.blender import BLENDER_PADRAO, SCRIPT, com_mapa, conferir_entorno, conferir_glb, juntar_cenas, nos_do_glb, rodar_blender


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



def test_conferir_entorno_acusa_peso():
    assert conferir_entorno(["Entorno", "Mar", "ViasPrincipais", "Predios"], 8.4) == ["entorno.glb com 8.4 MB (alvo 8.0 MB)"]


@pytest.mark.skipif(not BLENDER_PADRAO.exists(), reason="Blender 5.2 ausente")
def test_contexto_entra_so_na_previa(tmp_path):
    lote = {"objetos": [{"nome": "Q01L01", "material": "lote_residencial",
                         "vertices": [[0, 0, 1], [5, 0, 1], [0, 5, 1]], "faces": [[0, 1, 2]]}]}
    ctx = {"objetos": [{"nome": "Mar", "material": "mar",
                        "vertices": [[-50, -50, 0], [50, -50, 0], [0, 50, 0]], "faces": [[0, 1, 2]]}]}
    (tmp_path / "l.json").write_text(json.dumps(lote), encoding="utf-8")
    (tmp_path / "c.json").write_text(json.dumps(ctx), encoding="utf-8")
    rodar_blender(BLENDER_PADRAO, SCRIPT, str(tmp_path / "l.json"), str(tmp_path / "l.blend"),
                  str(tmp_path / "l.glb"), str(tmp_path / "p.png"), str(tmp_path / "c.json"))
    assert nos_do_glb(tmp_path / "l.glb") == ["Q01L01"]
    assert (tmp_path / "p-entorno.png").exists() and (tmp_path / "p.png").exists()


def test_com_mapa_poe_textura_so_nos_nomes_pedidos():
    dados = {"objetos": [{"nome": "Entorno", "material": "entorno"}, {"nome": "Mar", "material": "mar"}]}
    mapa = {"arquivo": "C:/m.jpg", "ext": [0, 0, 10, 10], "px": [8, 8]}
    novo = com_mapa(dados, mapa, {"Entorno"})
    assert novo["objetos"][0]["textura"] == {"arquivo": "C:/m.jpg", "ext": [0, 0, 10, 10]}
    assert novo["objetos"][0]["material"] == "chao" and "textura" not in novo["objetos"][1]
    assert "textura" not in dados["objetos"][0]  # não altera a entrada


def test_juntar_cenas():
    assert [o["nome"] for o in juntar_cenas({"objetos": [{"nome": "A"}]}, {"objetos": [{"nome": "B"}]})["objetos"]] == ["A", "B"]


def test_conferir_entorno_exige_os_objetos_novos():
    assert conferir_entorno(["Entorno", "Mar", "ViasPrincipais", "Predios"], 5.0) == []
    assert conferir_entorno(["Entorno", "Mar"], 5.0) == ["objeto do entorno faltando no GLB: ViasPrincipais",
                                                         "objeto do entorno faltando no GLB: Predios"]


@pytest.mark.skipif(not BLENDER_PADRAO.exists(), reason="Blender 5.2 ausente")
def test_textura_vira_uv_e_imagem_no_glb(tmp_path):
    from PIL import Image

    Image.new("RGB", (8, 8), (200, 100, 50)).save(tmp_path / "m.jpg")
    cena = {"objetos": [{"nome": "Entorno", "material": "chao", "vertices": [[0, 0, 0], [10, 0, 0], [0, 10, 0]],
                         "faces": [[0, 1, 2]], "textura": {"arquivo": str(tmp_path / "m.jpg"), "ext": [0, 0, 10, 10]}},
                        {"nome": "Predios", "material": "predio", "vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 1]],
                         "faces": [[0, 1, 2]], "suave": False}]}
    (tmp_path / "c.json").write_text(json.dumps(cena), encoding="utf-8")
    rodar_blender(BLENDER_PADRAO, SCRIPT, str(tmp_path / "c.json"), str(tmp_path / "c.blend"), str(tmp_path / "c.glb"))
    dados = (tmp_path / "c.glb").read_bytes()
    tamanho = struct.unpack_from("<I", dados, 12)[0]
    gltf = json.loads(dados[20:20 + tamanho])
    assert gltf.get("images") and gltf.get("textures")
    assert any("TEXCOORD_0" in p["attributes"] for m in gltf["meshes"] for p in m["primitives"])
