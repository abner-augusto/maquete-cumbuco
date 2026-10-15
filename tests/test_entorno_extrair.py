import pytest

from scripts.entorno.extrair import EntornoCfg, montar_base
from scripts.entorno.osm import Projecao

P = Projecao(534600.0, 9595100.0)
CFG = EntornoCfg(raio_vias=500.0, raio_faixas=300.0, raio_predios=300.0, raio_vegetacao=400.0,
                 raio_malha_regional=5000.0, mapa_px=256)


def _geo(pts):
    return [{"lon": lon, "lat": lat} for lon, lat in (P.lonlat(x, y) for x, y in pts)]


def _quad(x, y, l):
    return [(x, y), (x + l, y), (x + l, y + l), (x, y + l), (x, y)]


VIAS = {"elements": [
    {"type": "way", "id": 1, "tags": {"highway": "primary", "name": "CE-090"}, "geometry": _geo([(-900, 0), (900, 0)])},
    {"type": "way", "id": 2, "tags": {"highway": "steps"}, "geometry": _geo([(0, 0), (0, 50)])}]}
AREAS = {"elements": [{"type": "way", "id": 3, "tags": {"natural": "scrub"}, "geometry": _geo(_quad(10, 10, 50))}]}
PREDIOS = {"release": "x", "feicoes": [
    {"id": "a", "geometria": {"type": "Polygon", "coordinates": [[list(P.lonlat(x, y)) for x, y in _quad(20, 20, 10)]]},
     "fonte": "OpenStreetMap", "altura": None, "niveis": 2, "classe": None, "nome": None},
    {"id": "longe", "geometria": {"type": "Polygon", "coordinates": [[list(P.lonlat(x, y)) for x, y in _quad(900, 900, 10)]]},
     "fonte": "x", "altura": None, "niveis": None, "classe": None, "nome": None}]}


def test_montar_base_recorta_vias_no_raio_e_filtra_classes():
    b = montar_base(P, (0.0, 0.0), CFG, VIAS, AREAS, PREDIOS)
    (v,) = b["vias"]
    assert v["classe"] == "primary" and v["nome"] == "CE-090"
    assert min(x for x, _ in v["pontos"]) == pytest.approx(-500, abs=0.5)  # cortada no raio
    assert b["areas"][0]["tipo"] == "verde" and b["areas"][0]["tags"] == {"natural": "scrub"}
    assert [p["id"] for p in b["predios"]] == ["a"] and b["predios"][0]["area_m2"] == pytest.approx(100, rel=1e-3)


def test_montar_base_recusa_download_vazio():
    with pytest.raises(SystemExit, match="Nenhuma via"):
        montar_base(P, (0.0, 0.0), CFG, {"elements": []}, AREAS, PREDIOS)
    with pytest.raises(SystemExit, match="Nenhum prédio"):
        montar_base(P, (0.0, 0.0), CFG, VIAS, AREAS, {"release": "x", "feicoes": []})


def test_montar_base_recusa_areas_vazias():
    # revisão final: áreas vazias davam mapa sem lagoas nem praia e zero árvores, sem erro
    with pytest.raises(SystemExit, match="Nenhuma área"):
        montar_base(P, (0.0, 0.0), CFG, VIAS, {"elements": []}, PREDIOS)
