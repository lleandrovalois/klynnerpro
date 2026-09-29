"""
Módulo de Personalização de Rodapé e Cabeçalho / Numeração de Páginas.
Utiliza PyMuPDF (fitz) para carimbo vetorial de texto de alta fidelidade
e PikePDF para otimização e linearização (Fast Web View).
"""

from datetime import datetime
import logging
from pathlib import Path
import time
from typing import Any, Dict, Optional

import fitz  # PyMuPDF
import pikepdf

logger = logging.getLogger("footer_customizer")


def parse_hex_color(hex_str: str) -> tuple[float, float, float]:
    """Converte código hex (#RRGGBB) para tupla RGB normalizada (0.0 a 1.0)."""
    clean = hex_str.strip().lstrip("#")
    if len(clean) == 6:
        try:
            r = int(clean[0:2], 16) / 255.0
            g = int(clean[2:4], 16) / 255.0
            b = int(clean[4:6], 16) / 255.0
            return (r, g, b)
        except ValueError:
            pass
    return (0.392, 0.455, 0.545)  # #64748B (Slate padrão discreto)


def execute_pdf_footer(
    session_dir: Path,
    file_id: str,
    footer_text: str = "{page}",
    position: str = "footer",  # "footer" (inferior) ou "header" (superior)
    alignment: str = "center",  # "left", "center", "right"
    font_size: float = 9.0,
    font_color: str = "#64748B",
    skip_first_page: bool = False,
    page_start_number: int = 1,
    margin_offset: float = 25.0,
    margin_sides: float = 36.0,
    output_basename: Optional[str] = None,
    linearize: bool = True,
) -> Dict[str, Any]:
    """
    Insere rodapé, cabeçalho e/ou numeração de páginas personalizada em um documento PDF.
    
    Args:
        session_dir: Diretório de trabalho da sessão
        file_id: Nome do arquivo no diretório da sessão
        footer_text: Texto do rodapé com suporte a tags: {page}, {total}, {date}, {file}
        position: 'footer' para parte inferior ou 'header' para parte superior
        alignment: 'left', 'center' ou 'right'
        font_size: Tamanho da fonte em pontos
        font_color: Cor em formato hexadecimal (#RRGGBB)
        skip_first_page: Pula a primeira página (útil para capa)
        page_start_number: Número inicial para a contagem
        margin_offset: Distância em pontos da borda superior ou inferior
        margin_sides: Margem lateral em pontos
        output_basename: Nome base para o arquivo resultante
        linearize: Ativa Fast Web View
    """
    t0 = time.time()
    input_path = session_dir / Path(file_id).name
    if not input_path.exists():
        input_path = session_dir / "output" / Path(file_id).name
    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo de origem '{file_id}' não encontrado na sessão.")

    clean_stem = (output_basename or input_path.stem).strip()
    clean_stem = Path(clean_stem).stem
    if not clean_stem.endswith("_com_rodape") and not clean_stem.endswith("_numerado"):
        out_filename = f"{clean_stem}_com_rodape.pdf"
    else:
        out_filename = f"{clean_stem}.pdf"

    output_dir = session_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / out_filename
    temp_path = output_dir / f"tmp_{out_filename}"

    doc = fitz.open(str(input_path))
    total_pages = len(doc)
    today_str = datetime.now().strftime("%d/%m/%Y")
    doc_name = input_path.stem

    rgb_color = parse_hex_color(font_color)
    align_map = {"left": 0, "center": 1, "right": 2}
    align_code = align_map.get(alignment.lower(), 1)
    is_header = position.lower() == "header"

    pages_applied = 0
    safe_font_size = max(6.0, min(float(font_size), 24.0))

    try:
        for idx in range(total_pages):
            page_num_1based = idx + 1
            if skip_first_page and page_num_1based == 1:
                continue

            page = doc[idx]
            page_w = page.rect.width
            page_h = page.rect.height

            # Calcula número dinâmico da página
            counter_val = page_start_number + (idx - 1 if skip_first_page else idx)

            # Interpolação das tags dinâmicas
            rendered = (
                footer_text
                .replace("{page}", str(counter_val))
                .replace("{p}", str(counter_val))
                .replace("{total}", str(total_pages))
                .replace("{pages}", str(total_pages))
                .replace("{date}", today_str)
                .replace("{data}", today_str)
                .replace("{file}", doc_name)
                .replace("{doc}", doc_name)
            )

            # Define o retângulo onde o texto será encaixado
            box_height = safe_font_size * 2.2
            if is_header:
                box_y1 = margin_offset
                box_y2 = margin_offset + box_height
            else:
                box_y2 = page_h - margin_offset
                box_y1 = page_h - margin_offset - box_height

            rect = fitz.Rect(margin_sides, box_y1, page_w - margin_sides, box_y2)

            page.insert_textbox(
                rect,
                rendered,
                fontsize=safe_font_size,
                fontname="helv",
                color=rgb_color,
                align=align_code,
            )
            pages_applied += 1

        doc.save(str(temp_path))
    finally:
        doc.close()

    # Otimiza e lineariza via PikePDF para Fast Web View
    with pikepdf.open(temp_path) as pdoc:
        pdoc.save(str(out_path), linearize=linearize)
    temp_path.unlink(missing_ok=True)

    elapsed = time.time() - t0
    filesize = out_path.stat().st_size

    logger.info(
        f"Rodapé aplicado com sucesso: '{out_filename}', {pages_applied}/{total_pages} páginas, "
        f"{filesize} bytes em {elapsed:.2f}s"
    )

    return {
        "output_filename": out_filename,
        "filesize": filesize,
        "output_bytes": filesize,
        "pages": total_pages,
        "total_pages": total_pages,
        "pages_applied": pages_applied,
        "position": position,
        "alignment": alignment,
        "footer_text": footer_text,
        "linearized": linearize,
        "time_seconds": round(elapsed, 3),
        "duration_seconds": round(elapsed, 3),
    }
