import pytest

from scripts.comum.ambiente import ler_env, terreno_dir


def test_ler_env_ignora_comentarios_e_aspas(tmp_path):
    env = tmp_path / ".env"
    env.write_text('# c\nTERRENO_DIR="C:\\x y"\n\nOUTRA=1\n', encoding="utf-8")
    assert ler_env(env) == {"TERRENO_DIR": "C:\\x y", "OUTRA": "1"}


def test_terreno_dir_le_do_env(tmp_path, monkeypatch):
    monkeypatch.delenv("TERRENO_DIR", raising=False)
    pasta = tmp_path / "terreno"
    pasta.mkdir()
    env = tmp_path / ".env"
    env.write_text(f"TERRENO_DIR={pasta}\n", encoding="utf-8")
    assert terreno_dir(env) == pasta


def test_variavel_de_ambiente_tem_precedencia(tmp_path, monkeypatch):
    pasta = tmp_path / "outra"
    pasta.mkdir()
    monkeypatch.setenv("TERRENO_DIR", str(pasta))
    assert terreno_dir(tmp_path / "nao-existe.env") == pasta


def test_terreno_dir_ausente_explica(tmp_path, monkeypatch):
    monkeypatch.delenv("TERRENO_DIR", raising=False)
    with pytest.raises(RuntimeError, match="TERRENO_DIR ausente"):
        terreno_dir(tmp_path / ".env")


def test_terreno_dir_inexistente_explica(tmp_path, monkeypatch):
    monkeypatch.setenv("TERRENO_DIR", str(tmp_path / "sumiu"))
    with pytest.raises(RuntimeError, match="não existe"):
        terreno_dir(tmp_path / ".env")
