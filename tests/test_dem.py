import math

import numpy as np
import pytest
import rasterio
from pyproj import Transformer
from rasterio.transform import from_origin

from scripts.entorno.dem import amostrar, baixar, grade_dem

E0, N0 = 534600.0, 9595100.0
LON0, LAT0, PX = -38.75, -3.60, 1 / 3600


def _cota(lon, lat):
    return 1000.0 * (lon - LON0) + 500.0 * (lat - LAT0)  # plano: o bilinear reproduz exato


@pytest.fixture
def tif(tmp_path):
    n = 400
    cols, lins = np.meshgrid(np.arange(n), np.arange(n))
    z = _cota(LON0 + (cols + 0.5) * PX, LAT0 - (lins + 0.5) * PX).astype("float32")
    z[0, 0] = -32767.0  # nodata no canto
    caminho = tmp_path / "dem.tif"
    with rasterio.open(caminho, "w", driver="GTiff", width=n, height=n, count=1, dtype="float32",
                       crs="EPSG:4326", transform=from_origin(LON0, LAT0, PX, PX), nodata=-32767.0) as d:
        d.write(z, 1)
    return caminho


def test_amostrar_reproduz_o_plano_no_ponto_utm(tif):
    e = np.array([E0, E0 + 1234.5]); n = np.array([N0, N0 - 987.0])
    lon, lat = Transformer.from_crs("EPSG:31984", "EPSG:4326", always_xy=True).transform(e, n)
    assert amostrar(tif, e, n) == pytest.approx(_cota(lon, lat), abs=1e-3)


def test_amostrar_nodata_vira_zero(tif):
    lon, lat = LON0 + 0.5 * PX, LAT0 - 0.5 * PX  # centro do pixel nodata
    e, n = Transformer.from_crs("EPSG:4326", "EPSG:31984", always_xy=True).transform(lon, lat)
    assert amostrar(tif, np.array([e]), np.array([n]))[0] == pytest.approx(0.0, abs=1e-6)


def test_grade_dem_nos_em_multiplos_do_passo_e_cobre_o_raio(tif):
    g = grade_dem(tif, E0, N0, centro=(17.0, -42.0), raio=300.0, passo=30.0)
    assert g.x0 % 30 == 0 and g.y0 % 30 == 0
    assert g.x0 <= 17 - 300 and g.x0 + g.passo * (g.nx - 1) >= 17 + 300
    assert g.y0 <= -42 - 300 and g.y0 + g.passo * (g.ny - 1) >= -42 + 300
    lon, lat = Transformer.from_crs("EPSG:31984", "EPSG:4326", always_xy=True).transform(E0 + g.x0, N0 + g.y0)
    assert g.z[0][0] == pytest.approx(_cota(lon, lat), abs=0.01)


def test_baixar_grava_por_arquivo_parcial(tmp_path):
    origem = tmp_path / "origem.tif"
    origem.write_bytes(b"x" * 1000)
    destino = tmp_path / "cache" / "t.tif"
    assert baixar(origem.as_uri(), destino) == destino and destino.read_bytes() == b"x" * 1000
    assert not destino.with_suffix(".part").exists()
    origem.write_bytes(b"y")
    baixar(origem.as_uri(), destino)  # já existe: não baixa de novo
    assert destino.read_bytes() == b"x" * 1000
