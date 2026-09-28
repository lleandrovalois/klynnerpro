"""
Suite de testes automatizados para todas as funcionalidades do Klynner PDF PRO:
- Juntar PDF (Merge com Menu de Documentos e Marcadores)
- Dividir PDF (Split por faixas e páginas avulsas Burst)
- Organizar Páginas (Reorder, duplicar, excluir e rotação)
- Girar Páginas (Individual e lote 90°, 180°, 270°)
- Extrair Páginas (PDF único e ZIP avulso)
- Download e Pré-visualização
"""

import io
from pathlib import Path
import zipfile

import pikepdf
from starlette.testclient import TestClient

from app.main import app


def create_sample_pdf(num_pages: int = 5) -> io.BytesIO:
    doc = pikepdf.Pdf.new()
    for _ in range(num_pages):
        doc.add_blank_page(page_size=(595, 842))
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


def run_tests():
    client = TestClient(app)
    session_id = "test_suite_session_123"

    print("==================================================")
    print("  TESTANDO TODAS AS FUNCIONALIDADES DO KLYNNER PRO")
    print("==================================================")

    # 1. Página Inicial e HTML
    print("\n[1/10] Testando GET / (Template index.html e componentes)...")
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    assert "tools-nav-bar" in html
    assert "stage-merge" in html
    assert "stage-split" in html
    assert "stage-organize" in html
    assert "stage-rotate" in html
    assert "stage-extract" in html
    print("  -> Template index.html carregado com os 5 estágios e menu de navegação!")

    # 2. Health Check
    print("\n[2/10] Testando GET /api/health...")
    res = client.get("/api/health")
    assert res.status_code == 200
    health = res.json()
    assert len(health["features"]) == 5
    print("  -> Health check OK: 5 ferramentas ativas.")

    # 3. Upload de Arquivos
    print("\n[3/10] Testando POST /api/upload (Streaming e metadados)...")
    pdf1_data = create_sample_pdf(3)
    pdf2_data = create_sample_pdf(4)

    files = [
        ("files", ("Doc_Alpha.pdf", pdf1_data, "application/pdf")),
        ("files", ("Doc_Beta.pdf", pdf2_data, "application/pdf")),
    ]
    res = client.post("/api/upload", data={"session_id": session_id}, files=files)
    assert res.status_code == 200
    up_json = res.json()
    assert up_json["success"] is True
    assert len(up_json["files"]) == 2
    saved_alpha = up_json["files"][0]["saved_filename"]
    saved_beta = up_json["files"][1]["saved_filename"]
    print(f"  -> Upload OK: {saved_alpha} ({up_json['files'][0]['page_count']} pags), {saved_beta} ({up_json['files'][1]['page_count']} pags)")

    # 4. Juntar PDF (Merge)
    print("\n[4/10] Testando POST /api/merge (Menu de Documentos e Marcadores)...")
    merge_payload = {
        "session_id": session_id,
        "file_order": [
            {"id": saved_alpha, "menu_title": "Documento Alpha"},
            {"id": saved_beta, "menu_title": "Documento Beta"},
        ],
        "output_filename": "dossie_unificado.pdf",
        "create_visual_menu": True,
        "add_bookmarks": True,
        "linearize": True,
    }
    res = client.post("/api/merge", json=merge_payload)
    assert res.status_code == 200
    merge_json = res.json()
    assert merge_json["success"] is True
    assert merge_json["metrics"]["total_files"] == 2
    # 1 pág de menu visual + 3 pags alpha + 4 pags beta = 8 páginas
    assert merge_json["metrics"]["total_pages"] == 8
    print(f"  -> Merge OK: {merge_json['output_filename']} ({merge_json['metrics']['total_pages']} páginas geradas)")

    # 5. Dividir PDF (Split por Intervalos)
    print("\n[5/10] Testando POST /api/split (Modo Intervalos)...")
    split_payload = {
        "session_id": session_id,
        "file_id": saved_beta, # 4 páginas
        "mode": "ranges",
        "range_input": "1-2, 3-4",
        "output_filename": "beta_dividido",
        "linearize": True,
    }
    res = client.post("/api/split", json=split_payload)
    assert res.status_code == 200
    split_json = res.json()
    assert split_json["is_zip"] is True
    assert split_json["metrics"]["files_generated"] == 2
    print(f"  -> Split Intervalos OK: {split_json['output_filename']} ({split_json['metrics']['files_generated']} arquivos ZIP)")

    # 6. Dividir PDF (Split Modo Burst / All Pages)
    print("\n[6/10] Testando POST /api/split (Modo Burst / Avulsas)...")
    split_burst_payload = {
        "session_id": session_id,
        "file_id": saved_alpha, # 3 páginas
        "mode": "all_pages",
        "output_filename": "alpha_burst",
        "linearize": True,
    }
    res = client.post("/api/split", json=split_burst_payload)
    assert res.status_code == 200
    burst_json = res.json()
    assert burst_json["is_zip"] is True
    assert burst_json["metrics"]["files_generated"] == 3
    print(f"  -> Split Burst OK: {burst_json['output_filename']} (3 arquivos avulsos)")

    # 7. Organizar e Reordenar Páginas
    print("\n[7/10] Testando POST /api/organize (Reordenação, Duplicação e Rotação)...")
    organize_payload = {
        "session_id": session_id,
        "file_id": saved_beta, # Original tem 4 páginas (1, 2, 3, 4)
        "page_actions": [
            {"page": 3, "rotation": 0},   # Posição 1: pág 3
            {"page": 1, "rotation": 90},  # Posição 2: pág 1 girada 90°
            {"page": 1, "rotation": 90},  # Posição 3: pág 1 duplicada
            {"page": 4, "rotation": 180}, # Posição 4: pág 4 girada 180°
            # Pág 2 foi excluída!
        ],
        "output_filename": "beta_reorganizado.pdf",
        "linearize": True,
    }
    res = client.post("/api/organize", json=organize_payload)
    assert res.status_code == 200
    org_json = res.json()
    assert org_json["metrics"]["final_pages"] == 4
    print(f"  -> Organize OK: {org_json['output_filename']} ({org_json['metrics']['final_pages']} páginas reordenadas/duplicadas)")

    # 8. Girar Páginas
    print("\n[8/10] Testando POST /api/rotate (Rotação em lote e individual)...")
    rotate_payload = {
        "session_id": session_id,
        "file_id": saved_alpha, # 3 páginas
        "page_rotations": {
            "1": 90,
            "2": 180,
            "3": 270,
        },
        "output_filename": "alpha_rotacionado.pdf",
        "linearize": True,
    }
    res = client.post("/api/rotate", json=rotate_payload)
    assert res.status_code == 200
    rot_json = res.json()
    assert rot_json["metrics"]["pages_rotated"] == 3
    print(f"  -> Rotate OK: {rot_json['output_filename']} ({rot_json['metrics']['pages_rotated']} páginas rotacionadas)")

    # 9. Extrair Páginas (PDF único e ZIP)
    print("\n[9/10] Testando POST /api/extract (Modo Merge e Modo Split)...")
    extract_merge_payload = {
        "session_id": session_id,
        "file_id": saved_beta,
        "selected_pages": [1, 4],
        "mode": "merge",
        "output_filename": "beta_extraido_enxuto",
        "linearize": True,
    }
    res = client.post("/api/extract", json=extract_merge_payload)
    assert res.status_code == 200
    ext_m_json = res.json()
    assert ext_m_json["is_zip"] is False
    assert ext_m_json["metrics"]["extracted_pages_count"] == 2
    print(f"  -> Extract Merge OK: {ext_m_json['output_filename']} (PDF único com 2 páginas)")

    extract_split_payload = {
        "session_id": session_id,
        "file_id": saved_beta,
        "selected_pages": [2, 3],
        "mode": "split",
        "output_filename": "beta_extraido_avulso",
        "linearize": True,
    }
    res = client.post("/api/extract", json=extract_split_payload)
    assert res.status_code == 200
    ext_s_json = res.json()
    assert ext_s_json["is_zip"] is True
    assert ext_s_json["metrics"]["files_count"] == 2
    print(f"  -> Extract Split OK: {ext_s_json['output_filename']} (ZIP com páginas avulsas)")

    # 10. Download e Pré-visualização de Arquivos
    print("\n[10/10] Testando GET /api/download e /api/preview...")
    # Download do PDF
    dl_pdf = client.get(f"/api/download/{session_id}?filename=dossie_unificado.pdf")
    assert dl_pdf.status_code == 200
    assert dl_pdf.headers["content-type"] == "application/pdf"
    assert len(dl_pdf.content) > 1000

    # Download do ZIP
    dl_zip = client.get(f"/api/download/{session_id}?filename=beta_dividido_dividido.zip")
    assert dl_zip.status_code == 200
    assert "zip" in dl_zip.headers["content-type"].lower()
    with zipfile.ZipFile(io.BytesIO(dl_zip.content)) as zf:
        assert len(zf.namelist()) == 2

    # Preview do PDF
    prev_pdf = client.get(f"/api/preview/{session_id}?filename=dossie_unificado.pdf")
    assert prev_pdf.status_code == 200
    assert prev_pdf.headers["content-type"] == "application/pdf"

    # Preview do ZIP (deve retornar 400 informativo)
    prev_zip = client.get(f"/api/preview/{session_id}?filename=beta_dividido_dividido.zip")
    assert prev_zip.status_code == 400
    print("  -> Download de PDF e ZIP verificado com integridade binária!")
    print("  -> Pré-visualização inline validada!")

    # Limpeza da sessão de teste
    del_res = client.delete(f"/api/session/{session_id}")
    assert del_res.status_code == 200
    print("\n==================================================")
    print("  PARABÉNS! TODOS OS 10 TESTES PASSARAM COM 100%!")
    print("==================================================")


if __name__ == "__main__":
    run_tests()
