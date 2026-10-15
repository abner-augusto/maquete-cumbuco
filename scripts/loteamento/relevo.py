"""Relevo da Fase 1: curvas de nível do masterplan cotadas pelos rótulos, em grade regular.

Uso: uv run python -m scripts.loteamento.relevo
"""

import json
import math
import sys
from collections import Counter
from dataclasses import dataclass, field

import ezdxf
import numpy as np
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator

from scripts.comum.ambiente import RAIZ

from .geometria import area, contem

Ponto = tuple[float, float]
DXF = RAIZ / "cache" / "dxf" / "masterplan-r05.dxf"
DESTINO = RAIZ / "cache" / "cena" / "relevo.json"
MARGEM = 450.0  # m além dos lotes: o levantamento vai até alcance + transição do terreno.py
PASSO_GRADE = 5.0


@dataclass
class Curva:
    pontos: list[Ponto]
    z: float | None = None
    fechada: bool = False  # topo ou fundo de duna: cotada pelo anel que a contém (cotar_aneis)


def _dist_polilinha(p: Ponto, pts: list[Ponto]) -> float:
    px, py = p
    melhor = math.inf
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        dx, dy = bx - ax, by - ay
        t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        melhor = min(melhor, math.hypot(px - (ax + t * dx), py - (ay + t * dy)))
    return melhor


def _pontas(c: Curva) -> tuple[Ponto, Ponto]:
    return c.pontos[0], c.pontos[-1]


def cotar_mestras(
    mestras: list[Curva], rotulos: list[tuple[Ponto, float]], raio: float = 25.0,
    raio_curto: float = 6.0, emenda: float = 6.0,
) -> int:
    """Cota as mestras pelos rótulos. No desenho a mestra é cortada no rótulo, então o rótulo cota
    todo pedaço a até `raio_curto` (além do mais próximo, até `raio`), e o pedaço sem rótulo herda
    a cota do pedaço cotado cuja ponta está a até `emenda`."""
    votos: list[Counter] = [Counter() for _ in mestras]
    for p, z in rotulos:
        dists = [(_dist_polilinha(p, c.pontos), i) for i, c in enumerate(mestras)]
        d, i = min(dists)
        if d <= raio:
            votos[i][z] += 1
        for dj, j in dists:
            if j != i and dj <= raio_curto:
                votos[j][z] += 1
    for c, v in zip(mestras, votos):
        c.z = v.most_common(1)[0][0] if v else None
    mudou = True
    while mudou:
        mudou = False
        for c in (c for c in mestras if c.z is None and not c.fechada):
            vizinha = next(
                (m for m in mestras if m.z is not None and not m.fechada
                 and min(math.dist(a, b) for a in _pontas(c) for b in _pontas(m)) <= emenda),
                None,
            )
            if vizinha:
                c.z, mudou = vizinha.z, True
    return sum(1 for c in mestras if c.z is None)


def completar_mestras(mestras: list[Curva], cotadas: list[Curva], intervalo: float = 5.0) -> None:
    """Mestra que nem rótulo nem emenda cotaram (topo de duna fechado): múltiplo de `intervalo`
    mais próximo da cota da curva cotada mais perto."""
    for m in (m for m in mestras if m.z is None and not m.fechada):
        p = m.pontos[len(m.pontos) // 2]
        _, z = min(((_dist_polilinha(p, c.pontos), c.z) for c in cotadas if c is not m), default=(0, None))
        if z is not None:
            m.z = float(round(z / intervalo) * intervalo)


def _entre_mestras(p: Ponto, cotadas: list[Curva]) -> tuple[float, float, float, float] | None:
    """Mestra mais perto de `p` e a mais perto de cota diferente: (d1, z1, d2, z2)."""
    d = _dist_curvas([p], cotadas)
    ordem = np.argsort(d)
    z1 = cotadas[ordem[0]].z
    j = next((j for j in ordem if cotadas[j].z != z1), None)
    return None if j is None else (float(d[ordem[0]]), z1, float(d[j]), cotadas[j].z)


def cotar_intermediarias(inters: list[Curva], mestras: list[Curva], passo: float = 1.0, amostras: int = 40) -> None:
    """Curva aberta: interpolada entre as duas mestras que a cercam, no trecho em que elas estão
    mais perto (curva de km sai das mestras carregadas, e o meio dela pode estar longe de tudo)."""
    cotadas = [m for m in mestras if m.z is not None and len(m.pontos) > 1]
    for c in (c for c in inters if not c.fechada):
        if not cotadas:
            continue
        cercas = [e for p in c.pontos[:: max(1, len(c.pontos) // amostras)] if (e := _entre_mestras(p, cotadas))]
        if not cercas:
            continue
        d1, z1, d2, z2 = min(cercas, key=lambda e: e[0] + e[2])
        z = z1 + (z2 - z1) * d1 / (d1 + d2)
        z = round(z / passo) * passo
        sinal = 1 if z2 > z1 else -1
        if (z - z1) * sinal < passo:
            z = z1 + sinal * passo
        if (z2 - z) * sinal < passo:
            z = z2 - sinal * passo
        c.z = float(z)


def _dist_curvas(pts: list[Ponto], curvas: list[Curva]) -> np.ndarray:
    """Menor distância de qualquer ponto de `pts` a cada curva (vetorizado)."""
    a = np.array([p for c in curvas for p in c.pontos[:-1]], dtype=float)
    b = np.array([p for c in curvas for p in c.pontos[1:]], dtype=float)
    inicio = np.cumsum([0] + [len(c.pontos) - 1 for c in curvas[:-1]])
    ab = b - a
    l2 = np.maximum((ab * ab).sum(axis=1), 1e-12)
    melhor = np.full(len(a), np.inf)
    for p in pts:
        t = np.clip(((np.asarray(p) - a) * ab).sum(axis=1) / l2, 0.0, 1.0)
        melhor = np.minimum(melhor, np.hypot(*(a + t[:, None] * ab - p).T))
    return np.minimum.reduceat(melhor, inicio)


def cotar_aneis(mestras: list[Curva], inters: list[Curva], intervalo: float = 5.0, passo: float = 1.0) -> None:
    """Curvas fechadas (topos e fundos de duna), de fora para dentro: um passo além do anel que as
    contém, no sentido em que o relevo vinha de fora (morro continua subindo, cova continua descendo).
    Anel solto, sem anel em volta, toma por pai a curva cotada mais perto do lado de fora; se ela e a
    seguinte deixam um vão (mestras sem intermediária entre elas), o anel fica no vão. Curva já cotada
    dentro do anel manda no sentido: a cadeia caminha até ela."""
    todas = [c for c in mestras + inters if len(c.pontos) > 1]
    eh_mestra = {id(m) for m in mestras}
    aneis = sorted((c for c in todas if c.fechada), key=lambda c: area(c.pontos), reverse=True)
    caixa = {id(c): (min(x for x, _ in c.pontos), min(y for _, y in c.pontos),
                     max(x for x, _ in c.pontos), max(y for _, y in c.pontos)) for c in aneis}

    def dentro(anel: Curva, p: Ponto) -> bool:
        x0, y0, x1, y1 = caixa[id(anel)]
        return x0 <= p[0] <= x1 and y0 <= p[1] <= y1 and contem(anel.pontos, p)

    pai: dict[int, Curva | None] = {}
    for i, c in enumerate(aneis):
        de_fora = [a for a in aneis[:i] if dentro(a, c.pontos[0])]
        pai[id(c)] = de_fora[-1] if de_fora else None

    def vizinha(anel: Curva, menos: float | None, de_dentro: bool = False) -> float | None:
        lado = [q for q in todas if q is not anel and q.z is not None and q.z != menos
                and dentro(anel, q.pontos[0]) == de_dentro]
        if not lado:
            return None
        amostra = anel.pontos[:: max(1, len(anel.pontos) // 12)]
        return lado[int(np.argmin(_dist_curvas(amostra, lado)))].z

    def vizinha_de_fora(anel: Curva, menos: float | None) -> float | None:
        return vizinha(anel, menos)

    def lado_de_fora(anel: Curva) -> float | None:
        p = pai[id(anel)]
        if p is not None and p.z is not None and p.z != anel.z:
            return p.z
        return vizinha_de_fora(anel, anel.z)

    for c in aneis:
        if c.z is not None:
            continue
        p = pai[id(c)]
        if p is not None:
            if p.z is None:
                continue
            base, fora = p.z, lado_de_fora(p)
        else:
            base = vizinha_de_fora(c, None)
            if base is None:
                continue
            fora = vizinha_de_fora(c, base)
            if fora is not None and abs(fora - base) > passo:  # no vão entre duas curvas: fica entre elas
                fora = 2 * base - fora
        sentido = -1.0 if fora is not None and fora > base else 1.0
        alvo = vizinha(c, base, de_dentro=True)  # curva já cotada lá dentro (topo cortado no rótulo, fundo)
        if alvo is not None:
            sentido = 1.0 if alvo > base else -1.0
        if id(c) in eh_mestra:
            z = round((base + sentido * passo) / intervalo) * intervalo
            c.z = float(z if z != base else base + sentido * intervalo)
        else:
            z = base + sentido * passo
            if z % intervalo == 0:  # a mestra existiria aqui: sem nada lá dentro, é o outro sentido;
                z = base + 2 * sentido * passo if alvo is not None else base - sentido * passo  # com, faltou desenhá-la
            c.z = float(z)


@dataclass
class Grade:
    x0: float
    y0: float
    passo: float
    nx: int
    ny: int
    z: list[list[float]] = field(repr=False)  # z[j][i], j ao longo de y

    def cota(self, x: float, y: float) -> float:
        fx = min(max((x - self.x0) / self.passo, 0.0), self.nx - 1.0)
        fy = min(max((y - self.y0) / self.passo, 0.0), self.ny - 1.0)
        i, j = min(int(fx), self.nx - 2), min(int(fy), self.ny - 2)
        tx, ty = fx - i, fy - j
        z = self.z
        return (z[j][i] * (1 - tx) + z[j][i + 1] * tx) * (1 - ty) + (z[j + 1][i] * (1 - tx) + z[j + 1][i + 1] * tx) * ty

    def cota_malha(self, x: float, y: float) -> float:
        """Cota na superfície que a malha desenha: cada célula em dois triângulos pela diagonal de
        (i, j) a (i+1, j+1) (faces [a, a+1, a+nx+1] e [a, a+nx+1, a+nx]). O bilinear de `cota` difere
        disso em até |z00 − z10 + z11 − z01|/4 dentro da célula."""
        fx = min(max((x - self.x0) / self.passo, 0.0), self.nx - 1.0)
        fy = min(max((y - self.y0) / self.passo, 0.0), self.ny - 1.0)
        i, j = min(int(fx), self.nx - 2), min(int(fy), self.ny - 2)
        tx, ty = fx - i, fy - j
        z = self.z
        z00, z10, z01, z11 = z[j][i], z[j][i + 1], z[j + 1][i], z[j + 1][i + 1]
        if tx >= ty:
            return z00 + (z10 - z00) * tx + (z11 - z10) * ty
        return z00 + (z11 - z01) * tx + (z01 - z00) * ty

    def para_json(self) -> dict:
        """NaN (fora do levantamento) vai como null: JSON padrão."""
        z = [[None if v is None or math.isnan(v) else v for v in linha] for linha in self.z]
        return {"x0": self.x0, "y0": self.y0, "passo": self.passo, "nx": self.nx, "ny": self.ny, "z": z}

    @classmethod
    def de_json(cls, d: dict) -> "Grade":
        z = [[math.nan if v is None else v for v in linha] for linha in d["z"]]
        return cls(d["x0"], d["y0"], d["passo"], d["nx"], d["ny"], z)


def gerar_grade(curvas: list[Curva], ext: tuple[float, float, float, float], passo: float,
                preencher: bool = True) -> Grade:
    """Interpolação linear entre as curvas; fora delas, vizinho mais próximo ou (sem `preencher`) NaN."""
    pts = np.array([(x, y) for c in curvas if c.z is not None for x, y in c.pontos])
    zs = np.array([c.z for c in curvas if c.z is not None for _ in c.pontos])
    xmin, ymin, xmax, ymax = ext
    nx, ny = int(math.ceil((xmax - xmin) / passo)) + 1, int(math.ceil((ymax - ymin) / passo)) + 1
    gx, gy = np.meshgrid(xmin + passo * np.arange(nx), ymin + passo * np.arange(ny))
    z = LinearNDInterpolator(pts, zs)(gx, gy)
    vazio = np.isnan(z)
    if preencher and vazio.any():
        z[vazio] = NearestNDInterpolator(pts, zs)(gx[vazio], gy[vazio])
    return Grade(float(xmin), float(ymin), float(passo), nx, ny, np.round(z, 2).tolist())


def mascara(grade: Grade, aneis: list[list[Ponto]]) -> np.ndarray:
    """Pontos da grade dentro de algum dos anéis (z[j][i] → mascara[j, i]); par-ímpar, vetorizado."""
    gx, gy = np.meshgrid(grade.x0 + grade.passo * np.arange(grade.nx), grade.y0 + grade.passo * np.arange(grade.ny))
    dentro = np.zeros(gx.shape, dtype=bool)
    for anel in aneis:
        impar = np.zeros(gx.shape, dtype=bool)
        for (x0, y0), (x1, y1) in zip(anel, anel[1:] + anel[:1]):
            if y0 == y1:
                continue
            cruza = (y0 > gy) != (y1 > gy)
            impar ^= cruza & (gx < (x1 - x0) * (gy - y0) / (y1 - y0) + x0)
        dentro |= impar
    return dentro


def _densificar(pts: list[Ponto], passo: float = 10.0) -> list[Ponto]:
    saida = [pts[0]]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(bx - ax, by - ay) // passo))
        saida += [(ax + (bx - ax) * k / n, ay + (by - ay) * k / n) for k in range(1, n + 1)]
    return saida


def curva_do_dxf(e, e0: float, n0: float) -> Curva:
    """POLYLINE de curva de nível em coordenadas locais; a fechada volta ao início (o fecho conta)."""
    pts = [(p.x - e0, p.y - n0) for p in e.points()]
    fechada = bool(e.is_closed) and len(pts) > 2
    if fechada and pts[0] != pts[-1]:
        pts.append(pts[0])
    return Curva(_densificar(pts), fechada=fechada)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    georref = json.loads((RAIZ / "dados" / "georref.json").read_text(encoding="utf-8"))
    e0, n0 = georref["origem"]["E"], georref["origem"]["N"]
    lotes = json.loads((RAIZ / "dados" / "lotes.json").read_text(encoding="utf-8"))["lotes"]
    xs = [x for l in lotes for x, _ in l["poligono"]]
    ys = [y for l in lotes for _, y in l["poligono"]]
    ext = (min(xs) - MARGEM, min(ys) - MARGEM, max(xs) + MARGEM, max(ys) + MARGEM)
    perto = lambda pts: any(ext[0] - 50 <= x <= ext[2] + 50 and ext[1] - 50 <= y <= ext[3] + 50 for x, y in pts)  # noqa: E731

    msp = ezdxf.readfile(DXF).modelspace()
    mestras = [c for e in msp.query('POLYLINE[layer=="TOP-C-MESTRA"]') if perto((c := curva_do_dxf(e, e0, n0)).pontos)]
    inters = [c for e in msp.query('POLYLINE[layer=="TOP-C-INTER"]') if perto((c := curva_do_dxf(e, e0, n0)).pontos)]
    rotulos = []
    for t in msp.query('TEXT[layer=="TOP-C-MESTRA"]'):
        try:
            rotulos.append(((t.dxf.insert.x - e0, t.dxf.insert.y - n0), float(t.dxf.text.replace(",", "."))))
        except ValueError:
            continue
    sem = cotar_mestras(mestras, rotulos)
    cotar_intermediarias(inters, mestras)
    completar_mestras(mestras, [c for c in mestras + inters if c.z is not None])
    cotar_intermediarias(inters, mestras)  # de novo, agora com as mestras completadas
    cotar_aneis(mestras, inters)  # topos e fundos fechados, de fora para dentro
    grade = gerar_grade(mestras + inters, ext, PASSO_GRADE, preencher=False)
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(grade.para_json()), encoding="utf-8")
    todos = [v for linha in grade.z for v in linha]
    zs = [v for v in todos if not math.isnan(v)]
    print(
        f"mestras {len(mestras)} ({sem} sem rótulo nem emenda, completadas pela vizinha; "
        f"{sum(c.z is None for c in mestras)} sem cota) · intermediárias {len(inters)} "
        f"({sum(c.z is None for c in inters)} sem cota) · grade {grade.nx}×{grade.ny} ({len(zs) / len(todos):.0%} coberta) · cota {min(zs):.1f}–{max(zs):.1f} m"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
