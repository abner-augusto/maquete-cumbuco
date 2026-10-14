import pandas as pd
import pytest

from scripts.loteamento.fontes import LinhaPreco, ler_iptu, linhas_tabela

CSV = "quadra;lote;tipo;inscricao;arquivo\n01;01;ESPELHO 2025;138321-3;a.pdf\n01;02;BOLETO 2025;138339-6;b.pdf\n"


def test_ler_iptu_utf8(tmp_path):
    p = tmp_path / "i.csv"
    p.write_text(CSV, encoding="utf-8-sig")
    assert ler_iptu(p) == {"Q01L01": "138321-3", "Q01L02": "138339-6"}


def test_ler_iptu_cp1252(tmp_path):
    p = tmp_path / "i.csv"
    p.write_bytes(CSV.replace("ESPELHO", "ESPELHÃO").encode("cp1252"))
    assert ler_iptu(p)["Q01L01"] == "138321-3"


def test_ler_iptu_inscricoes_conflitantes_falham(tmp_path):
    p = tmp_path / "i.csv"
    p.write_text(CSV + "1;1;ESPELHO 2025;999999-9;c.pdf\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Q01L01"):
        ler_iptu(p)


def test_ler_iptu_ignora_linha_sem_quadra_e_lote(tmp_path):
    # No índice real, os boletos de uso misto e multifamiliar não têm quadra/lote.
    p = tmp_path / "i.csv"
    p.write_text(CSV + ";;BOLETO 2025;139193-3;USO MISTO.pdf\n", encoding="utf-8")
    assert set(ler_iptu(p)) == {"Q01L01", "Q01L02"}


def _df_set26():
    vazio = [None] * 15
    cab = ["QUADRA", "LOTE", None, "CLASSIFICAÇÃO", "PREÇO m²"] + [None] * 10
    linha = lambda q, l, a, c, m2, tot: [q, l, a, c, m2] + [None] * 9 + [tot]
    return pd.DataFrame(
        [
            vazio,
            [None, None, 137584.03] + [None] * 12,  # totais soltos acima do cabeçalho
            cab,
            [None, None, "ÁREA"] + [None] * 12,
            linha("H", 1, 14640.57, "D", 990, 14494164.3),
            linha(1, 1, 732.01, "A", 1380, 1010173.8),
            linha(1.0, 2.0, 480, "A", 1380, 662400),
            [None, None, 160858.19] + [None] * 12,  # linha de total, quadra vazia
        ]
    )


def test_linhas_tabela():
    t = linhas_tabela(_df_set26())
    assert set(t) == {"QHL01", "Q01L01", "Q01L02"}
    assert t["Q01L02"] == LinhaPreco(area_m2=480.0, classificacao="A", preco_m2=1380.0, preco_total=662400.0)


def test_linhas_tabela_corrige_quadra_14_14():
    # Na SET26 real, os lotes 1–7 da quadra 14 estão digitados como "14.14".
    df = _df_set26()
    df.loc[len(df)] = [14.14, 1, 487.01, "B", 1250] + [None] * 9 + [608762.5]
    assert "Q14L01" in linhas_tabela(df)


def test_linhas_tabela_lote_duplicado_falha():
    df = _df_set26()
    df.loc[len(df)] = df.iloc[5]
    with pytest.raises(ValueError, match="Q01L01"):
        linhas_tabela(df)
