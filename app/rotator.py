"""
Motor de rotação de páginas de arquivos PDF.
Permite rotação individual por página ou rotação em lote (90°, 180°, 270°)
com preservação de metadados e linearização (Fast Web View).
"""

import logging
from pathlib import Path
import time
from typing import Any, Dict, Optional, Union

import pikepdf

logger = logging.getLogger("pdf_rotator")


def execute_pdf_rotate(
    input_pdf_path: Path,
    output_pdf_path: Path,
    page_rotations: Optional[Dict[Union[str, int], int]] = None,
    default_rotation: int = 0,
    linearize: bool = True,
) -> Dict[str, Any]:
    """
    Aplica rotação nas páginas de um PDF.

    - page_rotations: dicionário mapeando número de página (1-based, ex: "1", 2) -> graus adicionais (90, 180, 270).
    - default_rotation: rotação base aplicada a páginas que não estejam especificadas individualmente.
    """
    start_time = time.time()
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    rot_map = {}
    if page_rotations:
        for k, v in page_rotations.items():
            try:
                rot_map[int(k)] = int(v) % 360
            except (ValueError, TypeError):
                continue

    rotated_count = 0

    with pikepdf.open(input_pdf_path) as pdf:
        total_pages = len(pdf.pages)
        if total_pages == 0:
            raise ValueError("O arquivo PDF não contém nenhuma página.")

        for i, page in enumerate(pdf.pages):
            page_num = i + 1
            angle = rot_map.get(page_num, default_rotation % 360)

            if angle != 0:
                current_rot = int(page.get("/Rotate", 0) or 0)
                page.Rotate = (current_rot + angle) % 360
                rotated_count += 1

        pdf.save(output_pdf_path, linearize=linearize)

    duration = round(time.time() - start_time, 2)
    output_bytes = output_pdf_path.stat().st_size

    return {
        "success": True,
        "total_pages": total_pages,
        "pages_rotated": rotated_count,
        "output_filename": output_pdf_path.name,
        "output_path": str(output_pdf_path),
        "output_bytes": output_bytes,
        "duration_seconds": duration,
    }
