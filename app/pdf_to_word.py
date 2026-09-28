"""
Módulo de Conversão de PDF para Microsoft Word (.docx)
Utiliza a biblioteca pdf2docx (PyMuPDF + python-docx) para reconstrução inteligente
de layout, parágrafos, tabelas, imagens e fontes editáveis.
"""

import logging
from pathlib import Path
import time
from typing import Any, Dict, Optional

from pdf2docx import Converter

logger = logging.getLogger("pdf_to_word")


def execute_pdf_to_word(
    session_dir: Path,
    file_id: str,
    output_basename: Optional[str] = None,
    start_page: Optional[int] = None,
    end_page: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Converte um documento PDF em arquivo Microsoft Word (.docx) editável.
    
    Args:
        session_dir: Diretório temporário da sessão
        file_id: Identificador do arquivo PDF no workspace da sessão
        output_basename: Nome base para o arquivo .docx gerado
        start_page: Página inicial (1-based, opcional)
        end_page: Página final (1-based, opcional)
    """
    t0 = time.time()
    input_path = session_dir / Path(file_id).name
    if not input_path.exists():
        input_path = session_dir / "output" / Path(file_id).name
    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo de origem '{file_id}' não encontrado na sessão.")

    clean_stem = (output_basename or input_path.stem).strip()
    clean_stem = Path(clean_stem).stem
    out_filename = f"{clean_stem}.docx"

    output_dir = session_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / out_filename

    # Descobre o total de páginas do PDF de entrada
    import pikepdf
    with pikepdf.open(input_path) as p_doc:
        total_input_pages = len(p_doc.pages)

    # Converte páginas selecionadas ou todas
    cv = Converter(str(input_path))
    try:
        # pdf2docx usa 0-based indexing para start e end
        s_page = (start_page - 1) if (start_page and start_page > 0) else 0
        e_page = end_page if (end_page and end_page > 0) else None

        cv.convert(str(out_path), start=s_page, end=e_page)
        
        effective_start = s_page
        effective_end = e_page if e_page is not None else total_input_pages
        converted_count = max(1, min(effective_end, total_input_pages) - effective_start)
    finally:
        cv.close()

    elapsed = time.time() - t0
    filesize = out_path.stat().st_size

    logger.info(
        f"PDF convertido para Word com sucesso: '{out_filename}', "
        f"{filesize} bytes em {elapsed:.2f}s"
    )

    return {
        "output_filename": out_filename,
        "filesize": filesize,
        "output_bytes": filesize,
        "pages_converted": converted_count,
        "total_pages": converted_count,
        "is_docx": True,
        "format": "docx",
        "time_seconds": round(elapsed, 3),
        "duration_seconds": round(elapsed, 3),
    }
