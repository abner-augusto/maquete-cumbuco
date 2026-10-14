import pytest

from scripts.loteamento.ids import id_lote, normalizar_lote, normalizar_quadra, tipo_por_quadra


@pytest.mark.parametrize("bruto", ["07", "7", 7, 7.0, "7.0", "Q-07", "QUADRA 07", "Qd. 7", " q7 "])
def test_quadra_numerica_vira_dois_digitos(bruto):
    assert normalizar_quadra(bruto) == "07"


@pytest.mark.parametrize("bruto", ["H", "h", "QUADRA H", "Q-M"])
def test_quadra_alfabetica_vira_letra(bruto):
    assert normalizar_quadra(bruto) in {"H", "M"}


@pytest.mark.parametrize("bruto", ["4", "04", 4.0, "LT 4", "Lote 04", "L-4"])
def test_lote_vira_dois_digitos(bruto):
    assert normalizar_lote(bruto) == "04"


def test_id_lote():
    assert id_lote("7", "4") == "Q07L04"
    assert id_lote("H", 1) == "QHL01"


@pytest.mark.parametrize("bruto", ["", "TOTAL", "7A", None])
def test_quadra_invalida_falha(bruto):
    with pytest.raises(ValueError):
        normalizar_quadra(bruto)


def test_tipo_por_quadra():
    assert tipo_por_quadra("07") == "residencial"
    assert tipo_por_quadra("M") == "uso_misto"
