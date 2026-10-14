from collections import Counter

import pytest

from scripts.loteamento.geometria import area
from scripts.loteamento.malha import aninhar, drapear, refinar, simplificar, triangular
from scripts.loteamento.relevo import Grade

QUADRADO = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]
FURO = [(40.0, 40.0), (60.0, 40.0), (60.0, 60.0), (40.0, 60.0)]


def _area_tris(verts, tris):
    return sum(area([verts[a], verts[b], verts[c]]) for a, b, c in tris)


def test_simplificar_tira_ponto_colinear_e_mantem_cantos():
    anel = [(0.0, 0.0), (50.0, 0.001), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]
    assert simplificar(anel, 0.05) == QUADRADO


def test_aninhar_reconhece_furo_e_ilha_dentro_do_furo():
    ilha = [(45.0, 45.0), (55.0, 45.0), (55.0, 55.0), (45.0, 55.0)]
    grupos = aninhar([FURO, QUADRADO, ilha])
    externos = sorted(area(e) for e, _ in grupos)
    assert externos == [100.0, 10000.0]
    grande = next(f for e, f in grupos if area(e) == 10000.0)
    assert grande == [FURO]


def test_triangular_respeita_o_furo():
    verts, tris = triangular(QUADRADO, [FURO])
    assert _area_tris(verts, tris) == pytest.approx(10000 - 400)


def test_refinar_limita_aresta_preserva_area_e_nao_deixa_frestas():
    verts, tris = refinar(*triangular(QUADRADO, []), 10.0)
    assert _area_tris(verts, tris) == pytest.approx(10000)
    arestas = Counter(tuple(sorted(e)) for a, b, c in tris for e in ((a, b), (b, c), (c, a)))
    for (i, j), n in arestas.items():
        (xa, ya), (xb, yb) = verts[i], verts[j]
        assert ((xa - xb) ** 2 + (ya - yb) ** 2) ** 0.5 <= 10.0 + 1e-9
        if n == 1:  # aresta de borda: tem de estar no contorno do quadrado
            assert xa == xb in (0.0, 100.0) or ya == yb in (0.0, 100.0)
        else:
            assert n == 2


def test_drapear_soma_offset_a_cota():
    g = Grade(0.0, 0.0, 10.0, 2, 2, [[10.0, 20.0], [10.0, 20.0]])
    assert drapear([(5.0, 5.0)], g, 0.1) == [[5.0, 5.0, 15.1]]


def test_aninhar_anel_que_atravessa_outro_nao_vira_furo():
    # revisão final: pedaços de via que cruzam a borda de outro viravam furo e sumiam
    meio_fora = [(80.0, 40.0), (140.0, 40.0), (140.0, 60.0), (80.0, 60.0)]
    grupos = aninhar([QUADRADO, meio_fora])
    assert sorted(area(e) for e, _ in grupos) == [1200.0, 10000.0]
    assert all(furos == [] for _, furos in grupos)


def test_aninhar_anel_colado_na_borda_nao_vira_furo():
    # via desenhada duas vezes: todos os vértices do anel menor sobre a borda do maior
    faixa = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]
    diagonal = [(0.0, 0.0), (10.0, 0.0), (100.0, 100.0), (90.0, 100.0)]
    grupos = aninhar([faixa, diagonal])
    assert all(furos == [] for _, furos in grupos) and len(grupos) == 2
