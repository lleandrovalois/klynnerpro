"""
Testes automatizados para as novas funcionalidades:
1. Imagem para PDF (Image to PDF)
2. Inserir Marca d'água em PDF (Watermark PDF - Texto, Mosaico e Imagem)
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


def create_sample_image(width: int = 400, height: int = 300, color: str = "red") -> io.BytesIO:
    img = Image.new("RGB", (width, height), color=color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, width - 20, height - 20], outline="white", width=4)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def test_suite_new_features():
    client = TestClient(app)
    session_id = "test_sess_new_features"

    print("==================================================")
    print("  TESTANDO NOVAS FUNCIONALIDADES DO KLYNNER PRO   ")
    print("==================================================")

    # 1. Validação de Interface HTML e Health Check
    print("\n[1/5] Testando GET / e GET /api/health...")
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    assert "stage-image-to-pdf" in html
    assert "stage-watermark" in html
    assert "tool-nav-i2p" in html
    assert "tool-nav-watermark" in html
    assert "Imagem para PDF" in html
    assert "Marca d&#39;água" in html or "Marca d'água" in html
    print("  -> Template index.html possui todos os novos estágios e botões de navegação!")

    h_res = client.get("/api/health")
    assert h_res.status_code == 200
    health = h_res.json()
    assert len(health["features"]) == 12
    assert "Converter Imagem para PDF (Image to PDF)" in health["features"]
    assert "Inserir Marca d'água (Watermark PDF)" in health["features"]
    print("  -> Health check OK: 12 ferramentas registradas e operacionais!")

    # 2. Upload de Imagens e PDF de Teste
    print("\n[2/5] Testando POST /api/upload com imagens (.png) e PDF...")
    img1_data = create_sample_image(800, 600, color="crimson")
    img2_data = create_sample_image(600, 800, color="navy")
    logo_data = create_sample_image(200, 200, color="gold")
    pdf_data = create_sample_pdf(3)

    files = [
        ("files", ("foto_paisagem.png", img1_data, "image/png")),
        ("files", ("foto_retrato.png", img2_data, "image/png")),
        ("files", ("logo_marca.png", logo_data, "image/png")),
        ("files", ("documento_base.pdf", pdf_data, "application/pdf")),
    ]
    up_res = client.post("/api/upload", data={"session_id": session_id}, files=files)
    assert up_res.status_code == 200
    up_data = up_res.json()
    assert up_data["success"] is True
    assert len(up_data["files"]) == 4

    saved_img1 = up_data["files"][0]["saved_filename"]
    saved_img2 = up_data["files"][1]["saved_filename"]
    saved_logo = up_data["files"][2]["saved_filename"]
    saved_pdf = up_data["files"][3]["saved_filename"]
    print(f"  -> Upload de 3 imagens e 1 PDF realizado com sucesso!")

    # 3. Teste Imagem para PDF
    print("\n[3/5] Testando POST /api/convert/image-to-pdf...")
    i2p_payload = {
        "session_id": session_id,
        "image_files": [saved_img1, saved_img2],
        "page_size": "a4",
        "orientation": "auto",
        "margin": "small",
        "output_filename": "album_fotos.pdf",
        "linearize": True,
    }
    i2p_res = client.post("/api/convert/image-to-pdf", json=i2p_payload)
    assert i2p_res.status_code == 200
    i2p_json = i2p_res.json()
    assert i2p_json["success"] is True
    assert i2p_json["metrics"]["total_images"] == 2
    assert i2p_json["metrics"]["total_pages"] == 2
    assert i2p_json["output_filename"] == "album_fotos.pdf"

    # Validação binária do PDF gerado
    dl_i2p = client.get(f"/api/download/{session_id}?filename=album_fotos.pdf")
    assert dl_i2p.status_code == 200
    with pikepdf.open(io.BytesIO(dl_i2p.content)) as doc:
        assert len(doc.pages) == 2
    print(f"  -> Imagem to PDF OK: {i2p_json['output_filename']} com 2 páginas compiladas e verificadas!")

    # 4. Teste Marca d'água Texto (Centro e Mosaico)
    print("\n[4/5] Testando POST /api/watermark com Texto (Centro e Mosaico)...")
    # 4.1 Marca d'água central em todas as páginas
    wm_text_payload = {
        "session_id": session_id,
        "file_id": saved_pdf,
        "watermark_type": "text",
        "text": "CONFIDENCIAL",
        "font_size": 48,
        "font_color": "#DC2626",
        "opacity": 0.3,
        "rotation": -45,
        "position": "center",
        "layer": "overlay",
        "pages": "all",
        "output_filename": "doc_confidencial.pdf",
        "linearize": True,
    }
    wm_res = client.post("/api/watermark", json=wm_text_payload)
    assert wm_res.status_code == 200
    wm_json = wm_res.json()
    assert wm_json["success"] is True
    assert wm_json["metrics"]["pages_watermarked"] == 3
    assert wm_json["metrics"]["total_pages"] == 3

    # Validação binária
    dl_wm = client.get(f"/api/download/{session_id}?filename=doc_confidencial.pdf")
    assert dl_wm.status_code == 200
    with pikepdf.open(io.BytesIO(dl_wm.content)) as doc:
        assert len(doc.pages) == 3
    print("  -> Marca d'água Texto (Centro em todas as páginas) OK!")

    # 4.2 Marca d'água Mosaico (Tiling) apenas na 1ª página
    wm_tile_payload = {
        "session_id": session_id,
        "file_id": saved_pdf,
        "watermark_type": "text",
        "text": "CÓPIA NÃO AUTORIZADA",
        "font_size": 32,
        "font_color": "#2563EB",
        "opacity": 0.2,
        "rotation": -45,
        "position": "tile",
        "layer": "overlay",
        "pages": "first",
        "output_filename": "doc_tile_copia.pdf",
        "linearize": True,
    }
    wm_tile_res = client.post("/api/watermark", json=wm_tile_payload)
    assert wm_tile_res.status_code == 200
    wm_tile_json = wm_tile_res.json()
    assert wm_tile_json["metrics"]["pages_watermarked"] == 1
    print("  -> Marca d'água Mosaico / Grade Repetida (Tiling) OK!")

    # 5. Teste Marca d'água com Imagem / Logotipo
    print("\n[5/5] Testando POST /api/watermark com Logotipo (Imagem)...")
    wm_img_payload = {
        "session_id": session_id,
        "file_id": saved_pdf,
        "watermark_type": "image",
        "watermark_image_id": saved_logo,
        "image_scale": 0.4,
        "opacity": 0.35,
        "rotation": 0,
        "position": "top",
        "layer": "overlay",
        "pages": "all",
        "output_filename": "doc_logo.pdf",
        "linearize": True,
    }
    wm_img_res = client.post("/api/watermark", json=wm_img_payload)
    assert wm_img_res.status_code == 200
    wm_img_json = wm_img_res.json()
    assert wm_img_json["success"] is True
    assert wm_img_json["metrics"]["pages_watermarked"] == 3

    dl_logo = client.get(f"/api/download/{session_id}?filename=doc_logo.pdf")
    assert dl_logo.status_code == 200
    with pikepdf.open(io.BytesIO(dl_logo.content)) as doc:
        assert len(doc.pages) == 3
    print("  -> Marca d'água com Logotipo (Imagem PNG com transparência) OK!")

    # Limpeza
    del_res = client.delete(f"/api/session/{session_id}")
    assert del_res.status_code == 200

    print("\n==================================================")
    print("  SUCESSO ABSOLUTO! TODOS OS TESTES PASSARAM!     ")
    print("==================================================")


if __name__ == "__main__":
    test_suite_new_features()
