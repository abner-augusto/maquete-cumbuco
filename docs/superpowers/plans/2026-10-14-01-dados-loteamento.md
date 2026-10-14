# Plano 1 — Fundação e dados do loteamento

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gerar, por script e sem número digitado à mão, `dados/lotes.json`, `dados/georref.json` e `dados/relatorio-conferencia.md` da Fase 1 a partir do `PLANTA VENDA.dwg`, do índice de IPTU e da tabela SET26.

**Architecture:** Projeto Python (uv) na raiz do repo, com o pacote `scripts/`. O DWG vira DXF pelo `accoreconsole` do AutoCAD 2018. Um inventário de layers vai para o Abner conferir (gate). Depois, módulos pequenos e puros (ids, fontes, geometria, extração, georreferência, conferência) são orquestrados por `scripts/loteamento/gerar_dados.py`, que falha quando a conferência acha erro.

**Tech Stack:** Python 3.12+ (máquina tem 3.14), uv, ezdxf 1.4.4, pandas + python-calamine (para `.xls`), pytest.

**Spec:** `docs/superpowers/specs/2026-10-14-maquete-cumbuco-design.md` (§3, §6, §7.1 passos 1–2, §9)
**Plano-mestre:** `docs/superpowers/plans/2026-10-14-00-plano-mestre.md`

## Global Constraints

- Nenhum número do front é digitado à mão: tudo em `dados/` sai de `scripts/`.
- A pasta do terreno vem de `TERRENO_DIR` no `.env` (gitignored); o repo nunca copia arquivos do cliente, só deriva dados deles.
- Id de lote: `Q<quadra>L<lote>`; quadra numérica com 2 dígitos (`Q07L04`), alfabética com a letra (`QHL01`); lote com 2 dígitos.
- CRS: SIRGAS 2000 / UTM 24S (`EPSG:31984`). Origem local arredondada a 100 m.
- Tolerância de área: 0,5% (`toleranciaArea: 0.005` no `config.json`).
- `mostrarPrecos` padrão `false`. Com `false`, **nenhum preço vai para `lotes.json`**. Se o preço estivesse no JSON, qualquer um o leria no navegador, e a regra "a URL não liga os preços" da spec §6 seria só aparência.
- Erro de conferência faz o script sair com código 1 e **não** grava `lotes.json`; o relatório é sempre gravado.
- Docs, mensagens e commits em português do Brasil.

**Interpretação da spec:** o "cadastro" da regra "lote no desenho sem linha no cadastro" é a **tabela de lotes (SET26)**, que lista os 347 lotes. O índice de IPTU é parcial (325) e só gera aviso, como a spec manda.

## Review Focus

1. **Rótulos com formatos variados** (`07`, `7`, `7.0`, `Q-07`, `QUADRA 07`, `LT 4`) entre DWG, tabela e IPTU precisam virar o mesmo id. Teste na Task 2.
2. **Lotes com frente em arco** (polilinha com bulge, comum em esquina e rotatória): a área não pode sair pela corda, senão a tolerância de 0,5% acusa erro falso. Teste na Task 3.
3. **Polilinha de lote "aberta" com o último ponto igual ao primeiro** deve contar como fechada, senão o lote some sem aviso. Teste na Task 3.
4. **Lote com zero ou dois rótulos dentro**, ou fora de qualquer quadra: o erro precisa nomear o handle do CAD para achar o lote. Teste na Task 5.
5. **`mostrarPrecos: false`**: nenhum campo de preço em lugar nenhum do `lotes.json`. Teste na Task 8. Um **CSV do IPTU salvo em cp1252** pelo Excel também precisa ser lido. Teste na Task 2.

---

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `pyproject.toml` | Projeto uv, dependências e configuração do pytest |
| `.env.example` | `TERRENO_DIR` e `ACCORE` de exemplo |
| `scripts/__init__.py`, `scripts/comum/__init__.py`, `scripts/loteamento/__init__.py` | Pacotes |
| `scripts/comum/ambiente.py` | `RAIZ`, leitura do `.env`, `terreno_dir()` |
| `scripts/loteamento/ids.py` | Normalização de quadra e lote, `id_lote`, `tipo_por_quadra` |
| `scripts/loteamento/fontes.py` | `ler_iptu`, `LinhaPreco`, `linhas_tabela`, `ler_tabela_set26` |
| `scripts/loteamento/geometria.py` | Pontos, área, centroide, ponto-em-polígono, segmentos com bulge, frente |
| `scripts/loteamento/converter_dwg.py` | DWG → DXF via `accoreconsole` |
| `scripts/loteamento/inventario.py` | Inventário de layers → `dados/inventario-layers.md` |
| `scripts/loteamento/layers.toml` | Mapa papel → layer, preenchido no gate |
| `scripts/loteamento/extrair.py` | `MapaLayers`, `LoteBruto`, `extrair_lotes` |
| `scripts/loteamento/georref.py` | Checagem de UTM 24S, origem local, `georref.json` |
| `scripts/loteamento/conferir.py` | `Relatorio`, `conferir`, `escrever_relatorio` |
| `scripts/loteamento/saida.py` | `Config`, `carregar_config`, `montar_lotes_json` |
| `scripts/loteamento/gerar_dados.py` | Orquestração e CLI |
| `dados/config.json` | Editado à mão |
| `tests/conftest.py` | DXF sintético e fixtures |
| `tests/test_*.py` | Um arquivo por módulo |
| `cache/` | DWG copiado e DXF gerado (gitignored) |

---

### Task 1: Projeto Python e ambiente

**Files:**
- Create: `pyproject.toml`, `.env.example`, `scripts/__init__.py`, `scripts/comum/__init__.py`, `scripts/loteamento/__init__.py`, `scripts/comum/ambiente.py`, `tests/test_ambiente.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `scripts.comum.ambiente.RAIZ: Path`, `ler_env(caminho: Path) -> dict[str, str]`, `terreno_dir(env_path: Path = RAIZ / ".env") -> Path`

- [ ] **Step 1: Criar `pyproject.toml`**

```toml
[project]
name = "maquete-cumbuco"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["ezdxf==1.4.4", "pandas>=2.2", "python-calamine>=0.8"]

[dependency-groups]
dev = ["pytest>=8"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 2: Criar `.env.example` e completar o `.gitignore`**

`.env.example`:
```
# Pasta do terreno (raiz das fontes de verdade)
TERRENO_DIR=<caminho da pasta do terreno>
ACCORE=C:\Program Files\Autodesk\AutoCAD 2018\accoreconsole.exe
```

Acrescentar ao `.gitignore`:
```
cache/
.venv/
.pytest_cache/
```

Copiar `.env.example` para `.env` (o `.env` não vai ao git).

- [ ] **Step 3: Escrever o teste que falha**

`tests/test_ambiente.py`:
```python
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
```

- [ ] **Step 4: Rodar e ver falhar**

Run: `uv sync && uv run pytest tests/test_ambiente.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'scripts.comum.ambiente'`

- [ ] **Step 5: Implementar**

Criar os três `__init__.py` vazios e `scripts/comum/ambiente.py`:
```python
"""Raiz do repo e leitura do .env (sem dependência externa)."""

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def ler_env(caminho: Path) -> dict[str, str]:
    valores: dict[str, str] = {}
    if not caminho.exists():
        return valores
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        valores[chave.strip()] = valor.strip().strip('"')
    return valores


def terreno_dir(env_path: Path = RAIZ / ".env") -> Path:
    valor = os.environ.get("TERRENO_DIR") or ler_env(env_path).get("TERRENO_DIR")
    if not valor:
        raise RuntimeError("TERRENO_DIR ausente: defina no .env (modelo em .env.example)")
    pasta = Path(valor)
    if not pasta.is_dir():
        raise RuntimeError(f"TERRENO_DIR não existe: {pasta}")
    return pasta
```

- [ ] **Step 6: Rodar e ver passar**

Run: `uv run pytest tests/test_ambiente.py -v`
Expected: 5 passed

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock .env.example .gitignore scripts tests
git commit -m "feat(dados): projeto Python e leitura do TERRENO_DIR"
```

---

### Task 2: Ids de lote e leitura das fontes (IPTU e SET26)

**Files:**
- Create: `scripts/loteamento/ids.py`, `scripts/loteamento/fontes.py`, `tests/test_ids.py`, `tests/test_fontes.py`

**Interfaces:**
- Produces:
  - `ids.normalizar_quadra(q) -> str` (`"07"` ou `"H"`), `ids.normalizar_lote(l) -> str` (`"04"`), `ids.id_lote(q, l) -> str` (`"Q07L04"`), `ids.tipo_por_quadra(q) -> str` (`"residencial"` | `"uso_misto"`)
  - `fontes.ler_iptu(caminho: Path) -> dict[str, str]` (id → inscrição)
  - `fontes.LinhaPreco(area_m2: float, classificacao: str, preco_m2: float, preco_total: float)` (frozen dataclass)
  - `fontes.linhas_tabela(df: pandas.DataFrame) -> dict[str, LinhaPreco]`, `fontes.ler_tabela_set26(caminho: Path) -> dict[str, LinhaPreco]`

**Contexto da SET26:** a aba `"12, 24 e 36meses"`, lida com `header=None`, tem na coluna 0 uma linha com o texto `QUADRA` (cabeçalho, linha 7). Os dados vêm depois: coluna 0 = quadra (`H`, `M`, `1`, `2`…), 1 = lote, 2 = área (m²), 3 = classificação (`A`–`D`), 4 = preço/m², 14 = preço total à vista. As linhas de totais têm a coluna 0 vazia. A aba `VENDAS BKP` é de **outro loteamento** (Itatiba) e não deve ser lida. Quadras alfabéticas (H, M) são os lotes de uso misto (decisão de 05/10/2026: "H1 e M1–M4, torres comerciais vendidas como lote").

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_ids.py`:
```python
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
```

`tests/test_fontes.py`:
```python
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


def test_linhas_tabela_lote_duplicado_falha():
    df = _df_set26()
    df.loc[len(df)] = df.iloc[5]
    with pytest.raises(ValueError, match="Q01L01"):
        linhas_tabela(df)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_ids.py tests/test_fontes.py -v`
Expected: FAIL com `ModuleNotFoundError`

- [ ] **Step 3: Implementar `scripts/loteamento/ids.py`**

```python
"""Id canônico de lote: Q<quadra>L<lote> (Q07L04, QHL01)."""

import re

_PREFIXO_QUADRA = re.compile(r"^(QUADRA|QD\.?|Q)\s*-?\s*")
_PREFIXO_LOTE = re.compile(r"^(LOTE|LT\.?|L)\s*-?\s*")
_INTEIRO = re.compile(r"\d+(\.0+)?")


def normalizar_quadra(q) -> str:
    if q is None:
        raise ValueError("quadra vazia")
    s = _PREFIXO_QUADRA.sub("", str(q).strip().upper())
    if _INTEIRO.fullmatch(s):
        return f"{int(float(s)):02d}"
    if re.fullmatch(r"[A-Z]", s):
        return s
    raise ValueError(f"quadra inválida: {q!r}")


def normalizar_lote(l) -> str:
    if l is None:
        raise ValueError("lote vazio")
    s = _PREFIXO_LOTE.sub("", str(l).strip().upper())
    if _INTEIRO.fullmatch(s):
        return f"{int(float(s)):02d}"
    raise ValueError(f"lote inválido: {l!r}")


def id_lote(q, l) -> str:
    return f"Q{normalizar_quadra(q)}L{normalizar_lote(l)}"


def tipo_por_quadra(q) -> str:
    return "uso_misto" if normalizar_quadra(q).isalpha() else "residencial"
```

Atenção: `"QUADRA H"` precisa perder o prefixo `QUADRA ` antes do teste de letra. A regex tenta `QUADRA` antes de `Q`, então `"Q-M"` vira `M`. Uma quadra literalmente chamada `Q` não existe no loteamento.

- [ ] **Step 4: Implementar `scripts/loteamento/fontes.py`**

```python
"""Leitura das fontes tabulares: índice de IPTU (CSV) e tabela SET26 (XLS)."""

import csv
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .ids import id_lote

ABA_SET26 = "12, 24 e 36meses"
COL_QUADRA, COL_LOTE, COL_AREA, COL_CLASSIF, COL_PRECO_M2, COL_TOTAL = 0, 1, 2, 3, 4, 14


def _ler_texto(caminho: Path) -> str:
    dados = caminho.read_bytes()
    for codificacao in ("utf-8-sig", "cp1252"):
        try:
            return dados.decode(codificacao)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"codificação desconhecida: {caminho}")


def ler_iptu(caminho: Path) -> dict[str, str]:
    inscricoes: dict[str, str] = {}
    for linha in csv.DictReader(_ler_texto(caminho).splitlines(), delimiter=";"):
        i = id_lote(linha["quadra"], linha["lote"])
        inscricao = linha["inscricao"].strip()
        if i in inscricoes and inscricoes[i] != inscricao:
            raise ValueError(f"{i}: duas inscrições ({inscricoes[i]}, {inscricao})")
        inscricoes[i] = inscricao
    return inscricoes


@dataclass(frozen=True)
class LinhaPreco:
    area_m2: float
    classificacao: str
    preco_m2: float
    preco_total: float


def _numero(v) -> bool:
    return isinstance(v, (int, float)) and not pd.isna(v)


def linhas_tabela(df: pd.DataFrame) -> dict[str, LinhaPreco]:
    cabecalho = next(
        i for i, v in enumerate(df[COL_QUADRA]) if str(v).strip().upper() == "QUADRA"
    )
    linhas: dict[str, LinhaPreco] = {}
    for _, r in df.iloc[cabecalho + 1 :].iterrows():
        q, l = r[COL_QUADRA], r[COL_LOTE]
        if pd.isna(q) or pd.isna(l) or not _numero(r[COL_AREA]):
            continue
        i = id_lote(q, l)
        if i in linhas:
            raise ValueError(f"{i} duplicado na tabela")
        linhas[i] = LinhaPreco(
            area_m2=float(r[COL_AREA]),
            classificacao=str(r[COL_CLASSIF]).strip(),
            preco_m2=float(r[COL_PRECO_M2]),
            preco_total=float(r[COL_TOTAL]),
        )
    return linhas


def ler_tabela_set26(caminho: Path) -> dict[str, LinhaPreco]:
    return linhas_tabela(pd.read_excel(caminho, sheet_name=ABA_SET26, header=None))
```

- [ ] **Step 5: Rodar e ver passar**

Run: `uv run pytest tests/test_ids.py tests/test_fontes.py -v`
Expected: todos passam

- [ ] **Step 6: Conferir contra os arquivos reais (sem gravar nada)**

Run:
```bash
uv run python -c "from scripts.comum.ambiente import terreno_dir as t; from scripts.loteamento.fontes import *; d=t(); i=ler_iptu(d/'4-PREFEITURA/IPTU_2025/00-INDICE IPTU 2025 - LOTES CANCUN.csv'); s=ler_tabela_set26(d/'1-ADMINISTRATIVO/FINANCEIRO/Tab Lancamento SET26 R01.xls'); print(len(i), len(s), sorted(s)[:3], sorted(set(i)-set(s))[:5])"
```
Expected: `325 347 ...`, e a lista de ids do IPTU fora da tabela (idealmente vazia). Anote o resultado na mensagem do commit; não corrija dados à mão.

- [ ] **Step 7: Commit**

```bash
git add scripts/loteamento/ids.py scripts/loteamento/fontes.py tests/test_ids.py tests/test_fontes.py
git commit -m "feat(dados): id canônico de lote e leitura do IPTU e da SET26"
```

---

### Task 3: Geometria de polígonos (com arcos)

**Files:**
- Create: `scripts/loteamento/geometria.py`, `tests/test_geometria.py`

**Interfaces:**
- Produces (`Ponto = tuple[float, float]`):
  - `poligono_fechado(e) -> bool` (LWPOLYLINE com `closed` ou primeiro ponto = último)
  - `pontos_de(e, distancia: float = 0.05) -> list[Ponto]` (achata arcos; sem ponto de fechamento duplicado)
  - `area(pts) -> float`, `centroide(pts) -> Ponto`, `contem(pts, p) -> bool`, `extensao(pts) -> tuple[float, float, float, float]`
  - `segmentos(e) -> list[tuple[Ponto, Ponto, float]]` (início, fim, comprimento real, inclusive em arco)
  - `indice_frente(segs, vias: list[list[Ponto]]) -> int` (segmento cujo ponto médio está mais perto de uma via)

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_geometria.py`:
```python
import math

import ezdxf
import pytest

from scripts.loteamento.geometria import (
    area, centroide, contem, extensao, indice_frente, pontos_de, poligono_fechado, segmentos,
)

E0, N0 = 500_000.0, 9_600_000.0


def _lw(pontos, close=True, fmt="xy"):
    msp = ezdxf.new().modelspace()
    return msp.add_lwpolyline(pontos, format=fmt, close=close)


def test_retangulo_em_coordenadas_utm():
    e = _lw([(E0, N0), (E0 + 10, N0), (E0 + 10, N0 + 20), (E0, N0 + 20)])
    pts = pontos_de(e)
    assert area(pts) == pytest.approx(200.0, abs=1e-6)
    assert centroide(pts) == pytest.approx((E0 + 5, N0 + 10))
    assert [round(s[2], 6) for s in segmentos(e)] == [10, 20, 10, 20]
    assert extensao(pts) == (E0, N0, E0 + 10, N0 + 20)


def test_aberta_com_ponto_final_igual_conta_como_fechada():
    e = _lw([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)], close=False)
    assert poligono_fechado(e)
    assert len(pontos_de(e)) == 4
    assert len(segmentos(e)) == 4


def test_aberta_de_verdade_nao_e_poligono():
    assert not poligono_fechado(_lw([(0, 0), (10, 0), (10, 10)], close=False))


def test_frente_em_arco_soma_o_segmento_circular():
    b = 0.2  # aresta de baixo vira arco para fora (sentido anti-horário)
    e = _lw([(0, 0, b), (30, 0, 0), (30, 20, 0), (0, 20, 0)], fmt="xyb")
    theta = 4 * math.atan(b)
    r = 30 / (2 * math.sin(theta / 2))
    segmento_circular = r * r / 2 * (theta - math.sin(theta))
    assert area(pontos_de(e)) == pytest.approx(600 + segmento_circular, rel=1e-3)
    assert segmentos(e)[0][2] == pytest.approx(r * theta, rel=1e-9)


def test_contem():
    q = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert contem(q, (5, 5))
    assert not contem(q, (15, 5))


def test_indice_frente_e_o_lado_mais_proximo_da_via():
    e = _lw([(0, 0), (10, 0), (10, 20), (0, 20)])
    via = [(-5, -3), (50, -3)]
    assert indice_frente(segmentos(e), [via]) == 0
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_geometria.py -v`
Expected: FAIL com `ModuleNotFoundError`

- [ ] **Step 3: Implementar `scripts/loteamento/geometria.py`**

```python
"""Geometria plana dos polígonos do DXF. Calcula relativo ao 1º ponto para não perder precisão em UTM."""

import math

from ezdxf import path

Ponto = tuple[float, float]
_EPS = 1e-6


def poligono_fechado(e) -> bool:
    if e.dxftype() != "LWPOLYLINE":
        return False
    if e.closed:
        return True
    pts = e.get_points("xy")
    return len(pts) >= 4 and math.dist(pts[0], pts[-1]) < _EPS


def pontos_de(e, distancia: float = 0.05) -> list[Ponto]:
    pts = [(v.x, v.y) for v in path.make_path(e).flattening(distance=distancia)]
    if len(pts) > 1 and math.dist(pts[0], pts[-1]) < _EPS:
        pts = pts[:-1]
    return pts


def _relativos(pts: list[Ponto]) -> tuple[Ponto, list[Ponto]]:
    ox, oy = pts[0]
    return (ox, oy), [(x - ox, y - oy) for x, y in pts]


def area(pts: list[Ponto]) -> float:
    _, r = _relativos(pts)
    s = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(r, r[1:] + r[:1]))
    return abs(s) / 2


def centroide(pts: list[Ponto]) -> Ponto:
    (ox, oy), r = _relativos(pts)
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(r, r[1:] + r[:1]):
        c = x0 * y1 - x1 * y0
        a += c
        cx += (x0 + x1) * c
        cy += (y0 + y1) * c
    a /= 2
    return (ox + cx / (6 * a), oy + cy / (6 * a))


def contem(pts: list[Ponto], p: Ponto) -> bool:
    x, y = p
    dentro = False
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            dentro = not dentro
    return dentro


def extensao(pts: list[Ponto]) -> tuple[float, float, float, float]:
    xs = [x for x, _ in pts]
    ys = [y for _, y in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def segmentos(e) -> list[tuple[Ponto, Ponto, float]]:
    pts = list(e.get_points("xyb"))
    if len(pts) > 1 and math.dist(pts[0][:2], pts[-1][:2]) < _EPS:
        pts = pts[:-1]
    saida = []
    for i, (x0, y0, b) in enumerate(pts):
        x1, y1, _ = pts[(i + 1) % len(pts)]
        corda = math.dist((x0, y0), (x1, y1))
        if abs(b) < 1e-12:
            comprimento = corda
        else:
            theta = 4 * math.atan(abs(b))
            comprimento = corda / (2 * math.sin(theta / 2)) * theta
        saida.append(((x0, y0), (x1, y1), comprimento))
    return saida


def _dist_ponto_segmento(p: Ponto, a: Ponto, b: Ponto) -> float:
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.dist(p, (ax + t * dx, ay + t * dy))


def indice_frente(segs: list[tuple[Ponto, Ponto, float]], vias: list[list[Ponto]]) -> int:
    def distancia(seg) -> float:
        (x0, y0), (x1, y1), _ = seg
        meio = ((x0 + x1) / 2, (y0 + y1) / 2)
        return min(_dist_ponto_segmento(meio, a, b) for via in vias for a, b in zip(via, via[1:]))

    return min(range(len(segs)), key=lambda i: distancia(segs[i]))
```

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_geometria.py -v`
Expected: 6 passed. Se o teste do arco falhar pelo sinal do bulge (o arco foi para dentro), troque `b = 0.2` por `b = -0.2` **só no teste**, conferindo que a área aumentou. A implementação usa `abs(b)` e não depende do sinal.

- [ ] **Step 5: Commit**

```bash
git add scripts/loteamento/geometria.py tests/test_geometria.py
git commit -m "feat(dados): geometria de polígonos com arcos e frente pela via"
```

---

### Task 4: DWG → DXF e inventário de layers (⛔ gate)

**Files:**
- Create: `scripts/loteamento/converter_dwg.py`, `scripts/loteamento/inventario.py`, `scripts/loteamento/layers.toml`, `tests/test_converter_dwg.py`, `tests/test_inventario.py`
- Gera (commitado): `dados/inventario-layers.md`, `dados/inventario-layers-masterplan.md`

**Interfaces:**
- Consumes: `geometria.poligono_fechado`, `ambiente.terreno_dir`, `ambiente.ler_env`, `ambiente.RAIZ`
- Produces:
  - `converter_dwg.FONTES: dict[str, str]` (nome → caminho relativo ao terreno), `script_dxfout(dxf: Path) -> str`, `converter(dwg: Path, dxf: Path, accore: Path) -> None`
  - `inventario.LayerResumo(nome, por_tipo: dict[str, int], fechadas: int, blocos: dict[str, int], textos: list[str], extensao: tuple | None)`, `inventariar(doc) -> list[LayerResumo]`, `escrever_md(resumos, destino: Path, titulo: str) -> None`
  - `cache/dxf/planta-venda.dxf`, `cache/dxf/masterplan-r05.dxf`

**Por que copiar o DWG antes:** o caminho tem acentos e vírgula (`AMÉRICAS- MASTERPLAN GERAL-R05,.dwg`), e o `accoreconsole` e os arquivos `.scr` lidam mal com isso. A cópia em `cache/dwg/<nome>.dwg` deixa o caminho em ASCII.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_converter_dwg.py`:
```python
from pathlib import Path

from scripts.loteamento.converter_dwg import FONTES, script_dxfout


def test_script_dxfout_exporta_2013_com_precisao_maxima():
    scr = script_dxfout(Path(r"C:\cache\dxf\planta-venda.dxf"))
    linhas = scr.splitlines()
    assert linhas[0] == "FILEDIA 0"
    assert linhas[1] == '_.DXFOUT "C:\\cache\\dxf\\planta-venda.dxf" _V 2013 16'
    assert scr.isascii()


def test_fontes_apontam_para_dwg_do_urbanismo():
    assert FONTES["planta-venda"] == "6-PROJETOS/01-URBANISMO/DWG/PLANTA VENDA.dwg"
    assert FONTES["masterplan-r05"].endswith("MASTERPLAN GERAL-R05,.dwg")
```

`tests/test_inventario.py`:
```python
import ezdxf

from scripts.loteamento.inventario import escrever_md, inventariar


def test_inventario_resume_por_layer(tmp_path):
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (10, 0), (10, 10), (0, 10)], close=True, dxfattribs={"layer": "LOTES"})
    msp.add_lwpolyline([(0, 0), (5, 5)], dxfattribs={"layer": "LOTES"})
    msp.add_text("12", dxfattribs={"layer": "NUM"})
    bloco = doc.blocks.new("ROTULO")
    bloco.add_attdef("N", (0, 0))
    msp.add_blockref("ROTULO", (1, 1), dxfattribs={"layer": "NUM"}).add_auto_attribs({"N": "7"})

    resumos = {r.nome: r for r in inventariar(doc)}
    assert resumos["LOTES"].por_tipo == {"LWPOLYLINE": 2}
    assert resumos["LOTES"].fechadas == 1
    assert resumos["NUM"].blocos == {"ROTULO": 1}
    assert set(resumos["NUM"].textos) == {"12", "7"}

    destino = tmp_path / "inv.md"
    escrever_md(list(resumos.values()), destino, "Teste")
    texto = destino.read_text(encoding="utf-8")
    assert "| LOTES |" in texto and "LWPOLYLINE: 2" in texto
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_converter_dwg.py tests/test_inventario.py -v`
Expected: FAIL com `ModuleNotFoundError`

- [ ] **Step 3: Implementar `scripts/loteamento/converter_dwg.py`**

```python
"""DWG → DXF pelo accoreconsole do AutoCAD. Uso: uv run python -m scripts.loteamento.converter_dwg"""

import shutil
import subprocess
import sys
from pathlib import Path

from scripts.comum.ambiente import RAIZ, ler_env, terreno_dir

FONTES = {
    "planta-venda": "6-PROJETOS/01-URBANISMO/DWG/PLANTA VENDA.dwg",
    "masterplan-r05": "6-PROJETOS/01-URBANISMO/DWG/00-CIDADE DAS AMÉRICAS- MASTERPLAN GERAL-R05,.dwg",
}
ACCORE_PADRAO = Path(r"C:\Program Files\Autodesk\AutoCAD 2018\accoreconsole.exe")


def script_dxfout(dxf: Path) -> str:
    return "\n".join(["FILEDIA 0", f'_.DXFOUT "{dxf}" _V 2013 16', ""])


def converter(dwg: Path, dxf: Path, accore: Path) -> None:
    dxf.parent.mkdir(parents=True, exist_ok=True)
    dxf.unlink(missing_ok=True)
    scr = dxf.with_suffix(".scr")
    scr.write_text(script_dxfout(dxf), encoding="ascii")
    r = subprocess.run(
        [str(accore), "/i", str(dwg), "/s", str(scr), "/l", "en-US"],
        capture_output=True, timeout=900,
    )
    if not dxf.exists():
        saida = r.stdout.decode("utf-16-le", errors="replace")[-2000:]
        raise RuntimeError(f"accoreconsole não gerou {dxf} (código {r.returncode}):\n{saida}")


def main() -> int:
    terreno = terreno_dir()
    accore = Path(ler_env(RAIZ / ".env").get("ACCORE", ACCORE_PADRAO))
    for nome, relativo in FONTES.items():
        copia = RAIZ / "cache" / "dwg" / f"{nome}.dwg"
        copia.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(terreno / relativo, copia)
        destino = RAIZ / "cache" / "dxf" / f"{nome}.dxf"
        converter(copia, destino, accore)
        print(f"{nome}: {destino} ({destino.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Implementar `scripts/loteamento/inventario.py`**

```python
"""Inventário de layers de um DXF, para decidir o layers.toml. Uso: uv run python -m scripts.loteamento.inventario"""

import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import ezdxf
from ezdxf import bbox

from scripts.comum.ambiente import RAIZ

from .geometria import poligono_fechado

_AMOSTRAS = 8


@dataclass
class LayerResumo:
    nome: str
    por_tipo: dict[str, int]
    fechadas: int
    blocos: dict[str, int]
    textos: list[str]
    extensao: tuple[float, float, float, float] | None


def _textos(e) -> list[str]:
    t = e.dxftype()
    if t == "TEXT":
        return [e.dxf.text.strip()]
    if t == "MTEXT":
        return [e.plain_text().strip()]
    if t == "INSERT":
        return [a.dxf.text.strip() for a in e.attribs]
    return []


def inventariar(doc) -> list[LayerResumo]:
    grupos = defaultdict(list)
    for e in doc.modelspace():
        grupos[e.dxf.layer].append(e)
    resumos = []
    for nome in sorted(grupos):
        ents = grupos[nome]
        textos = [t for e in ents for t in _textos(e) if t]
        caixa = bbox.extents(ents, fast=True)
        resumos.append(
            LayerResumo(
                nome=nome,
                por_tipo=dict(Counter(e.dxftype() for e in ents)),
                fechadas=sum(1 for e in ents if poligono_fechado(e)),
                blocos=dict(Counter(e.dxf.name for e in ents if e.dxftype() == "INSERT")),
                textos=list(dict.fromkeys(textos))[:_AMOSTRAS],
                extensao=(caixa.extmin.x, caixa.extmin.y, caixa.extmax.x, caixa.extmax.y) if caixa.has_data else None,
            )
        )
    return resumos


def escrever_md(resumos: list[LayerResumo], destino: Path, titulo: str) -> None:
    linhas = [
        f"# Inventário de layers — {titulo}",
        "",
        "Gerado por `scripts/loteamento/inventario.py`. Serve para preencher `scripts/loteamento/layers.toml`.",
        "",
        "| Layer | Entidades | Polilinhas fechadas | Blocos | Amostra de textos | Extensão (xmin, ymin, xmax, ymax) |",
        "|---|---|---:|---|---|---|",
    ]
    for r in resumos:
        tipos = ", ".join(f"{k}: {v}" for k, v in sorted(r.por_tipo.items()))
        blocos = ", ".join(f"{k}: {v}" for k, v in sorted(r.blocos.items()))
        textos = " · ".join(t.replace("|", "/") for t in r.textos)
        ext = "" if r.extensao is None else ", ".join(f"{v:.1f}" for v in r.extensao)
        linhas.append(f"| {r.nome} | {tipos} | {r.fechadas} | {blocos} | {textos} | {ext} |")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def main() -> int:
    for nome, sufixo in (("planta-venda", ""), ("masterplan-r05", "-masterplan")):
        doc = ezdxf.readfile(RAIZ / "cache" / "dxf" / f"{nome}.dxf")
        escrever_md(inventariar(doc), RAIZ / "dados" / f"inventario-layers{sufixo}.md", nome)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Rodar os testes e ver passar**

Run: `uv run pytest tests/test_converter_dwg.py tests/test_inventario.py -v`
Expected: 3 passed

- [ ] **Step 6: Converter os DWGs reais**

Run: `uv run python -m scripts.loteamento.converter_dwg`
Expected: duas linhas `planta-venda: ...cache\dxf\planta-venda.dxf (NNN KB)` e `masterplan-r05: ...`.

Se o `accoreconsole` não gerar o DXF, a mensagem traz o fim da saída do console. Leia os prompts que o AutoCAD 2018 mostrou e ajuste **apenas** a linha `_.DXFOUT` de `script_dxfout` e o teste dela para a sequência real de respostas. Plano B, se o console não servir: abrir o DWG no AutoCAD 2018, `SAVEAS` → *AutoCAD 2013 DXF*, gravar em `cache/dxf/<nome>.dxf` e registrar isso na mensagem do commit.

- [ ] **Step 7: Gerar os inventários**

Run: `uv run python -m scripts.loteamento.inventario`
Expected: `dados/inventario-layers.md` e `dados/inventario-layers-masterplan.md` com uma linha por layer.

- [ ] **Step 8: Escrever o rascunho de `scripts/loteamento/layers.toml` a partir do inventário**

Escolha, pelo inventário da planta de venda, a layer de cada papel:
- `lotes`: layer com muitas polilinhas fechadas, cerca de 347.
- `rotulo_lote`: layer com textos ou atributos numéricos curtos.
- `quadras`: layer com cerca de 20 polilinhas fechadas.
- `rotulo_quadra`: textos do tipo `QUADRA 07` ou `07`.
- `meio_fio`: as polilinhas abertas que contornam as quadras.

```toml
# Mapa papel → layer do PLANTA VENDA.dwg. Conferido pelo Abner em <data> (gate da Task 4 do Plano 1).
lotes = "<layer dos polígonos de lote>"
rotulo_lote = "<layer dos números de lote>"
quadras = "<layer dos polígonos de quadra>"
rotulo_quadra = "<layer dos rótulos de quadra>"
meio_fio = "<layer do meio-fio ou alinhamento das vias>"
```

Anote também a extensão (xmin…ymax) da layer de lotes: se ficar perto de E 500.000 e N 9.600.000, o DWG está em UTM 24S.

- [ ] **Step 9: ⛔ Gate — conferência do Abner**

Pare e mostre ao Abner o `dados/inventario-layers.md` e o rascunho do `layers.toml`, com três perguntas:
1. As layers escolhidas estão certas?
2. A organização é a esperada (um polígono fechado por lote, o número do lote como texto ou atributo dentro dele, a quadra como polígono com rótulo dentro)?
3. A extensão indica UTM 24S?

**Não siga para a Task 5 sem a resposta.** Se a organização for outra (o número do lote fora do polígono, a quadra só como texto solto, os lotes como linhas soltas em vez de polilinhas), atualize primeiro as Tasks 5 e 6 deste plano. O contrato `LoteBruto` da Task 5 não muda.

- [ ] **Step 10: Commit**

```bash
git add scripts/loteamento/converter_dwg.py scripts/loteamento/inventario.py scripts/loteamento/layers.toml tests/test_converter_dwg.py tests/test_inventario.py dados/inventario-layers.md dados/inventario-layers-masterplan.md
git commit -m "feat(dados): DWG para DXF via accoreconsole e inventário de layers"
```

---

### Task 5: Extração dos lotes do DXF

**Files:**
- Create: `scripts/loteamento/extrair.py`, `tests/conftest.py`, `tests/test_extrair.py`

**Interfaces:**
- Consumes: `geometria.*`, `ids.normalizar_quadra`, `ids.normalizar_lote`, `ids.id_lote`, `layers.toml` (Task 4)
- Produces:
  - `extrair.MapaLayers(lotes, rotulo_lote, quadras, rotulo_quadra, meio_fio)` (frozen) e `MapaLayers.carregar(caminho: Path) -> MapaLayers`
  - `extrair.LoteBruto(id: str, quadra: str, lote: str, handle: str, pontos: list[Ponto], lados_m: list[float], frente_m: float | None)` (frozen)
  - `extrair.ExtracaoErro(Exception)`, com `.erros: list[str]`
  - `extrair.textos_da_layer(msp, layer: str) -> list[tuple[Ponto, str]]`
  - `extrair.extrair_lotes(doc, mapa: MapaLayers) -> dict[str, LoteBruto]`
  - Fixtures de `tests/conftest.py`: `doc_sintetico`, `mapa_sintetico`, `tabela_sintetica`, `iptu_sintetico`, `AREA_H1`

**Estratégia** (a validada no gate):
- O lote é uma polilinha fechada na layer `lotes`.
- O número do lote é o único rótulo da layer `rotulo_lote` dentro do polígono (TEXT, MTEXT ou ATTRIB).
- A quadra é a polilinha fechada da layer `quadras` que contém o centroide do lote, e o rótulo dela é o único texto da layer `rotulo_quadra` dentro dela.
- A frente é o lado mais perto da layer `meio_fio`.
- Todo problema vira item de erro com o handle do CAD, e todos aparecem juntos.

- [ ] **Step 1: Criar as fixtures em `tests/conftest.py`**

```python
import math

import ezdxf
import pytest

from scripts.loteamento.extrair import MapaLayers
from scripts.loteamento.fontes import LinhaPreco

E0, N0 = 500_000.0, 9_600_000.0
BULGE_H1 = 0.2
_THETA = 4 * math.atan(BULGE_H1)
_R = 30 / (2 * math.sin(_THETA / 2))
AREA_H1 = 600 + _R * _R / 2 * (_THETA - math.sin(_THETA))


def _ret(x, y, w, h):
    return [(E0 + x, N0 + y), (E0 + x + w, N0 + y), (E0 + x + w, N0 + y + h), (E0 + x, N0 + y + h)]


@pytest.fixture
def mapa_sintetico():
    return MapaLayers(lotes="LOTES", rotulo_lote="NUM_LOTE", quadras="QUADRAS", rotulo_quadra="NUM_QUADRA", meio_fio="MEIO_FIO")


@pytest.fixture
def doc_sintetico():
    """Quadra 01 com dois lotes 10×20 e quadra H com um lote 30×20 de frente em arco; meio-fio ao sul."""
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_lwpolyline(_ret(-1, -1, 22, 22), close=True, dxfattribs={"layer": "QUADRAS"})
    msp.add_text("QUADRA 01", dxfattribs={"layer": "NUM_QUADRA", "insert": (E0 + 5, N0 + 15)})
    msp.add_lwpolyline(_ret(0, 0, 10, 20), close=True, dxfattribs={"layer": "LOTES"})
    msp.add_text("1", dxfattribs={"layer": "NUM_LOTE", "insert": (E0 + 5, N0 + 10)})
    msp.add_lwpolyline(_ret(10, 0, 10, 20), close=True, dxfattribs={"layer": "LOTES"})
    bloco = doc.blocks.new("NUMERO")
    bloco.add_attdef("N", (0, 0), dxfattribs={"layer": "NUM_LOTE"})
    ref = msp.add_blockref("NUMERO", (E0 + 15, N0 + 10), dxfattribs={"layer": "NUM_LOTE"})
    ref.add_auto_attribs({"N": "02"})
    for a in ref.attribs:  # garante a layer do ATTRIB, que é o que a extração lê
        a.dxf.layer = "NUM_LOTE"
    msp.add_lwpolyline(_ret(29, -6, 32, 27), close=True, dxfattribs={"layer": "QUADRAS"})
    msp.add_text("H", dxfattribs={"layer": "NUM_QUADRA", "insert": (E0 + 45, N0 + 18)})
    msp.add_lwpolyline(
        [(E0 + 30, N0, BULGE_H1), (E0 + 60, N0, 0), (E0 + 60, N0 + 20, 0), (E0 + 30, N0 + 20, 0)],
        format="xyb", close=True, dxfattribs={"layer": "LOTES"},
    )
    msp.add_text("LT 1", dxfattribs={"layer": "NUM_LOTE", "insert": (E0 + 45, N0 + 10)})
    msp.add_lwpolyline([(E0 - 5, N0 - 8), (E0 + 65, N0 - 8)], dxfattribs={"layer": "MEIO_FIO"})
    return doc


@pytest.fixture
def tabela_sintetica():
    return {
        "Q01L01": LinhaPreco(200.0, "A", 1380.0, 276000.0),
        "Q01L02": LinhaPreco(200.0, "A", 1380.0, 276000.0),
        "QHL01": LinhaPreco(round(AREA_H1, 2), "D", 990.0, round(AREA_H1 * 990, 2)),
    }


@pytest.fixture
def iptu_sintetico():
    return {"Q01L01": "138321-3", "Q01L02": "138339-6"}
```

O bulge `0.2` precisa curvar a aresta sul **para fora**, rumo ao meio-fio. Se a Task 3 tiver mostrado que o sinal é o contrário, use `-0.2` aqui também.

- [ ] **Step 2: Escrever o teste que falha**

`tests/test_extrair.py`:
```python
import pytest

from scripts.loteamento.extrair import ExtracaoErro, MapaLayers, extrair_lotes
from tests.conftest import AREA_H1, E0, N0
from scripts.loteamento.geometria import area


def test_extrai_tres_lotes_com_ids_canonicos(doc_sintetico, mapa_sintetico):
    lotes = extrair_lotes(doc_sintetico, mapa_sintetico)
    assert set(lotes) == {"Q01L01", "Q01L02", "QHL01"}
    l1 = lotes["Q01L01"]
    assert (l1.quadra, l1.lote) == ("01", "01")
    assert l1.lados_m == [10.0, 20.0, 10.0, 20.0]
    assert l1.frente_m == 10.0
    assert area(lotes["QHL01"].pontos) == pytest.approx(AREA_H1, rel=1e-3)
    assert lotes["QHL01"].frente_m > 30  # frente em arco é mais longa que a corda


def test_lote_sem_rotulo_e_erro_com_handle(doc_sintetico, mapa_sintetico):
    msp = doc_sintetico.modelspace()
    texto = next(e for e in msp.query('TEXT[layer=="NUM_LOTE"]') if e.dxf.text == "1")
    msp.delete_entity(texto)
    with pytest.raises(ExtracaoErro) as exc:
        extrair_lotes(doc_sintetico, mapa_sintetico)
    assert any("0 rótulos" in e and "lote" in e for e in exc.value.erros)


def test_lote_com_dois_rotulos_e_erro(doc_sintetico, mapa_sintetico):
    doc_sintetico.modelspace().add_text("9", dxfattribs={"layer": "NUM_LOTE", "insert": (E0 + 3, N0 + 3)})
    with pytest.raises(ExtracaoErro) as exc:
        extrair_lotes(doc_sintetico, mapa_sintetico)
    assert any("2 rótulos" in e for e in exc.value.erros)


def test_lote_fora_de_quadra_e_erro(doc_sintetico, mapa_sintetico):
    msp = doc_sintetico.modelspace()
    msp.add_lwpolyline([(E0 + 100, N0), (E0 + 110, N0), (E0 + 110, N0 + 10), (E0 + 100, N0 + 10)], close=True, dxfattribs={"layer": "LOTES"})
    msp.add_text("5", dxfattribs={"layer": "NUM_LOTE", "insert": (E0 + 105, N0 + 5)})
    with pytest.raises(ExtracaoErro) as exc:
        extrair_lotes(doc_sintetico, mapa_sintetico)
    assert any("0 quadras" in e for e in exc.value.erros)


def test_mapa_carrega_do_toml(tmp_path):
    p = tmp_path / "layers.toml"
    p.write_text('lotes="A"\nrotulo_lote="B"\nquadras="C"\nrotulo_quadra="D"\nmeio_fio="E"\n', encoding="utf-8")
    assert MapaLayers.carregar(p) == MapaLayers("A", "B", "C", "D", "E")
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `uv run pytest tests/test_extrair.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'scripts.loteamento.extrair'`

- [ ] **Step 4: Implementar `scripts/loteamento/extrair.py`**

```python
"""Lotes do DXF de venda: polígono, quadra, número, lados e frente."""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .geometria import Ponto, centroide, contem, indice_frente, poligono_fechado, pontos_de, segmentos
from .ids import id_lote, normalizar_lote, normalizar_quadra

_RE_LOTE = re.compile(r"^(?:LOTE|LT\.?|L)?\s*-?\s*(\d{1,3})$", re.IGNORECASE)
_RE_QUADRA = re.compile(r"^(?:QUADRA|QD\.?|Q)?\s*-?\s*(\d{1,3}|[A-Z])$", re.IGNORECASE)
_TIPOS_VIA = ("LWPOLYLINE", "POLYLINE", "LINE", "ARC")


@dataclass(frozen=True)
class MapaLayers:
    lotes: str
    rotulo_lote: str
    quadras: str
    rotulo_quadra: str
    meio_fio: str

    @classmethod
    def carregar(cls, caminho: Path) -> "MapaLayers":
        return cls(**tomllib.loads(caminho.read_text(encoding="utf-8")))


@dataclass(frozen=True)
class LoteBruto:
    id: str
    quadra: str
    lote: str
    handle: str
    pontos: list[Ponto]
    lados_m: list[float]
    frente_m: float | None


class ExtracaoErro(Exception):
    def __init__(self, erros: list[str]):
        super().__init__(f"{len(erros)} erro(s) na extração")
        self.erros = erros


def textos_da_layer(msp, layer: str) -> list[tuple[Ponto, str]]:
    saida = []
    for e in msp:
        t = e.dxftype()
        if t == "TEXT" and e.dxf.layer == layer:
            saida.append(((e.dxf.insert.x, e.dxf.insert.y), e.dxf.text.strip()))
        elif t == "MTEXT" and e.dxf.layer == layer:
            saida.append(((e.dxf.insert.x, e.dxf.insert.y), e.plain_text().strip()))
        elif t == "INSERT":
            for a in e.attribs:
                if a.dxf.layer == layer:
                    saida.append(((a.dxf.insert.x, a.dxf.insert.y), a.dxf.text.strip()))
    return saida


def _rotulos(msp, layer: str, regex: re.Pattern) -> list[tuple[Ponto, str]]:
    return [(p, m.group(1)) for p, t in textos_da_layer(msp, layer) if (m := regex.match(t))]


def extrair_lotes(doc, mapa: MapaLayers) -> dict[str, LoteBruto]:
    msp = doc.modelspace()
    erros: list[str] = []

    rotulos_quadra = _rotulos(msp, mapa.rotulo_quadra, _RE_QUADRA)
    quadras: list[tuple[list[Ponto], str]] = []
    for e in msp.query(f'LWPOLYLINE[layer=="{mapa.quadras}"]'):
        if not poligono_fechado(e):
            continue
        pts = pontos_de(e)
        dentro = [r for p, r in rotulos_quadra if contem(pts, p)]
        if len(dentro) != 1:
            erros.append(f"quadra handle {e.dxf.handle}: {len(dentro)} rótulos {dentro}")
            continue
        quadras.append((pts, dentro[0]))

    rotulos_lote = _rotulos(msp, mapa.rotulo_lote, _RE_LOTE)
    vias = [pontos_de(e) for e in msp if e.dxf.layer == mapa.meio_fio and e.dxftype() in _TIPOS_VIA]

    lotes: dict[str, LoteBruto] = {}
    for e in msp.query(f'LWPOLYLINE[layer=="{mapa.lotes}"]'):
        if not poligono_fechado(e):
            continue
        h = e.dxf.handle
        pts = pontos_de(e)
        dentro = [r for p, r in rotulos_lote if contem(pts, p)]
        if len(dentro) != 1:
            erros.append(f"lote handle {h}: {len(dentro)} rótulos {dentro}")
            continue
        c = centroide(pts)
        qs = [r for qpts, r in quadras if contem(qpts, c)]
        if len(qs) != 1:
            erros.append(f"lote handle {h} (nº {dentro[0]}): dentro de {len(qs)} quadras {qs}")
            continue
        q, l = normalizar_quadra(qs[0]), normalizar_lote(dentro[0])
        i = id_lote(q, l)
        if i in lotes:
            erros.append(f"{i} repetido (handles {lotes[i].handle} e {h})")
            continue
        segs = segmentos(e)
        frente = round(segs[indice_frente(segs, vias)][2], 2) if vias else None
        lotes[i] = LoteBruto(i, q, l, h, pts, [round(s[2], 2) for s in segs], frente)

    if erros:
        raise ExtracaoErro(erros)
    return lotes
```

- [ ] **Step 5: Rodar e ver passar**

Run: `uv run pytest tests/test_extrair.py -v`
Expected: 5 passed

- [ ] **Step 6: Rodar no DXF real, sem gravar nada**

Run:
```bash
uv run python -c "import ezdxf; from scripts.comum.ambiente import RAIZ; from scripts.loteamento.extrair import *; d=ezdxf.readfile(RAIZ/'cache/dxf/planta-venda.dxf'); m=MapaLayers.carregar(RAIZ/'scripts/loteamento/layers.toml'); \
exec('try:\n l=extrair_lotes(d,m); print(len(l), sorted(l)[:5])\nexcept ExtracaoErro as x: print(len(x.erros)); print(*x.erros[:40], sep=chr(10))')"
```
Expected: `347` e ids. Se houver erros, leia-os. Caso típico: o rótulo fica fora do polígono em lotes estreitos. Corrija a **estratégia** (por exemplo, rótulo mais próximo do centroide quando nenhum cai dentro), com um teste novo em `tests/test_extrair.py` que reproduza o caso antes da correção. Nunca edite o DXF.

- [ ] **Step 7: Commit**

```bash
git add scripts/loteamento/extrair.py tests/conftest.py tests/test_extrair.py
git commit -m "feat(dados): extração dos lotes do DXF de venda"
```

---

### Task 6: Georreferência e origem local

**Files:**
- Create: `scripts/loteamento/georref.py`, `tests/test_georref.py`

**Interfaces:**
- Consumes: `geometria.extensao`
- Produces: `CRS = "EPSG:31984"`, `GeorrefErro(Exception)`, `parece_utm_24s(ext) -> bool`, `origem(ext) -> tuple[float, float]` (centro arredondado a 100 m), `para_local(pts, e0, n0) -> list[list[float]]` (arredondado a 0,01 m), `georref_json(e0, n0) -> dict`

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_georref.py`:
```python
import pytest

from scripts.loteamento.georref import CRS, georref_json, origem, para_local, parece_utm_24s


def test_reconhece_utm_24s_de_caucaia():
    assert parece_utm_24s((517_000.0, 9_597_000.0, 519_500.0, 9_599_000.0))


@pytest.mark.parametrize("ext", [(0, 0, 500, 300), (-38.8, -3.7, -38.7, -3.6), (517_000, 7_400_000, 518_000, 7_401_000)])
def test_rejeita_coordenadas_locais_geograficas_ou_de_outro_lugar(ext):
    assert not parece_utm_24s(ext)


def test_origem_e_o_centro_arredondado_a_100m():
    assert origem((517_010.0, 9_597_020.0, 519_480.0, 9_598_990.0)) == (518_200.0, 9_598_000.0)


def test_para_local():
    assert para_local([(518_210.123, 9_598_005.456)], 518_200.0, 9_598_000.0) == [[10.12, 5.46]]


def test_georref_json():
    assert georref_json(1.0, 2.0) == {"crs": CRS, "origem": {"E": 1.0, "N": 2.0}}
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_georref.py -v`
Expected: FAIL com `ModuleNotFoundError`

- [ ] **Step 3: Implementar `scripts/loteamento/georref.py`**

```python
"""SIRGAS 2000 / UTM 24S e a origem local da cena (x = leste, y = norte, em metros)."""

CRS = "EPSG:31984"


class GeorrefErro(Exception):
    pass


def parece_utm_24s(ext: tuple[float, float, float, float]) -> bool:
    xmin, ymin, xmax, ymax = ext
    return 166_000 <= xmin <= xmax <= 834_000 and 9_400_000 <= ymin <= ymax <= 9_800_000


def origem(ext: tuple[float, float, float, float]) -> tuple[float, float]:
    xmin, ymin, xmax, ymax = ext
    return (round((xmin + xmax) / 2, -2), round((ymin + ymax) / 2, -2))


def para_local(pts, e0: float, n0: float) -> list[list[float]]:
    return [[round(x - e0, 2), round(y - n0, 2)] for x, y in pts]


def georref_json(e0: float, n0: float) -> dict:
    return {"crs": CRS, "origem": {"E": e0, "N": n0}}
```

A faixa de N entre 9.400.000 e 9.800.000 cobre o litoral do Ceará (latitude de cerca de 2° a 6° S) e recusa coordenadas do Sudeste.

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_georref.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/loteamento/georref.py tests/test_georref.py
git commit -m "feat(dados): checagem de UTM 24S e origem local da cena"
```

Se o gate da Task 4 tiver mostrado que o DWG **não** está em UTM 24S, pare aqui. O registro pelo KMZ do estande e por pontos notáveis vira uma task nova neste plano, escrita com o Abner, e a Task 8 só roda depois dela.

---

### Task 7: Conferência e relatório

**Files:**
- Create: `scripts/loteamento/conferir.py`, `tests/test_conferir.py`

**Interfaces:**
- Consumes: `LoteBruto` (Task 5), `LinhaPreco` (Task 2), `geometria.area`
- Produces: `Relatorio(erros: list[str], avisos: list[str], contagens: dict[str, int])`; `conferir(lotes, tabela, iptu, mostrar_precos: bool, tolerancia: float) -> Relatorio`; `escrever_relatorio(rel: Relatorio, destino: Path) -> None`

| Caso (spec §6) | Efeito |
|---|---|
| Lote no desenho e não na tabela, ou o contrário | erro |
| \|área do desenho − área da tabela\| / área da tabela > tolerância | erro |
| Lote sem inscrição de IPTU | aviso |
| Inscrição de IPTU de um lote fora do desenho | aviso |
| `mostrar_precos` e lote sem preço total > 0 | erro |

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_conferir.py`:
```python
from dataclasses import replace

from scripts.loteamento.conferir import conferir, escrever_relatorio
from scripts.loteamento.extrair import extrair_lotes
from scripts.loteamento.fontes import LinhaPreco


def _lotes(doc, mapa):
    return extrair_lotes(doc, mapa)


def test_tudo_confere_com_aviso_de_iptu(doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    rel = conferir(_lotes(doc_sintetico, mapa_sintetico), tabela_sintetica, iptu_sintetico, False, 0.005)
    assert rel.erros == []
    assert rel.avisos == ["QHL01: sem inscrição de IPTU"]
    assert rel.contagens == {"desenho": 3, "tabela": 3, "iptu": 2}


def test_lote_faltando_dos_dois_lados(doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    tabela = dict(tabela_sintetica)
    del tabela["Q01L02"]
    tabela["Q09L09"] = LinhaPreco(100.0, "A", 1.0, 100.0)
    rel = conferir(_lotes(doc_sintetico, mapa_sintetico), tabela, iptu_sintetico, False, 0.005)
    assert "Q01L02: no desenho e não na tabela" in rel.erros
    assert "Q09L09: na tabela e não no desenho" in rel.erros


def test_area_fora_da_tolerancia(doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    tabela = dict(tabela_sintetica, Q01L01=replace(tabela_sintetica["Q01L01"], area_m2=202.0))
    rel = conferir(_lotes(doc_sintetico, mapa_sintetico), tabela, iptu_sintetico, False, 0.005)
    assert rel.erros == ["Q01L01: área do desenho 200.00 m² × tabela 202.00 m² (-0.99%)"]


def test_area_dentro_da_tolerancia_passa(doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    tabela = dict(tabela_sintetica, Q01L01=replace(tabela_sintetica["Q01L01"], area_m2=200.9))
    assert conferir(_lotes(doc_sintetico, mapa_sintetico), tabela, iptu_sintetico, False, 0.005).erros == []


def test_preco_obrigatorio_so_com_precos_ligados(doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    tabela = dict(tabela_sintetica, Q01L01=replace(tabela_sintetica["Q01L01"], preco_total=0.0))
    lotes = _lotes(doc_sintetico, mapa_sintetico)
    assert conferir(lotes, tabela, iptu_sintetico, False, 0.005).erros == []
    assert conferir(lotes, tabela, iptu_sintetico, True, 0.005).erros == ["Q01L01: sem preço na tabela"]


def test_relatorio_markdown(tmp_path, doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    rel = conferir(_lotes(doc_sintetico, mapa_sintetico), tabela_sintetica, iptu_sintetico, False, 0.005)
    destino = tmp_path / "r.md"
    escrever_relatorio(rel, destino)
    texto = destino.read_text(encoding="utf-8")
    assert "| desenho | 3 |" in texto
    assert "## Erros (0)" in texto
    assert "- QHL01: sem inscrição de IPTU" in texto
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_conferir.py -v`
Expected: FAIL com `ModuleNotFoundError`

- [ ] **Step 3: Implementar `scripts/loteamento/conferir.py`**

```python
"""Conferência desenho × tabela × IPTU (spec §6). Erro bloqueia o lotes.json; aviso só informa."""

from dataclasses import dataclass, field
from pathlib import Path

from .extrair import LoteBruto
from .fontes import LinhaPreco
from .geometria import area


@dataclass
class Relatorio:
    erros: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    contagens: dict[str, int] = field(default_factory=dict)


def conferir(
    lotes: dict[str, LoteBruto],
    tabela: dict[str, LinhaPreco],
    iptu: dict[str, str],
    mostrar_precos: bool,
    tolerancia: float,
) -> Relatorio:
    rel = Relatorio(contagens={"desenho": len(lotes), "tabela": len(tabela), "iptu": len(iptu)})
    desenho, cadastro = set(lotes), set(tabela)
    rel.erros += [f"{i}: no desenho e não na tabela" for i in sorted(desenho - cadastro)]
    rel.erros += [f"{i}: na tabela e não no desenho" for i in sorted(cadastro - desenho)]
    for i in sorted(desenho & cadastro):
        a, t = area(lotes[i].pontos), tabela[i].area_m2
        if abs(a - t) / t > tolerancia:
            rel.erros.append(f"{i}: área do desenho {a:.2f} m² × tabela {t:.2f} m² ({(a - t) / t:+.2%})")
        if mostrar_precos and tabela[i].preco_total <= 0:
            rel.erros.append(f"{i}: sem preço na tabela")
    rel.avisos += [f"{i}: sem inscrição de IPTU" for i in sorted(desenho - set(iptu))]
    rel.avisos += [f"{i}: inscrição de IPTU de lote fora do desenho" for i in sorted(set(iptu) - desenho)]
    return rel


def escrever_relatorio(rel: Relatorio, destino: Path) -> None:
    linhas = [
        "# Relatório de conferência — lotes da Fase 1",
        "",
        "Gerado por `scripts/loteamento/gerar_dados.py`. Erro bloqueia o `lotes.json`; aviso só informa.",
        "",
        "| Fonte | Lotes |",
        "|---|---:|",
        *[f"| {k} | {v} |" for k, v in rel.contagens.items()],
        "",
        f"## Erros ({len(rel.erros)})",
        "",
        *[f"- {e}" for e in rel.erros],
        "",
        f"## Avisos ({len(rel.avisos)})",
        "",
        *[f"- {a}" for a in rel.avisos],
    ]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
```

O teste de duas casas (`-0.99%`): (200 − 202) / 202 = −0,990%. O formato `+.2%` produz `-0.99%`.

- [ ] **Step 4: Rodar e ver passar**

Run: `uv run pytest tests/test_conferir.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/loteamento/conferir.py tests/test_conferir.py
git commit -m "feat(dados): conferência desenho, tabela e IPTU com relatório"
```

---

### Task 8: `config.json`, `lotes.json` e o comando `gerar_dados`

**Files:**
- Create: `dados/config.json`, `scripts/loteamento/saida.py`, `scripts/loteamento/gerar_dados.py`, `tests/test_saida.py`, `tests/test_gerar_dados.py`
- Gera (commitado): `dados/lotes.json`, `dados/georref.json`, `dados/relatorio-conferencia.md`

**Interfaces:**
- Consumes: tudo das Tasks 2–7
- Produces:
  - `saida.Config(mostrar_precos: bool, tabela_arquivo: str, tabela_nome: str, tabela_referencia: str, tolerancia_area: float)`, `saida.carregar_config(caminho: Path) -> Config`
  - `saida.montar_lotes_json(lotes, tabela, iptu, config, e0, n0) -> dict`
  - `gerar_dados.gerar(doc, mapa, tabela, iptu, config, saida_dir: Path) -> Relatorio`, `gerar_dados.main() -> int` (0 ok, 1 erro de conferência, 2 falta DXF)
- **Contrato `lotes.json`** (consumido pelos Planos 3 e 5):

```json
{
  "versao": 1,
  "crs": "EPSG:31984",
  "origem": {"E": 518200.0, "N": 9598000.0},
  "precos": {"tabela": "SET26", "referencia": "2026-09"},
  "lotes": [
    {
      "id": "Q07L04", "quadra": "07", "lote": "04", "tipo": "residencial",
      "area_m2": 402.29, "lados_m": [12.0, 33.52, 12.0, 33.52], "frente_m": 12.0,
      "poligono": [[-120.5, 33.2], [-108.5, 33.2], [-108.5, 66.72], [-120.5, 66.72]],
      "inscricao_iptu": "138341-8",
      "preco": {"total": 555160.2, "m2": 1380.0, "classificacao": "A"}
    }
  ]
}
```
  - `area_m2` é a área da tabela, o número comercial (a conferência garante que difere do desenho em até 0,5%).
  - `poligono` usa coordenadas locais em metros (x = leste, y = norte).
  - `inscricao_iptu` é omitida quando não existe.
  - Com `mostrarPrecos: false`, a chave `"precos"` vale `null` e **nenhum** lote tem `"preco"`.
  - Os lotes saem ordenados por id.

- [ ] **Step 1: Criar `dados/config.json`**

```json
{
  "mostrarPrecos": false,
  "tabelaPrecos": {
    "arquivo": "1-ADMINISTRATIVO/FINANCEIRO/Tab Lancamento SET26 R01.xls",
    "nome": "SET26",
    "referencia": "2026-09"
  },
  "toleranciaArea": 0.005
}
```

- [ ] **Step 2: Escrever os testes que falham**

`tests/test_saida.py`:
```python
import json

from scripts.loteamento.extrair import extrair_lotes
from scripts.loteamento.saida import Config, carregar_config, montar_lotes_json
from tests.conftest import E0, N0

CFG = Config(mostrar_precos=False, tabela_arquivo="t.xls", tabela_nome="SET26", tabela_referencia="2026-09", tolerancia_area=0.005)


def test_carregar_config(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"mostrarPrecos": True, "tabelaPrecos": {"arquivo": "a", "nome": "n", "referencia": "r"}, "toleranciaArea": 0.01}), encoding="utf-8")
    assert carregar_config(p) == Config(True, "a", "n", "r", 0.01)


def test_lotes_json_sem_precos_nao_vaza_preco(doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    j = montar_lotes_json(extrair_lotes(doc_sintetico, mapa_sintetico), tabela_sintetica, iptu_sintetico, CFG, E0, N0)
    texto = json.dumps(j)
    assert j["precos"] is None
    assert "preco" not in texto.replace('"precos": null', "")
    assert "276000" not in texto and "1380" not in texto


def test_lotes_json_com_precos(doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    cfg = Config(True, "t.xls", "SET26", "2026-09", 0.005)
    j = montar_lotes_json(extrair_lotes(doc_sintetico, mapa_sintetico), tabela_sintetica, iptu_sintetico, cfg, E0, N0)
    assert j["precos"] == {"tabela": "SET26", "referencia": "2026-09"}
    l1 = j["lotes"][0]
    assert l1["id"] == "Q01L01"
    assert l1["preco"] == {"total": 276000.0, "m2": 1380.0, "classificacao": "A"}


def test_formato_do_lote(doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    j = montar_lotes_json(extrair_lotes(doc_sintetico, mapa_sintetico), tabela_sintetica, iptu_sintetico, CFG, E0, N0)
    assert [l["id"] for l in j["lotes"]] == ["Q01L01", "Q01L02", "QHL01"]
    l1, h1 = j["lotes"][0], j["lotes"][2]
    assert l1 == {
        "id": "Q01L01", "quadra": "01", "lote": "01", "tipo": "residencial", "area_m2": 200.0,
        "lados_m": [10.0, 20.0, 10.0, 20.0], "frente_m": 10.0,
        "poligono": [[0.0, 0.0], [10.0, 0.0], [10.0, 20.0], [0.0, 20.0]], "inscricao_iptu": "138321-3",
    }
    assert h1["tipo"] == "uso_misto" and "inscricao_iptu" not in h1
```

`tests/test_gerar_dados.py`:
```python
import json

from scripts.loteamento.gerar_dados import gerar
from scripts.loteamento.saida import Config

CFG = Config(False, "t.xls", "SET26", "2026-09", 0.005)


def test_gera_os_tres_arquivos(tmp_path, doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    rel = gerar(doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico, CFG, tmp_path)
    assert rel.erros == []
    assert len(json.loads((tmp_path / "lotes.json").read_text(encoding="utf-8"))["lotes"]) == 3
    assert json.loads((tmp_path / "georref.json").read_text(encoding="utf-8"))["crs"] == "EPSG:31984"
    assert (tmp_path / "relatorio-conferencia.md").exists()


def test_erro_de_conferencia_nao_grava_lotes_json(tmp_path, doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    tabela = dict(tabela_sintetica)
    del tabela["QHL01"]
    rel = gerar(doc_sintetico, mapa_sintetico, tabela, iptu_sintetico, CFG, tmp_path)
    assert rel.erros
    assert not (tmp_path / "lotes.json").exists()
    assert "QHL01: no desenho e não na tabela" in (tmp_path / "relatorio-conferencia.md").read_text(encoding="utf-8")


def test_erro_de_extracao_vai_para_o_relatorio(tmp_path, doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    msp = doc_sintetico.modelspace()
    for t in list(msp.query('TEXT[layer=="NUM_LOTE"]')):
        msp.delete_entity(t)
    rel = gerar(doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico, CFG, tmp_path)
    assert any("0 rótulos" in e for e in rel.erros)
    assert not (tmp_path / "lotes.json").exists()


def test_lotes_json_antigo_e_apagado_quando_ha_erro(tmp_path, doc_sintetico, mapa_sintetico, tabela_sintetica, iptu_sintetico):
    (tmp_path / "lotes.json").write_text("{}", encoding="utf-8")
    tabela = dict(tabela_sintetica)
    del tabela["QHL01"]
    gerar(doc_sintetico, mapa_sintetico, tabela, iptu_sintetico, CFG, tmp_path)
    assert not (tmp_path / "lotes.json").exists()
```

O último teste garante que um `lotes.json` velho não sobreviva a uma rodada com erro e pareça atual.

- [ ] **Step 3: Rodar e ver falhar**

Run: `uv run pytest tests/test_saida.py tests/test_gerar_dados.py -v`
Expected: FAIL com `ModuleNotFoundError`

- [ ] **Step 4: Implementar `scripts/loteamento/saida.py`**

```python
"""config.json → Config, e a montagem do lotes.json (contrato do Plano 1, Task 8)."""

import json
from dataclasses import dataclass
from pathlib import Path

from .extrair import LoteBruto
from .fontes import LinhaPreco
from .georref import CRS, para_local
from .ids import tipo_por_quadra


@dataclass(frozen=True)
class Config:
    mostrar_precos: bool
    tabela_arquivo: str
    tabela_nome: str
    tabela_referencia: str
    tolerancia_area: float


def carregar_config(caminho: Path) -> Config:
    c = json.loads(caminho.read_text(encoding="utf-8"))
    t = c["tabelaPrecos"]
    return Config(bool(c["mostrarPrecos"]), t["arquivo"], t["nome"], t["referencia"], float(c["toleranciaArea"]))


def montar_lotes_json(
    lotes: dict[str, LoteBruto],
    tabela: dict[str, LinhaPreco],
    iptu: dict[str, str],
    config: Config,
    e0: float,
    n0: float,
) -> dict:
    saida = []
    for i in sorted(lotes):
        l, t = lotes[i], tabela[i]
        item = {
            "id": i,
            "quadra": l.quadra,
            "lote": l.lote,
            "tipo": tipo_por_quadra(l.quadra),
            "area_m2": round(t.area_m2, 2),
            "lados_m": l.lados_m,
            "frente_m": l.frente_m,
            "poligono": para_local(l.pontos, e0, n0),
        }
        if i in iptu:
            item["inscricao_iptu"] = iptu[i]
        if config.mostrar_precos:
            item["preco"] = {"total": round(t.preco_total, 2), "m2": round(t.preco_m2, 2), "classificacao": t.classificacao}
        saida.append(item)
    return {
        "versao": 1,
        "crs": CRS,
        "origem": {"E": e0, "N": n0},
        "precos": {"tabela": config.tabela_nome, "referencia": config.tabela_referencia} if config.mostrar_precos else None,
        "lotes": saida,
    }
```

O polígono de `lotes.json` usa os pontos achatados (arcos viram trechos de 5 cm no máximo), e é isso que o front e o Blender desenham. Os `lados_m` usam o comprimento real do arco.

- [ ] **Step 5: Implementar `scripts/loteamento/gerar_dados.py`**

```python
"""Gera dados/lotes.json, georref.json e relatorio-conferencia.md. Uso: uv run python -m scripts.loteamento.gerar_dados"""

import json
import sys
from pathlib import Path

import ezdxf

from scripts.comum.ambiente import RAIZ, terreno_dir

from .conferir import Relatorio, conferir, escrever_relatorio
from .extrair import ExtracaoErro, MapaLayers, extrair_lotes
from .fontes import ler_iptu, ler_tabela_set26
from .geometria import extensao
from .georref import georref_json, origem, parece_utm_24s
from .saida import Config, carregar_config, montar_lotes_json

IPTU_CSV = "4-PREFEITURA/IPTU_2025/00-INDICE IPTU 2025 - LOTES CANCUN.csv"


def _gravar_json(destino: Path, dados: dict) -> None:
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def gerar(doc, mapa: MapaLayers, tabela, iptu, config: Config, saida_dir: Path) -> Relatorio:
    saida_dir.mkdir(parents=True, exist_ok=True)
    (saida_dir / "lotes.json").unlink(missing_ok=True)
    try:
        lotes = extrair_lotes(doc, mapa)
    except ExtracaoErro as erro:
        rel = Relatorio(erros=erro.erros)
        escrever_relatorio(rel, saida_dir / "relatorio-conferencia.md")
        return rel

    ext = extensao([p for l in lotes.values() for p in l.pontos])
    rel = conferir(lotes, tabela, iptu, config.mostrar_precos, config.tolerancia_area)
    if not parece_utm_24s(ext):
        rel.erros.insert(0, f"desenho fora de UTM 24S: extensão {ext}")
    escrever_relatorio(rel, saida_dir / "relatorio-conferencia.md")
    if rel.erros:
        return rel

    e0, n0 = origem(ext)
    _gravar_json(saida_dir / "georref.json", georref_json(e0, n0))
    _gravar_json(saida_dir / "lotes.json", montar_lotes_json(lotes, tabela, iptu, config, e0, n0))
    return rel


def main() -> int:
    dxf = RAIZ / "cache" / "dxf" / "planta-venda.dxf"
    if not dxf.exists():
        print("Falta o DXF. Rode antes: uv run python -m scripts.loteamento.converter_dwg")
        return 2
    terreno = terreno_dir()
    config = carregar_config(RAIZ / "dados" / "config.json")
    rel = gerar(
        ezdxf.readfile(dxf),
        MapaLayers.carregar(RAIZ / "scripts" / "loteamento" / "layers.toml"),
        ler_tabela_set26(terreno / config.tabela_arquivo),
        ler_iptu(terreno / IPTU_CSV),
        config,
        RAIZ / "dados",
    )
    print(f"{rel.contagens} · {len(rel.erros)} erro(s) · {len(rel.avisos)} aviso(s) → dados/relatorio-conferencia.md")
    return 1 if rel.erros else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Rodar e ver passar**

Run: `uv run pytest -v`
Expected: a suíte inteira passa.

- [ ] **Step 7: Rodar com os dados reais**

Run: `uv run python -m scripts.loteamento.gerar_dados`
Expected:
- **Saída 0:** `{'desenho': 347, 'tabela': 347, 'iptu': 325} · 0 erro(s) · N aviso(s)`, com `dados/lotes.json` e `dados/georref.json` criados.
- **Saída 1:** leia `dados/relatorio-conferencia.md`.
  - Divergência de dados (área, lote faltando), como a do 347 / 344 / 325 já esperada: **não corrija à mão nem afrouxe a tolerância**. Leve o relatório ao Abner, porque a decisão sobre o dado é dele.
  - Erro de estratégia de extração: volte à Task 5, Step 6.

- [ ] **Step 8: Conferir o contrato à mão**

Run: `uv run python -c "import json; j=json.load(open('dados/lotes.json',encoding='utf-8')); print(j['precos'], len(j['lotes']), j['lotes'][0]); assert all('preco' not in l for l in j['lotes'])"`
Expected: `None 347 {...}`, sem nenhum preço.

- [ ] **Step 9: Commit**

```bash
git add dados/config.json scripts/loteamento/saida.py scripts/loteamento/gerar_dados.py tests/test_saida.py tests/test_gerar_dados.py dados/lotes.json dados/georref.json dados/relatorio-conferencia.md
git commit -m "feat(dados): lotes.json, georref.json e relatório de conferência da Fase 1"
```

Se a rodada real terminou com erro, o commit leva só o código e o `relatorio-conferencia.md` (o `lotes.json` não existe). O plano termina com o relatório entregue ao Abner.

---

## Fim do Plano 1

**Entregue:** `dados/lotes.json` (347 lotes, sem preços), `dados/georref.json`, `dados/relatorio-conferencia.md` e `dados/inventario-layers*.md`, todos reproduzíveis com:

```bash
uv run python -m scripts.loteamento.converter_dwg
uv run python -m scripts.loteamento.gerar_dados
```

**Próximo:** escrever o Plano 3 (modelagem no Blender), que consome `lotes.json`, `georref.json` e `layers.toml`. O Plano 2 (marca) pode correr em paralelo desde o início.
