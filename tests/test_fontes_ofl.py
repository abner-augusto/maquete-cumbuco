import hashlib

import pytest

from scripts.marca.fontes import FONTES, baixar


def _origem(tmp_path, conteudo=b"fonte"):
    o = tmp_path / "origem.ttf"
    o.write_bytes(conteudo)
    return o.as_uri(), hashlib.sha256(conteudo).hexdigest()


def test_baixa_e_confere_hash(tmp_path):
    url, sha = _origem(tmp_path)
    destino = tmp_path / "cache" / "f.ttf"
    assert baixar(url, destino, sha).read_bytes() == b"fonte"


def test_hash_errado_nao_grava(tmp_path):
    url, _ = _origem(tmp_path)
    destino = tmp_path / "f.ttf"
    with pytest.raises(ValueError, match="SHA-256"):
        baixar(url, destino, "0" * 64)
    assert not destino.exists()


def test_arquivo_presente_com_hash_certo_nao_baixa_de_novo(tmp_path):
    destino = tmp_path / "f.ttf"
    destino.write_bytes(b"fonte")
    sha = hashlib.sha256(b"fonte").hexdigest()
    assert baixar("file:///nao/existe.ttf", destino, sha) == destino


def test_fontes_fixas_em_commit_com_licenca():
    assert {"Cinzel[wght].ttf", "Jost[wght].ttf", "Cinzel-OFL.txt", "Jost-OFL.txt"} == set(FONTES)
    for url, sha in FONTES.values():
        assert "/main/" not in url and len(sha) == 64
