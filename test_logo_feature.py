"""
Teste automatizado para a funcionalidade de Adicionar Logotipo em PDF.
"""

import io
from pathlib import Path
import pikepdf
from PIL import Image, ImageDraw
from starlette.testclient import TestClient

from app.main import app


def create_sample_pdf(num_pages: int = 3) -> io.BytesIO:
    doc = pikepdf.Pdf.new()
    for _ in range(num_pages):
        doc.add_blank_page(page_size=(595, 842))
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


def create_sample_logo_png(width: int = 300, height: int = 150) -> io.BytesIO:
    # Cria logo com canal alfa (transparente) e elemento colorido
    img = Image.new("RGBA", (width, height), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([10, 10, width - 10, height - 10], radius=15, fill=(16, 185, 129, 230), outline=(255, 255, 255, 255), width=3)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def run_logo_tests():
    client = TestClient(app)
    session_id = "test_session_logo_suite"

    print("==================================================")
    print("  TESTANDO FUNCIONALIDADE: ADICIONAR LOGO NO PDF  ")
    print("==================================================")

    # 1. Interface e Health Check
    print("\n[1/5] Verificando GET / e GET /api/health...")
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    assert "stage-add-logo" in html
    assert 'data-tool="add-logo"' in html
    assert "Adicionar Logo" in html
    print("  -> Template index.html renderiza palco stage-add-logo e botões!")

    h_res = client.get("/api/health")
    assert h_res.status_code == 200
    health = h_res.json()
    assert any("Logotipo" in feat for feat in health["features"])
    print("  -> /api/health confirma suporte a Adicionar Logotipo no PDF!")

    # 2. Upload de Arquivos
    print("\n[2/5] Testando upload de PDF e logotipo PNG...")
    pdf_bytes = create_sample_pdf(3)
    logo_bytes = create_sample_logo_png(250, 120)

    files = [
        ("files", ("relatorio_empresa.pdf", pdf_bytes, "application/pdf")),
        ("files", ("logo_oficial.png", logo_bytes, "image/png")),
    ]
    up_res = client.post("/api/upload", data={"session_id": session_id}, files=files)
    assert up_res.status_code == 200
    up_data = up_res.json()
    assert up_data["success"] is True
    assert len(up_data["files"]) == 2

    pdf_saved = up_data["files"][0]["saved_filename"]
    logo_saved = up_data["files"][1]["saved_filename"]
    print(f"  -> Upload concluído: PDF='{pdf_saved}', Logo='{logo_saved}'")

    # 3. Adicionar Logo em todas as páginas (Topo Direito)
    print("\n[3/5] Testando POST /api/add-logo (Topo Direito em Todas as Páginas)...")
    payload1 = {
        "session_id": session_id,
        "file_id": pdf_saved,
        "logo_image_id": logo_saved,
        "position": "top-right",
        "scale": 0.22,
        "margin_x": 36.0,
        "margin_y": 36.0,
        "opacity": 1.0,
        "layer": "overlay",
        "pages": "all",
        "output_filename": "relatorio_com_logo_top_right.pdf",
        "linearize": True,
    }
    res_logo1 = client.post("/api/add-logo", json=payload1)
    assert res_logo1.status_code == 200
    data1 = res_logo1.json()
    assert data1["success"] is True
    assert data1["metrics"]["pages_applied"] == 3
    assert data1["metrics"]["position"] == "top-right"
    print(f"  -> Logo aplicado: {data1['output_filename']} ({data1['metrics']['pages_applied']}/3 págs em {data1['metrics']['duration_seconds']}s)")

    # 4. Adicionar Logo com exceção de capa (except-first) e posição Rodapé Direito
    print("\n[4/5] Testando POST /api/add-logo (Rodapé Direito, exceto capa)...")
    payload2 = {
        "session_id": session_id,
        "file_id": pdf_saved,
        "logo_image_id": logo_saved,
        "position": "bottom-right",
        "scale": 0.18,
        "margin_x": 28.0,
        "margin_y": 28.0,
        "opacity": 0.85,
        "layer": "overlay",
        "pages": "except-first",
        "output_filename": "relatorio_com_logo_rodape.pdf",
        "linearize": True,
    }
    res_logo2 = client.post("/api/add-logo", json=payload2)
    assert res_logo2.status_code == 200
    data2 = res_logo2.json()
    assert data2["success"] is True
    assert data2["metrics"]["pages_applied"] == 2 # 3 páginas menos capa = 2
    assert data2["metrics"]["position"] == "bottom-right"
    print(f"  -> Logo aplicado nas internas: {data2['output_filename']} ({data2['metrics']['pages_applied']}/3 págs aplicadas)")

    # 5. Validação de Download e Preview
    print("\n[5/5] Testando download e pré-visualização do resultado...")
    dl_res = client.get(f"/api/download/{session_id}?filename=relatorio_com_logo_top_right.pdf")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/pdf"
    assert len(dl_res.content) > 1000

    # Verifica integridade do PDF gerado com pikepdf
    with pikepdf.open(io.BytesIO(dl_res.content)) as pdoc:
        assert len(pdoc.pages) == 3
    print("  -> Download e integridade do PDF verificado com sucesso via PikePDF!")

    # Limpeza
    del_res = client.delete(f"/api/session/{session_id}")
    assert del_res.status_code == 200
    print("\n==================================================")
    print("  PARABÉNS! TODOS OS TESTES PASSARAM COM 100%!    ")
    print("==================================================")


if __name__ == "__main__":
    run_logo_tests()
