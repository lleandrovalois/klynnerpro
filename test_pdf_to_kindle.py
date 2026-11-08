"""
Testes automatizados completos para a funcionalidade de Conversão de PDF para Kindle (EPUB / MOBI).
Cobre todos os Cenários BDD (Cenário 1, 2 e 3) e Regras de Negócio (RN-01 a RN-05).
"""

import io
from pathlib import Path
import time
import zipfile

from PIL import Image
import pikepdf
import pymupdf
from starlette.testclient import TestClient

from app.main import app
from app.pdf_to_kindle import (
    analyze_pdf_for_kindle,
    execute_pdf_to_kindle,
    get_kindle_job,
    KINDLE_JOBS,
)
from app.storage import get_session_dir


def create_text_pdf_with_bookmarks(num_pages: int = 3) -> io.BytesIO:
    """Gera PDF de teste com camadas de texto, marcadores/capítulos, cabeçalhos repetidos e hifenização."""
    doc = pymupdf.open()
    toc = []

    for i in range(1, num_pages + 1):
        page = doc.new_page(width=595, height=842)
        # Cabeçalho repetido no topo (10%)
        page.insert_text((50, 60), "Manual Corporativo Klynner", fontsize=9)
        # Título do capítulo
        page.insert_text((50, 140), f"Capítulo {i}: Fundamentos e Práticas", fontsize=16)
        # Texto corrido com quebra de linha hifenizada para testar reflow
        page.insert_text((50, 190), f"Este é o texto explicativo do capítulo {i} sobre transfor-\nmação de dados e reflow dinâmico.", fontsize=11)
        page.insert_text((50, 230), "Aqui continua o parágrafo sem interrupção de leitura na tela do leitor digital.", fontsize=11)
        # Rodapé repetido na base (90%)
        page.insert_text((50, 800), f"Página {i}", fontsize=9)

        toc.append([1, f"Capítulo {i}", i])

    doc.set_toc(toc)
    doc.set_metadata({
        "title": "Guia Oficial de Leitura Kindle",
        "author": "Equipe Editorial Klynner",
    })

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    buf.seek(0)
    return buf


def create_encrypted_pdf() -> io.BytesIO:
    """Gera PDF criptografado por senha para validação do Cenário 2."""
    doc = pikepdf.Pdf.new()
    doc.add_blank_page(page_size=(400, 600))
    buf = io.BytesIO()
    doc.save(buf, encryption=pikepdf.Encryption(owner="secreto123", user="secreto123"))
    buf.seek(0)
    return buf


def create_scanned_image_only_pdf() -> io.BytesIO:
    """Gera PDF puramente baseado em imagens (sem camada OCR) para validação do Cenário 3."""
    doc = pymupdf.open()
    page = doc.new_page(width=450, height=650)
    img = Image.new("RGB", (350, 550), color="ivory")
    img_buf = io.BytesIO()
    img.save(img_buf, format="JPEG")
    page.insert_image(pymupdf.Rect(50, 50, 400, 600), stream=img_buf.getvalue())
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    buf.seek(0)
    return buf


def run_kindle_tests():
    client = TestClient(app)
    session_id = "test_kindle_suite_session"
    session_dir = get_session_dir(session_id)

    print("==================================================")
    print("  TESTANDO CONVERSÃO PDF PARA KINDLE (EPUB / MOBI) ")
    print("==================================================")

    # 1. Health check e validação da lista de features e interface HTML
    print("\n[1/7] Testando interface HTML (GET /) e registro da feature no GET /api/health...")
    page_res = client.get("/")
    assert page_res.status_code == 200
    page_html = page_res.text
    assert "stage-pdf-to-kindle" in page_html
    assert 'data-tool="pdf-to-kindle"' in page_html
    assert "PDF para Kindle" in page_html
    assert "kindle-fmt-epub" in page_html
    assert "kindle-fmt-mobi" in page_html
    assert "kindle-scanned-warning-box" in page_html
    assert "btn-start-kindle" in page_html
    print("  -> Template index.html renderiza perfeitamente o estágio e controles do conversor Kindle!")

    h_res = client.get("/api/health")
    assert h_res.status_code == 200
    features = h_res.json()["features"]
    assert "Converter PDF para Kindle (EPUB / MOBI)" in features
    print("  -> Feature 'Converter PDF para Kindle (EPUB / MOBI)' devidamente registrada!")

    # 2. Cenário 2: Validação de arquivo protegido por senha (Cenário 2 BDD)
    print("\n[2/7] Testando Cenário 2 (PDF protegido por senha)...")
    enc_data = create_encrypted_pdf()
    up_enc = client.post("/api/upload", data={"session_id": session_id}, files=[("files", ("documento_travado.pdf", enc_data, "application/pdf"))])
    assert up_enc.status_code == 200
    enc_file_id = up_enc.json()["files"][0]["saved_filename"]

    # Deve falhar no analyze com mensagem exata
    res_enc = client.post("/api/kindle/analyze", json={"session_id": session_id, "file_id": enc_file_id})
    assert res_enc.status_code == 400
    err_msg = res_enc.json()["detail"]
    assert err_msg == "O arquivo enviado está protegido por senha. Remova a senha antes de converter."
    print(f"  -> Cenário 2 OK: Bloqueio imediato com a mensagem esperada: '{err_msg}'")

    # 3. Cenário 3: Detecção de PDF digitalizado sem camada de texto (Cenário 3 BDD)
    print("\n[3/7] Testando Cenário 3 (PDF digitalizado sem OCR)...")
    scanned_data = create_scanned_image_only_pdf()
    up_scan = client.post("/api/upload", data={"session_id": session_id}, files=[("files", ("scan_sem_ocr.pdf", scanned_data, "application/pdf"))])
    assert up_scan.status_code == 200
    scan_file_id = up_scan.json()["files"][0]["saved_filename"]

    res_scan = client.post("/api/kindle/analyze", json={"session_id": session_id, "file_id": scan_file_id})
    assert res_scan.status_code == 200
    scan_info = res_scan.json()
    assert scan_info["is_scanned"] is True
    expected_warning = "Este documento não possui camada de texto editável. A formatação no Kindle pode não suportar ajuste dinâmico de fonte."
    assert scan_info["warning_message"] == expected_warning
    print(f"  -> Cenário 3 OK: Alerta emitido corretamente: '{scan_info['warning_message']}'")

    # Conversão do scan com force_fixed_layout=True
    fixed_res = execute_pdf_to_kindle(
        session_dir=session_dir,
        file_id=scan_file_id,
        output_format="epub",
        force_fixed_layout=True,
    )
    assert fixed_res["is_fixed_layout"] is True
    fixed_epub_path = session_dir / "output" / fixed_res["output_filename"]
    assert fixed_epub_path.exists()
    with zipfile.ZipFile(fixed_epub_path, "r") as zf:
        # Garante que a imagem da página foi empacotada no EPUB
        assert any("images/page_1.jpg" in name for name in zf.namelist())
    print("  -> Cenário 3 (Opção Prosseguir com layout fixo) validado com sucesso!")

    # 4. Cenário 1: Conversão bem-sucedida de PDF baseado em texto para .epub (Cenário 1 BDD)
    print("\n[4/7] Testando Cenário 1 (Conversão bem-sucedida para .epub com reflow e marcadores)...")
    text_data = create_text_pdf_with_bookmarks(num_pages=3)
    up_text = client.post("/api/upload", data={"session_id": session_id}, files=[("files", ("livro_completo.pdf", text_data, "application/pdf"))])
    assert up_text.status_code == 200
    text_file_id = up_text.json()["files"][0]["saved_filename"]

    # Análise de metadados
    ana_res = client.post("/api/kindle/analyze", json={"session_id": session_id, "file_id": text_file_id})
    assert ana_res.status_code == 200
    ana_data = ana_res.json()
    assert ana_data["total_pages"] == 3
    assert ana_data["suggested_title"] == "Guia Oficial de Leitura Kindle"
    assert ana_data["suggested_author"] == "Equipe Editorial Klynner"
    assert ana_data["has_bookmarks"] is True
    assert ana_data["chapters_count"] == 3
    assert ana_data["is_scanned"] is False
    print("  -> Metadados e marcadores extraídos perfeitamente!")

    # Conversão síncrona/direta para teste de integridade binária
    epub_res = execute_pdf_to_kindle(
        session_dir=session_dir,
        file_id=text_file_id,
        output_format="epub",
        output_basename="meu_ebook_kindle",
    )
    assert epub_res["format"] == "epub"
    assert epub_res["total_pages"] == 3
    assert epub_res["chapters_count"] == 3
    assert epub_res["has_cover"] is True

    # 5. Validação profunda da estrutura do EPUB (RN-01, RN-02, RN-03)
    print("\n[5/7] Validando especificação EPUB (mimetype, cover.jpg, toc.ncx, reflow, remoção de headers)...")
    epub_path = session_dir / "output" / "meu_ebook_kindle.epub"
    assert epub_path.exists()
    assert epub_path.stat().st_size > 5000

    with zipfile.ZipFile(epub_path, "r") as zf:
        file_list = zf.namelist()
        # O mimetype DEVE ser o primeiro arquivo no zip (especificação IDPF/EPUB)
        assert file_list[0] == "mimetype"
        assert zf.read("mimetype") == b"application/epub+zip"

        # Verificação do container e manifesto
        assert "META-INF/container.xml" in file_list
        assert "OEBPS/content.opf" in file_list
        assert "OEBPS/styles.css" in file_list

        # RN-03: Extração de Capa (cover.jpg) da Página 1
        assert "OEBPS/images/cover.jpg" in file_list
        assert "OEBPS/cover.xhtml" in file_list

        # Capítulos correspondentes aos bookmarks (Cenário 1)
        assert "OEBPS/chapter_1.xhtml" in file_list
        assert "OEBPS/chapter_2.xhtml" in file_list
        assert "OEBPS/chapter_3.xhtml" in file_list
        assert "OEBPS/toc.ncx" in file_list
        assert "OEBPS/nav.xhtml" in file_list

        # RN-02: Validação de reflow e remoção de cabeçalhos repetidos
        ch1_text = zf.read("OEBPS/chapter_1.xhtml").decode("utf-8")
        # Cabeçalho "Manual Corporativo Klynner" e "Página 1" devem ter sido descartados
        assert "Manual Corporativo Klynner" not in ch1_text
        assert "Página 1" not in ch1_text
        # A palavra "transfor-\nmação" deve ter sido desfeita para "transformação"
        assert "transformação" in ch1_text

        # Sumário navegável NCX
        ncx_text = zf.read("OEBPS/toc.ncx").decode("utf-8")
        assert "Capítulo 1" in ncx_text
        assert "Capítulo 2" in ncx_text
        assert "Capítulo 3" in ncx_text

    print("  -> EPUB 100% conforme: mimetype uncompressed, capa cover.jpg, reflow de texto e sumário navegável!")

    # 6. RN-01: Conversão para formato secundário .mobi
    print("\n[6/7] Testando conversão para formato .mobi (Mobipocket PalmDOC)...")
    mobi_res = execute_pdf_to_kindle(
        session_dir=session_dir,
        file_id=text_file_id,
        output_format="mobi",
        output_basename="meu_ebook_kindle",
    )
    assert mobi_res["format"] == "mobi"
    mobi_path = session_dir / "output" / "meu_ebook_kindle.mobi"
    assert mobi_path.exists()
    assert mobi_path.stat().st_size > 5000

    with open(mobi_path, "rb") as f_mobi:
        mobi_bytes = f_mobi.read()
        # Validação do Palm Database Header
        assert mobi_bytes[60:64] == b"BOOK"
        assert mobi_bytes[64:68] == b"MOBI"
        # Validação da presença do cabeçalho EXTH
        assert b"EXTH" in mobi_bytes
    print("  -> Formato MOBI gerado e validado com sucesso!")

    # 7. Teste de fila/polling assíncrono via API (/api/convert/pdf-to-kindle)
    print("\n[7/7] Testando fila assíncrona com polling de progresso (/api/convert/pdf-to-kindle)...")
    convert_req = {
        "session_id": session_id,
        "file_id": text_file_id,
        "output_format": "epub",
        "title": "E-book Teste Polling",
        "author": "Autor Teste",
        "output_filename": "ebook_polling_teste",
    }
    post_res = client.post("/api/convert/pdf-to-kindle", json=convert_req)
    assert post_res.status_code == 200
    job_info = post_res.json()
    assert job_info["success"] is True
    job_id = job_info["job_id"]
    assert job_id.startswith("kindle_")

    # Polling até conclusão
    max_wait = 15
    start_time = time.time()
    final_status = None
    while time.time() - start_time < max_wait:
        poll_res = client.get(f"/api/convert/pdf-to-kindle/status/{job_id}")
        assert poll_res.status_code == 200
        status_data = poll_res.json()
        if status_data["status"] == "completed":
            final_status = status_data
            break
        elif status_data["status"] == "error":
            raise RuntimeError(f"Job falhou: {status_data.get('error')}")
        time.sleep(0.3)

    assert final_status is not None, "Job assíncrono não concluiu dentro do tempo limite"
    assert final_status["progress"] == 100
    assert final_status["download_url"].startswith("/api/download/")
    assert final_status["output_filename"] == "ebook_polling_teste.epub"

    # Download do arquivo gerado
    dl_res = client.get(final_status["download_url"])
    assert dl_res.status_code == 200
    assert len(dl_res.content) > 5000
    print(f"  -> Job assíncrono {job_id} concluído com sucesso e download verificado!")

    # Limpeza
    client.delete(f"/api/session/{session_id}")
    print("\n==================================================")
    print("  PARABÉNS! TODOS OS TESTES KINDLE PASSARAM 100%! ")
    print("==================================================")


if __name__ == "__main__":
    run_kindle_tests()
