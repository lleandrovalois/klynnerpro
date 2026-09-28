"""
Motor de extração de páginas de PDF.
Gera um novo documento contendo exclusivamente as páginas selecionadas pelo usuário,
com opção de unir em PDF único ou exportar em arquivos avulsos (ZIP).
"""

import logging
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional
import zipfile

import pikepdf

logger = logging.getLogger("pdf_extractor")


def execute_pdf_extract(
    input_pdf_path: Path,
    session_dir: Path,
    selected_pages: List[int],
    mode: str = "merge",  # "merge" (1 PDF único) | "split" (ZIP com arquivos separados)
    output_basename: Optional[str] = None,
    linearize: bool = True,
) -> Dict[str, Any]:
    """
    Extrai páginas selecionadas de um PDF.
    - selected_pages: lista de inteiros 1-based (ex: [1, 3, 4, 7])
    - mode: "merge" para gerar um único PDF ou "split" para ZIP com cada página separada.
    """
    start_time = time.time()
    out_dir = session_dir / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    base_name = output_basename or input_pdf_path.stem or "paginas_extraidas"
    base_name = re.sub(r"\.(pdf|zip)$", "", base_name, flags=re.IGNORECASE)

    if not selected_pages:
        raise ValueError("Nenhuma página foi selecionada para extração.")

    with pikepdf.open(input_pdf_path) as source_pdf:
        total_source_pages = len(source_pdf.pages)
        if total_source_pages == 0:
            raise ValueError("O arquivo PDF de origem está vazio.")

        # Valida páginas únicas e dentro dos limites válidos, preservando a ordem solicitada
        valid_pages: List[int] = []
        for p in selected_pages:
            if 1 <= p <= total_source_pages and p not in valid_pages:
                valid_pages.append(p)

        if not valid_pages:
            raise ValueError(f"Nenhuma página selecionada é válida (o arquivo possui {total_source_pages} páginas).")

        if mode == "merge":
            new_pdf = pikepdf.Pdf.new()
            for p_num in valid_pages:
                new_pdf.pages.append(source_pdf.pages[p_num - 1])

            out_filename = f"{base_name}.pdf"
            output_file = out_dir / out_filename
            new_pdf.save(output_file, linearize=linearize)
            is_zip = False
            files_count = 1
            output_bytes = output_file.stat().st_size

        elif mode == "split":
            temp_extract_dir = session_dir / "extracted_parts"
            if temp_extract_dir.exists():
                import shutil
                shutil.rmtree(temp_extract_dir, ignore_errors=True)
            temp_extract_dir.mkdir(parents=True, exist_ok=True)

            part_files: List[Path] = []
            digit_count = max(2, len(str(total_source_pages)))

            for p_num in valid_pages:
                part_pdf = pikepdf.Pdf.new()
                part_pdf.pages.append(source_pdf.pages[p_num - 1])
                part_name = f"{base_name}_pag_{p_num:0{digit_count}d}.pdf"
                part_path = temp_extract_dir / part_name
                part_pdf.save(part_path, linearize=linearize)
                part_files.append(part_path)

            out_filename = f"{base_name}_extraidas.zip"
            output_file = out_dir / out_filename

            with zipfile.ZipFile(output_file, "w", compression=zipfile.ZIP_DEFLATED) as zip_out:
                for pf in part_files:
                    zip_out.write(pf, arcname=pf.name)

            is_zip = True
            files_count = len(part_files)
            output_bytes = output_file.stat().st_size

        else:
            raise ValueError(f"Modo de extração desconhecido: '{mode}'")

    duration = round(time.time() - start_time, 2)

    return {
        "success": True,
        "total_source_pages": total_source_pages,
        "extracted_pages_count": len(valid_pages),
        "files_count": files_count,
        "output_filename": out_filename,
        "output_path": str(output_file),
        "output_bytes": output_bytes,
        "duration_seconds": duration,
        "is_zip": is_zip,
    }
