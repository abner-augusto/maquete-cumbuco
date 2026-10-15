"""Pontos de interesse: coordenada do OSM (Nominatim, casado pela referência da curadoria; lugar
ausente do OSM vai com a coordenada lida no satélite, campo "satelite" da curadoria),
minutos de carro no grafo viário do OSM e fotos livres do Wikimedia Commons.

Uso: uv run python -m scripts.pontos.pontos

Escreve dados/pontos.json e cache/pontos/fotos-candidatas.html (galeria para aprovar fotos:
a escolhida vai como "foto": "File:…" no ponto da curadoria, e o script a baixa na próxima vez).
Minutos: modelo simples de argumento de venda (velocidade fixa por classe, mão única, + 1 min de
manobra), como no Manoa.
"""

import heapq
import html
import json
import math
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

from scripts.comum.ambiente import RAIZ
from scripts.entorno.extrair import BASE, MALHA
from scripts.loteamento.terreno import DESTINO_ENTORNO, Relevo
from scripts.entorno.osm import AGENTE, Projecao, linha_osm, overpass, poligono_osm

CURADORIA = RAIZ / "scripts" / "pontos" / "curadoria.json"
DESTINO = RAIZ / "dados" / "pontos.json"
FOTOS = RAIZ / "dados" / "pontos" / "fotos"
CACHE = RAIZ / "cache" / "pontos"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
COMMONS = "https://commons.wikimedia.org/w/api.php"
CARRO_KMH = {
    "motorway": 80, "trunk": 60, "primary": 50, "secondary": 40, "tertiary": 35, "motorway_link": 35,
    "trunk_link": 35, "primary_link": 30, "secondary_link": 30, "tertiary_link": 25, "unclassified": 30,
    "residential": 25, "living_street": 15, "service": 15, "track": 15,
}
MANOBRA_MIN = 1
PONTA_M_MIN = 25 * 1000 / 60  # do loteamento à rua e da rua ao ponto, como rua local
LIMITE_PONTA_M = 3000  # alvo além disso sem sair do nó de partida: sem rota


def slug(nome: str) -> str:
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def distancia_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371008.8 * math.asin(math.sqrt(a))


def escolher_osm(resultados: list[dict], ref_lat: float, ref_lon: float, max_m: float = 2000.0) -> dict | None:
    """O resultado do OSM mais perto da referência da curadoria; nada além de `max_m` (homônimo)."""
    perto = [(distancia_m(ref_lat, ref_lon, float(r["lat"]), float(r["lon"])), r) for r in resultados]
    perto = [(d, r) for d, r in perto if d <= max_m]
    return min(perto, key=lambda t: t[0])[1] if perto else None


def faixa(dist_m: float, limite: float = 3000.0) -> str:
    return "proximo" if dist_m <= limite else "distante"


def licenca_livre(nome: str) -> bool:
    n = (nome or "").upper()
    if "NC" in n.replace("-", " ").split() or "-NC" in n or "-ND" in n or " ND" in n:
        return False
    return n.startswith(("CC BY", "CC0", "PUBLIC DOMAIN", "PD"))


def grafo_carro(elementos: list[dict], proj: Projecao) -> tuple[dict, dict]:
    xy, grafo = {}, {}
    for w in elementos:
        tags = w.get("tags", {})
        classe = tags.get("highway")
        if classe not in CARRO_KMH or "nodes" not in w or "geometry" not in w:
            continue
        if tags.get("motor_vehicle") == "no" or tags.get("access") in ("no", "private"):
            continue
        for n, g in zip(w["nodes"], w["geometry"]):
            xy[n] = proj.xy(g["lon"], g["lat"])
        mao = tags.get("oneway") or ("yes" if tags.get("junction") == "roundabout" else None)
        for a, b in zip(w["nodes"], w["nodes"][1:]):
            t = math.dist(xy[a], xy[b]) / (CARRO_KMH[classe] * 1000 / 60)
            if mao != "-1":
                grafo.setdefault(a, []).append((b, t))
            if mao not in ("yes", "1", "true", "-1"):
                grafo.setdefault(b, []).append((a, t))
            if mao == "-1":
                grafo.setdefault(b, []).append((a, t))
    return xy, grafo


def minutos(grafo: dict, xy: dict, origem: tuple[float, float], alvo: tuple[float, float]) -> int | None:
    """Minutos de carro: entra no grafo pelo nó mais perto da origem e sai pelo nó *alcançável* mais
    perto do alvo (o mais perto pode estar num trecho solto da malha). As pontas (do loteamento à rua,
    da rua ao ponto) contam a 25 km/h, como rua local."""
    a = min(xy, key=lambda n: math.dist(xy[n], origem))
    tempo, fila = {a: 0.0}, [(0.0, a)]
    while fila:
        t, n = heapq.heappop(fila)
        if t > tempo[n]:
            continue
        for v, dt in grafo.get(n, []):
            if t + dt < tempo.get(v, math.inf):
                tempo[v] = t + dt
                heapq.heappush(fila, (t + dt, v))
    b = min(tempo, key=lambda n: math.dist(xy[n], alvo))
    ponta = (math.dist(xy[a], origem) + math.dist(xy[b], alvo)) / PONTA_M_MIN
    total = tempo[b] + ponta + MANOBRA_MIN
    return math.ceil(round(total, 6)) if b != a or math.dist(xy[a], alvo) < LIMITE_PONTA_M else None

def _get(url: str, params: dict, cache) -> dict | list:
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": AGENTE})
    with urllib.request.urlopen(req, timeout=60) as r:
        dados = json.loads(r.read())
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    time.sleep(1.1)  # política de uso do Nominatim e boa educação com o Commons
    return dados


def _sem_html(texto: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", texto or "")).strip()


def candidatos_commons(nome: str, lat: float, lon: float) -> list[dict]:
    """Arquivos do Commons perto do ponto (2 km) e pelo nome, só com licença livre."""
    comum = {"action": "query", "format": "json", "prop": "imageinfo", "iiprop": "url|extmetadata",
             "iiurlwidth": 1600}
    perto = _get(COMMONS, {**comum, "generator": "geosearch", "ggscoord": f"{lat}|{lon}", "ggsradius": 2000,
                           "ggsnamespace": 6, "ggslimit": 20}, CACHE / "commons" / f"{slug(nome)}-geo.json")
    busca = _get(COMMONS, {**comum, "generator": "search", "gsrsearch": f"{nome} Ceará", "gsrnamespace": 6,
                           "gsrlimit": 20}, CACHE / "commons" / f"{slug(nome)}-busca.json")
    vistos, saida = set(), []
    for dados in (perto, busca):
        for pg in (dados.get("query", {}).get("pages", {}) or {}).values():
            info = (pg.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata", {})
            lic = meta.get("LicenseShortName", {}).get("value", "")
            if pg["title"] in vistos or not licenca_livre(lic) or not info.get("thumburl"):
                continue
            vistos.add(pg["title"])
            saida.append({"titulo": pg["title"], "miniatura": info["thumburl"], "pagina": info.get("descriptionurl"),
                          "autor": _sem_html(meta.get("Artist", {}).get("value", "")), "licenca": lic,
                          "licenca_url": meta.get("LicenseUrl", {}).get("value")})
    return saida


def galeria(candidatos: dict[str, list[dict]]) -> str:
    blocos = []
    for nome, cs in candidatos.items():
        itens = "".join(
            f'<figure><img src="{html.escape(c["miniatura"])}" loading="lazy" width="320">'
            f'<figcaption><b>{html.escape(c["titulo"])}</b><br>{html.escape(c["autor"])} · '
            f'{html.escape(c["licenca"])} · <a href="{html.escape(c.get("pagina") or "")}">página</a></figcaption></figure>'
            for c in cs) or "<p>sem foto livre encontrada</p>"
        blocos.append(f"<section><h2>{html.escape(nome)}</h2>{itens}</section>")
    return ("<!doctype html><meta charset=utf-8><title>Fotos candidatas</title>"
            "<style>body{font:14px sans-serif;margin:16px}figure{display:inline-block;width:330px;vertical-align:top}"
            "img{max-width:320px}</style><h1>Fotos candidatas (Wikimedia Commons, licença livre)</h1>"
            + "".join(blocos))


def separar_pendentes(pontos: list[dict]) -> tuple[list[dict], list[str]]:
    """Ponto com "pendente" na curadoria (sem elemento no OSM, à espera de decisão) fica fora do site."""
    return [p for p in pontos if not p.get("pendente")], [f"{p['nome']}: {p['pendente']}" for p in pontos if p.get("pendente")]


def ponto_do_elemento(proj: Projecao, el: dict, em_terra=None) -> tuple[float, float]:
    """(lon, lat) do pino: o nó; numa área, um ponto garantidamente dentro dela (o centro da caixa de
    uma praia curva cai no mar), e com `em_terra(x, y)` o ponto da área em terra mais perto desse;
    numa linha, o meio dela."""
    if el["type"] == "node":
        return el["lon"], el["lat"]
    g = poligono_osm(proj, el)
    if g is None:
        from shapely.geometry import LineString

        g = LineString(linha_osm(proj, el.get("geometry") or [m for mb in el.get("members", [])
                                                              for m in (mb.get("geometry") or [])]))
        pt = g.interpolate(0.5, normalized=True)
    else:
        pt = g.representative_point()
        if em_terra is not None and not em_terra(pt.x, pt.y):
            from shapely.geometry import Point

            x0, y0, x1, y1 = g.bounds
            passo = max(x1 - x0, y1 - y0) / 200
            grade = [Point(x0 + i * passo, y0 + j * passo) for i in range(201) for j in range(201)]
            ok = [q for q in grade if g.contains(q) and em_terra(q.x, q.y)]
            if ok:
                pt = min(ok, key=pt.distance)
    return proj.lonlat(pt.x, pt.y)


LIMITE_SATELITE_M = 500  # ponto marcado longe da referência do Google é digitação errada


def coordenada_osm(p: dict, proj: Projecao, em_terra=None) -> dict:
    """Coordenada do pino: do OSM, ou lida sobre a imagem de satélite quando o lugar não está no OSM
    ("satelite" na curadoria, como os marcos do Manoa)."""
    if p.get("satelite"):
        s = p["satelite"]
        d = distancia_m(p["ref_lat"], p["ref_lon"], s["lat"], s["lon"])
        if d > LIMITE_SATELITE_M:
            raise SystemExit(f"{p['nome']}: \"satelite\" a {d:.0f} m da referência (limite {LIMITE_SATELITE_M} m); "
                             f"confira a leitura")
        return {"lat": s["lat"], "lon": s["lon"], "osm_type": None, "osm_id": None, "fonte": "satelite"}
    if p.get("osm"):
        tipo, ident = p["osm"].split("/")
        els = overpass(f"[out:json];{tipo}({ident});out geom;", CACHE / "osm" / f"{tipo}-{ident}-geom.json")["elements"]
        if not els:
            raise SystemExit(f"{p['nome']}: {p['osm']} não existe no OSM; corrija o \"osm\" da curadoria")
        lon, lat = ponto_do_elemento(proj, els[0], em_terra)
        return {"lat": lat, "lon": lon, "osm_type": tipo, "osm_id": int(ident), "fonte": "osm"}
    caixa = 0.05
    rs = _get(NOMINATIM, {"q": p["nome"], "format": "jsonv2", "limit": 10, "bounded": 1,
                          "viewbox": f"{p['ref_lon'] - caixa},{p['ref_lat'] + caixa},{p['ref_lon'] + caixa},{p['ref_lat'] - caixa}"},
              CACHE / "nominatim" / f"{slug(p['nome'])}.json")
    r = escolher_osm(rs, p["ref_lat"], p["ref_lon"])
    if r is None:
        raise SystemExit(f"{p['nome']}: sem elemento do OSM a até 2 km da referência; "
                         f"ponha \"osm\": \"node/…\" na curadoria")
    return {"lat": float(r["lat"]), "lon": float(r["lon"]), "osm_type": r["osm_type"], "osm_id": r["osm_id"], "fonte": "osm"}


def baixar_foto(p: dict, cand: list[dict]) -> dict:
    escolhida = next((c for c in cand if c["titulo"] == p["foto"]), None)
    if escolhida is None:
        raise SystemExit(f"{p['nome']}: foto {p['foto']} não está entre as candidatas livres")
    destino = FOTOS / f"{slug(p['nome'])}.jpg"
    if not destino.exists():
        FOTOS.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(escolhida["miniatura"], headers={"User-Agent": AGENTE})
        with urllib.request.urlopen(req, timeout=120) as r:
            destino.write_bytes(r.read())
    return {"foto": f"pontos/fotos/{destino.name}", "credito": escolhida["autor"], "licenca": escolhida["licenca"],
            "licenca_url": escolhida["licenca_url"], "fonte_foto": escolhida["pagina"]}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    georref = json.loads((RAIZ / "dados" / "georref.json").read_text(encoding="utf-8"))
    proj = Projecao(georref["origem"]["E"], georref["origem"]["N"])
    cur = json.loads(CURADORIA.read_text(encoding="utf-8"))
    centro = tuple(json.loads(BASE.read_text(encoding="utf-8"))["centro"])
    xy, grafo = grafo_carro(json.loads(MALHA.read_text(encoding="utf-8"))["elements"]
                            + json.loads((MALHA.parent / "osm-vias.json").read_text(encoding="utf-8"))["elements"], proj)
    relevo = Relevo.carregar()
    nivel = next(o for o in json.loads(DESTINO_ENTORNO.read_text(encoding="utf-8"))["objetos"]
                 if o["nome"] == "Mar")["vertices"][0][2]
    em_terra = lambda x, y: relevo.cota(x, y) > nivel + 0.5  # noqa: E731 — o pino não fica no mar
    pontos, candidatos = [], {}
    prontos, pendentes = separar_pendentes(cur["pontos"])
    for p in prontos:
        c = coordenada_osm(p, proj, em_terra)
        x, y = proj.xy(c["lon"], c["lat"])
        dist = math.dist((x, y), centro)
        cand = candidatos_commons(p["nome"], c["lat"], c["lon"])
        candidatos[p["nome"]] = cand
        foto = baixar_foto(p, cand) if p.get("foto") else {k: None for k in
                                                           ("foto", "credito", "licenca", "licenca_url", "fonte_foto")}
        m = minutos(grafo, xy, centro, (x, y))
        if m is None:
            raise SystemExit(f"{p['nome']}: sem rota de carro no grafo")
        pontos.append({"nome": p["nome"], "categoria": p["categoria"], "lat": round(c["lat"], 6), "lon": round(c["lon"], 6),
                       "x": round(x, 1), "y": round(y, 1), "km": round(dist / 1000, 1), "minutos_carro": m,
                       "faixa": faixa(dist), "fonte_coord": c["fonte"],
                       "osm": f"{c['osm_type']}/{c['osm_id']}" if c["osm_type"] else None, **foto})
        print(f"{p['nome'][:30]:30s} {dist / 1000:5.1f} km {m:3d} min  {pontos[-1]['faixa']:8s} "
              f"{len(cand):2d} fotos livres  ref↔OSM {distancia_m(p['ref_lat'], p['ref_lon'], c['lat'], c['lon']):5.0f} m")
    DESTINO.write_text(json.dumps({"versao": 1, "origem": {"x": 0, "y": 0},
                                   "fontes": "coordenadas © OpenStreetMap contributors (ODbL), ou marcadas sobre imagem de satélite (Esri World Imagery) quando o lugar não está no OSM; fotos: Wikimedia Commons (autor e licença por ponto)",
                                   "pontos": pontos}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (CACHE / "fotos-candidatas.html").write_text(galeria(candidatos), encoding="utf-8")
    print(f"{len(pontos)} pontos → {DESTINO.relative_to(RAIZ)}; galeria → cache/pontos/fotos-candidatas.html")
    for p in pendentes:
        print("pendente (fora do site):", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
