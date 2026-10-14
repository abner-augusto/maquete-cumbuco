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
