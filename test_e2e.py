"""
Teste de ponta a ponta (E2E) com validação de Menu de Documentos.
Valida:
1. Upload de múltiplos PDFs.
2. Geração da Página Inicial de Menu Visual com links clicáveis.
3. Criação dos marcadores (Outlines) com o nome de cada arquivo.
4. Configuração /PageMode /UseOutlines para abertura automática da barra de menu.
5. Download e Pré-visualização.
"""

import sys
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import pikepdf
import urllib.request
import urllib.parse
import json
import io

BASE_URL = "http://127.0.0.1:8000"


def create_test_pdf(filename: str, num_pages: int):
    doc = pikepdf.Pdf.new()
    for _ in range(num_pages):
        doc.add_blank_page(page_size=(595, 842))
    path = Path(filename)
    doc.save(path)
    return path


def run_e2e_test():
    print("[1/5] Criando PDFs de teste...")
    pdf1 = create_test_pdf("Doc_01_Contrato.pdf", 3)
    pdf2 = create_test_pdf("Doc_02_Balancete.pdf", 4)
    pdf3 = create_test_pdf("Doc_03_Anexo.pdf", 2)
    test_files = [pdf1, pdf2, pdf3]

    try:
        # 1. Upload
        print("[2/5] Enviando arquivos para a sessão...")
        boundary = "----WebKitFormBoundaryMenuTest998"
        body = io.BytesIO()
        session_id = "test_menu_e2e_sess"

        body.write(f"--{boundary}\r\n".encode())
        body.write(f'Content-Disposition: form-data; name="session_id"\r\n\r\n{session_id}\r\n'.encode())

        for pf in test_files:
            content = pf.read_bytes()
            body.write(f"--{boundary}\r\n".encode())
            body.write(f'Content-Disposition: form-data; name="files"; filename="{pf.name}"\r\n'.encode())
            body.write(b"Content-Type: application/pdf\r\n\r\n")
            body.write(content)
            body.write(b"\r\n")
        body.write(f"--{boundary}--\r\n".encode())

        req = urllib.request.Request(
            f"{BASE_URL}/api/upload",
            data=body.getvalue(),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST"
        )

        with urllib.request.urlopen(req) as resp:
            upload_data = json.loads(resp.read().decode())

        assert upload_data["success"] is True
        print(f"  -> {len(upload_data['files'])} arquivos salvos no servidor.")

        # 2. Merge com Menu de Documentos
        print("[3/5] Processando fusão com Menu de Documentos e Marcadores...")
        file_order = [
            {"id": upload_data["files"][0]["saved_filename"], "menu_title": "1. Contrato Social"},
            {"id": upload_data["files"][1]["saved_filename"], "menu_title": "2. Balancete Financeiro"},
            {"id": upload_data["files"][2]["saved_filename"], "menu_title": "3. Anexo e Relatório Técnico"}
        ]

        merge_payload = {
            "session_id": session_id,
            "file_order": file_order,
            "output_filename": "dossie_com_menu.pdf",
            "create_visual_menu": True,
            "add_bookmarks": True,
            "linearize": True
        }

        req = urllib.request.Request(
            f"{BASE_URL}/api/merge",
            data=json.dumps(merge_payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req) as resp:
            merge_data = json.loads(resp.read().decode())

        assert merge_data["success"] is True
        metrics = merge_data["metrics"]
        # 3 + 4 + 2 páginas originais = 9 + 1 página de menu visual = 10 páginas
        assert metrics["total_pages"] == 10, f"Total de páginas incorreto: {metrics['total_pages']}"
        print(f"  -> Unificação concluída em {metrics['duration_seconds']}s")
        print(f"  -> Total de páginas (com menu): {metrics['total_pages']}")

        # 3. Baixa e inspeciona o PDF resultante
        print("[4/5] Inspecionando estrutura do PDF resultante...")
        dl_url = f"{BASE_URL}{merge_data['download_url']}"
        with urllib.request.urlopen(dl_url) as resp:
            pdf_bytes = resp.read()

        # Abre o PDF com pikepdf para inspecionar os marcadores e PageMode
        with pikepdf.open(io.BytesIO(pdf_bytes)) as result_pdf:
            # Verifica PageMode /UseOutlines
            assert "/PageMode" in result_pdf.Root
            assert str(result_pdf.Root.PageMode) == "/UseOutlines"
            print("  [OK] /PageMode /UseOutlines está configurado para abertura automática da barra lateral.")

            # Verifica Outlines
            with result_pdf.open_outline() as outline:
                item_titles = [item.title for item in outline.root]
                print(f"  [OK] Marcadores encontrados no menu: {item_titles}")
                assert "1. Contrato Social" in item_titles
                assert "2. Balancete Financeiro" in item_titles
                assert "3. Anexo e Relatório Técnico" in item_titles

            # Verifica anotações de link na página 0 (Menu Visual)
            page_0 = result_pdf.pages[0]
            assert "/Annots" in page_0
            annots = page_0.Annots
            assert len(annots) == 3, f"Esperado 3 links no menu, encontrados {len(annots)}"
            print(f"  [OK] Página inicial contém {len(annots)} links clicáveis para cada documento!")

        # 4. Limpeza
        print("[5/5] Limpando sessão...")
        del_req = urllib.request.Request(f"{BASE_URL}/api/session/{session_id}", method="DELETE")
        with urllib.request.urlopen(del_req) as resp:
            assert json.loads(resp.read().decode())["success"] is True

        print("\n=======================================================")
        print("  TODOS OS TESTES DO MENU FORAM APROVADOS COM SUCESSO! ")
        print("=======================================================")

    finally:
        for pf in test_files:
            if pf.exists():
                pf.unlink()


if __name__ == "__main__":
    run_e2e_test()
