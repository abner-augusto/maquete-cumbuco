import json
import struct
from pathlib import Path

import pytest

from scripts.loteamento.blender import BLENDER_PADRAO, SCRIPT, com_tiles, conferir_entorno, copiar_mapas_osm, conferir_glb, juntar_cenas, nos_do_glb, rodar_blender


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


def test_juntar_cenas():
    assert [o["nome"] for o in juntar_cenas({"objetos": [{"nome": "A"}]}, {"objetos": [{"nome": "B"}]})["objetos"]] == ["A", "B"]


@pytest.mark.skipif(not BLENDER_PADRAO.exists(), reason="Blender 5.2 ausente")
def test_textura_vira_uv_e_imagem_no_glb(tmp_path):
    from PIL import Image

    Image.new("RGB", (8, 8), (200, 100, 50)).save(tmp_path / "m.jpg")
    cena = {"objetos": [{"nome": "Entorno_00", "material": "chao", "vertices": [[0, 0, 0], [10, 0, 0], [0, 10, 0]],
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


ENTORNO_OK = ["Entorno_00", "Entorno_01", "Entorno_10", "Entorno_11", "Mar", "ViasPrincipais", "Predios"]


def test_com_tiles_poe_a_imagem_do_tile_pelo_sufixo():
    dados = {"objetos": [{"nome": "Terreno_10", "material": "terreno"}, {"nome": "Q01L01", "material": "x"},
                         {"nome": "Mar", "material": "mar"}]}
    tiles = {"10": {"arquivo": "C:/m10.jpg", "ext": [0, 0, 10, 10], "janela": [0, 0, 9, 9], "px": [8, 8]}}
    novo = com_tiles(dados, tiles, ("Terreno",))
    assert novo["objetos"][0]["textura"] == {"arquivo": "C:/m10.jpg", "ext": [0, 0, 10, 10]}
    assert novo["objetos"][0]["material"] == "chao"
    assert "textura" not in novo["objetos"][1] and "textura" not in novo["objetos"][2]
    assert "textura" not in dados["objetos"][0]


def test_copiar_mapas_osm_leva_um_jpeg_por_tile_com_o_nome_do_front(tmp_path):
    origem = tmp_path / "mapa_osm_01.jpg"
    origem.write_bytes(b"jpeg")
    destino = tmp_path / "maquete"
    destino.mkdir()
    assert copiar_mapas_osm({"01": {"arquivo": str(origem)}}, destino) == ["01"]
    assert (destino / "mapa-osm_01.jpg").read_bytes() == b"jpeg"
    assert copiar_mapas_osm({}, destino) == []  # cache sem o masterplan: nada a copiar


def test_conferir_entorno_exige_os_quatro_pedacos_e_o_peso():
    assert conferir_entorno(ENTORNO_OK, 5.0) == []
    assert conferir_entorno(ENTORNO_OK, 11.4) == ["entorno.glb com 11.4 MB (alvo 11.0 MB)"]
    assert conferir_entorno(["Entorno_00", "Mar", "ViasPrincipais", "Predios"], 5.0) == [
        f"objeto do entorno faltando no GLB: Entorno_{k}" for k in ("01", "10", "11")]


@pytest.mark.skipif(not BLENDER_PADRAO.exists(), reason="Blender 5.2 ausente")
def test_lote_sai_com_pivo_no_centro(tmp_path):
    cena = {"objetos": [{"nome": "Q01L01", "material": "lote_residencial", "suave": False, "origem": [5.0, 10.0, 21.4],
                         "vertices": [[0, 0, 21.4], [10, 0, 21.4], [10, 20, 21.4], [0, 20, 21.4]],
                         "faces": [[0, 1, 2], [0, 2, 3]]}]}
    (tmp_path / "c.json").write_text(json.dumps(cena), encoding="utf-8")
    rodar_blender(BLENDER_PADRAO, SCRIPT, str(tmp_path / "c.json"), str(tmp_path / "c.blend"), str(tmp_path / "c.glb"))
    dados = (tmp_path / "c.glb").read_bytes()
    gltf = json.loads(dados[20:20 + struct.unpack_from("<I", dados, 12)[0]])
    no = next(n for n in gltf["nodes"] if n["name"] == "Q01L01")
    assert no["translation"] == pytest.approx([5.0, 21.4, -10.0], abs=1e-4)


@pytest.mark.skipif(not BLENDER_PADRAO.exists(), reason="Blender 5.2 ausente")
def test_tile_sai_preso_na_borda(tmp_path):
    # revisão final: com REPEAT, os níveis pequenos do mipmap misturavam a borda oposta do tile (costura de longe)
    from PIL import Image

    Image.new("RGB", (8, 8), (200, 100, 50)).save(tmp_path / "m.jpg")
    cena = {"objetos": [{"nome": "Entorno_00", "material": "chao", "vertices": [[0, 0, 0], [10, 0, 0], [0, 10, 0]],
                         "faces": [[0, 1, 2]], "textura": {"arquivo": str(tmp_path / "m.jpg"), "ext": [0, 0, 10, 10]}}]}
    (tmp_path / "c.json").write_text(json.dumps(cena), encoding="utf-8")
    rodar_blender(BLENDER_PADRAO, SCRIPT, str(tmp_path / "c.json"), str(tmp_path / "c.blend"), str(tmp_path / "c.glb"))
    dados = (tmp_path / "c.glb").read_bytes()
    gltf = json.loads(dados[20:20 + struct.unpack_from("<I", dados, 12)[0]])
    assert all(s.get("wrapS") == 33071 and s.get("wrapT") == 33071 for s in gltf["samplers"])  # CLAMP_TO_EDGE
