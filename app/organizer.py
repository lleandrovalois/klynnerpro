"""
Motor de organização e reordenação de páginas de PDF.
Suporta:
- Reordenação arbitrária de páginas.
- Duplicação de páginas específicas.
- Exclusão de páginas indesejadas.
- Rotação individual por página integrada à reorganização.
"""

import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

import pikepdf

logger = logging.getLogger("pdf_organizer")


def execute_pdf_organize(
    input_pdf_path: Path,
    output_pdf_path: Path,
    page_actions: List[Dict[str, Any]],
    linearize: bool = True,
) -> Dict[str, Any]:
    """
    Executa a reordenação, duplicação e exclusão de páginas de um PDF.

    page_actions é uma lista de dicionários no formato:
    [
        {"page": 1, "rotation": 0},
        {"page": 3, "rotation": 90},
        {"page": 3, "rotation": 90},  # Duplicada
        ...
    ]
    Onde 'page' é o índice 1-based da página original.
    """
    start_time = time.time()
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    if not page_actions:
        raise ValueError("A lista de páginas para o novo documento não pode estar vazia.")

    with pikepdf.open(input_pdf_path) as source_pdf:
        total_source_pages = len(source_pdf.pages)
        if total_source_pages == 0:
            raise ValueError("O documento PDF original não possui páginas.")

        new_pdf = pikepdf.Pdf.new()

        for item in page_actions:
            orig_page_num = int(item.get("page", 1))
            rot_delta = int(item.get("rotation", 0))

            if not (1 <= orig_page_num <= total_source_pages):
                logger.warning(f"Página {orig_page_num} fora dos limites (1..{total_source_pages}), ignorando.")
                continue

            page_idx = orig_page_num - 1
            # Importa a página para o novo PDF
            new_pdf.pages.append(source_pdf.pages[page_idx])
            last_added_page = new_pdf.pages[-1]

            if rot_delta != 0:
                current_rot = int(last_added_page.get("/Rotate", 0) or 0)
                last_added_page.Rotate = (current_rot + rot_delta) % 360

        if len(new_pdf.pages) == 0:
            raise ValueError("Nenhuma página válida foi incluída no documento final.")

        new_pdf.save(output_pdf_path, linearize=linearize)

    duration = round(time.time() - start_time, 2)
    output_bytes = output_pdf_path.stat().st_size

    return {
        "success": True,
        "total_source_pages": total_source_pages,
        "final_pages": len(page_actions),
        "output_filename": output_pdf_path.name,
        "output_path": str(output_pdf_path),
        "output_bytes": output_bytes,
        "duration_seconds": duration,
    }
