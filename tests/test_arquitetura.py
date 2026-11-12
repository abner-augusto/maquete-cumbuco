import ast

from scripts.comum.ambiente import RAIZ

SCRIPTS = RAIZ / "scripts"
DENTRO_DO_BLENDER = SCRIPTS / "blender"
REGISTRO_DA_CONVERSAO = SCRIPTS / "marcos" / "conversao"
MODULOS_DO_BLENDER = {"bpy", "bmesh", "mathutils"}


def _importados(arquivo) -> set[str]:
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    nomes = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            nomes.update(alias.name for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module and no.level == 0:
            nomes.add(no.module)
    return nomes


def _raizes(nomes: set[str]) -> set[str]:
    return {nome.split(".")[0] for nome in nomes}


def _relativo(arquivo) -> str:
    return arquivo.relative_to(RAIZ).as_posix()


def test_so_scripts_blender_importa_a_api_do_blender():
    fora = [
        arquivo for arquivo in SCRIPTS.rglob("*.py")
        if DENTRO_DO_BLENDER not in arquivo.parents and REGISTRO_DA_CONVERSAO not in arquivo.parents
    ]
    assert fora
    infratores = {_relativo(a): sorted(usados) for a in fora if (usados := _raizes(_importados(a)) & MODULOS_DO_BLENDER)}
    assert not infratores, f"a geometria é Python puro; só scripts/blender/ importa o Blender: {infratores}"


def test_scripts_blender_nao_importa_o_pipeline():
    dentro = list(DENTRO_DO_BLENDER.glob("*.py"))
    assert dentro
    infratores = {_relativo(a): sorted(usados) for a in dentro if (usados := _raizes(_importados(a)) & {"scripts"})}
    assert not infratores, f"scripts/blender/ só constrói a partir do JSON de cena, sem importar o pipeline: {infratores}"
