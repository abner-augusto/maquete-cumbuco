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
