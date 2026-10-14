from scripts.marca.familias import ATIVA, FAMILIAS, textos


def test_familia_ativa_e_cidade_das_americas_sem_alternativa():
    # Decisão da empresa (14/10/2026): o nome Alternativa espera o registro.
    f = FAMILIAS[ATIVA]
    assert ATIVA == "americas" and not f.confidencial
    assert not any("ALTERNATIVA" in t.upper() for t in [*textos(f), f.titulo])
    assert f.mae is None


def test_familia_alternativa_guardada_para_validacao():
    f = FAMILIAS["alternativa"]
    assert f.confidencial and f.mae == "DESENVOLVIMENTO URBANO"
