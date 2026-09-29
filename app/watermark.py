"""
Motor de aplicação de marcas d'água (texto e imagem) em arquivos PDF.
Suporta rotação, opacidade, repetição em mosaico (tiling), cores personalizadas,
seleção de páginas e posicionamento em frente (overlay) ou fundo (underlay).
"""

import io
import logging
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional, Set

from PIL import Image, ImageOps
import pikepdf
import pypdf
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

logger = logging.getLogger("pdf_watermark")


def parse_page_range(range_str: str, total_pages: int) -> Set[int]:
    """
    Interpreta strings de intervalos como '1-3, 5, 8-10' em um conjunto de páginas (1-based).
    Se for 'all', retorna todas as páginas. Se for 'first', retorna apenas a página 1.
    """
    clean_str = (range_str or "all").strip().lower()
    if clean_str in ("all", "todas", "*"):
        return set(range(1, total_pages + 1))
    if clean_str in ("first", "primeira", "1"):
        return {1} if total_pages >= 1 else set()

    pages: Set[int] = set()
    parts = clean_str.split(",")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            sub = part.split("-")
            if len(sub) == 2:
                try:
                    start = max(1, int(sub[0].strip()))
                    end = min(total_pages, int(sub[1].strip()))
                    if start <= end:
                        pages.update(range(start, end + 1))
                except ValueError:
                    continue
        else:
            try:
                p = int(part)
                if 1 <= p <= total_pages:
                    pages.add(p)
            except ValueError:
                continue

    return pages if pages else set(range(1, total_pages + 1))


def _generate_watermark_page_bytes(
    page_w: float,
    page_h: float,
    watermark_type: str,
    text: str,
    font_size: int,
    font_color: str,
    opacity: float,
    rotation: int,
    position: str,
    watermark_image_path: Optional[Path],
    image_scale: float,
) -> bytes:
    """Gera um PDF em memória de página única com o conteúdo da marca d'água nas dimensões exatas da página alvo."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(page_w, page_h))

    # Normalização de opacidade (0.01 a 1.0)
    op = max(0.01, min(1.0, float(opacity)))

    # Normalização de cor hex
    if not font_color.startswith("#"):
        font_color = f"#{font_color}"
    if len(font_color) not in (4, 7):
        font_color = "#DC2626"

    try:
        color_obj = HexColor(font_color)
    except Exception:
        color_obj = HexColor("#DC2626")

    cx = page_w / 2.0
    cy = page_h / 2.0

    if position == "top":
        target_y = page_h - max(50.0, float(font_size) * 1.5)
    elif position == "bottom":
        target_y = max(50.0, float(font_size) * 1.5)
    else:  # "center" ou "tile"
        target_y = cy

    if watermark_type == "text":
        c.setFillColor(color_obj, alpha=op)
        c.setStrokeColor(color_obj, alpha=op)
        c.setFont("Helvetica-Bold", font_size)

        if position == "tile":
            # Padrão repetido em grade (mosaico) cobrindo a página inteira
            step_x = max(180.0, float(font_size) * len(text) * 0.65 + 60.0)
            step_y = max(120.0, float(font_size) * 3.0 + 60.0)

            c.saveState()
            c.translate(cx, cy)
            c.rotate(rotation)

            diag = (page_w**2 + page_h**2) ** 0.5
            start_x = -diag
            end_x = diag
            start_y = -diag
            end_y = diag

            curr_y = start_y
            row = 0
            while curr_y <= end_y:
                offset_x = (step_x / 2.0) if (row % 2 == 1) else 0.0
                curr_x = start_x + offset_x
                while curr_x <= end_x:
                    c.drawCentredString(curr_x, curr_y - (font_size / 3.0), text)
                    curr_x += step_x
                curr_y += step_y
                row += 1

            c.restoreState()
        else:
            # Posição única (centro, topo ou rodapé)
            c.saveState()
            c.translate(cx, target_y)
            c.rotate(rotation)
            c.drawCentredString(0, -font_size / 3.0, text)
            c.restoreState()

    elif watermark_type == "image" and watermark_image_path and watermark_image_path.exists():
        try:
            with Image.open(watermark_image_path) as raw_img:
                raw_img = ImageOps.exif_transpose(raw_img)
                img = raw_img.convert("RGBA")

                # Aplica opacidade diretamente no canal alfa da imagem
                r, g, b, a = img.split()
                adjusted_a = a.point(lambda p: int(p * op))
                img.putalpha(adjusted_a)

                orig_w, orig_h = img.size
                max_dim = min(page_w, page_h) * max(0.1, min(1.0, image_scale))
                scale = min(max_dim / orig_w, max_dim / orig_h)
                draw_w = orig_w * scale
                draw_h = orig_h * scale

                img_buf = io.BytesIO()
                img.save(img_buf, format="PNG")
                img_buf.seek(0)
                reader = ImageReader(img_buf)

                if position == "tile":
                    step_x = max(160.0, draw_w + 60.0)
                    step_y = max(120.0, draw_h + 60.0)

                    c.saveState()
                    c.translate(cx, cy)
                    c.rotate(rotation)

                    diag = (page_w**2 + page_h**2) ** 0.5
                    start_x = -diag
                    end_x = diag
                    start_y = -diag
                    end_y = diag

                    curr_y = start_y
                    row = 0
                    while curr_y <= end_y:
                        offset_x = (step_x / 2.0) if (row % 2 == 1) else 0.0
                        curr_x = start_x + offset_x
                        while curr_x <= end_x:
                            c.drawImage(
                                reader,
                                curr_x - draw_w / 2.0,
                                curr_y - draw_h / 2.0,
                                width=draw_w,
                                height=draw_h,
                                mask="auto",
                            )
                            curr_x += step_x
                        curr_y += step_y
                        row += 1

                    c.restoreState()
                else:
                    c.saveState()
                    c.translate(cx, target_y)
                    c.rotate(rotation)
                    c.drawImage(
                        reader,
                        -draw_w / 2.0,
                        -draw_h / 2.0,
                        width=draw_w,
                        height=draw_h,
                        mask="auto",
                    )
                    c.restoreState()
        except Exception as img_err:
            logger.error(f"Erro ao desenhar imagem da marca d'água: {img_err}", exc_info=True)
            raise ValueError(f"Falha ao processar imagem de marca d'água: {str(img_err)}")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


def execute_pdf_watermark(
    input_pdf_path: Path,
    output_pdf_path: Path,
    watermark_type: str = "text",
    text: Optional[str] = "CONFIDENCIAL",
    font_size: int = 48,
    font_color: str = "#DC2626",
    opacity: float = 0.25,
    rotation: int = -45,
    position: str = "center",
    watermark_image_path: Optional[Path] = None,
    image_scale: float = 0.5,
    layer: str = "overlay",
    pages: str = "all",
    linearize: bool = True,
) -> Dict[str, Any]:
    """
    Aplica marca d'água (texto ou imagem) em um arquivo PDF existente.
    
    - input_pdf_path: caminho do PDF de entrada
    - output_pdf_path: caminho do PDF de saída
    - watermark_type: 'text' ou 'image'
    - text: texto da marca d'água
    - font_size: tamanho da fonte em pt (12 a 120)
    - font_color: código hexadecimal da cor (ex: '#DC2626')
    - opacity: nível de transparência (0.05 a 1.0)
    - rotation: rotação em graus (-45, 0, 45, 90)
    - position: 'center', 'top', 'bottom', ou 'tile' (mosaico em toda a página)
    - watermark_image_path: caminho da imagem caso watermark_type == 'image'
    - image_scale: escala proporcional da imagem (0.1 a 1.0)
    - layer: 'overlay' (sobreposto ao conteúdo) ou 'underlay' (abaixo do conteúdo/fundo)
    - pages: 'all', 'first', ou intervalos numéricos (ex: '1-3, 5')
    - linearize: otimização Fast Web View via PikePDF
    """
    start_time = time.time()
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_pdf_path.exists():
        raise FileNotFoundError(f"Arquivo de entrada não encontrado: {input_pdf_path}")

    text_to_use = (text or "CONFIDENCIAL").strip()
    is_overlay = layer.lower() != "underlay"

    reader = pypdf.PdfReader(str(input_pdf_path))
    writer = pypdf.PdfWriter()

    total_pages = len(reader.pages)
    if total_pages == 0:
        raise ValueError("O documento PDF não possui páginas.")

    target_pages = parse_page_range(pages, total_pages)
    watermarked_count = 0

    # Cache de buffers de marca d'água por dimensão (w, h) para evitar recriação repetida
    wm_cache: Dict[str, bytes] = {}

    for idx, page in enumerate(reader.pages):
        page_num = idx + 1
        page_box = page.mediabox
        page_w = float(page_box.width)
        page_h = float(page_box.height)

        if page_num in target_pages:
            dim_key = f"{round(page_w, 1)}x{round(page_h, 1)}"
            if dim_key not in wm_cache:
                wm_bytes = _generate_watermark_page_bytes(
                    page_w=page_w,
                    page_h=page_h,
                    watermark_type=watermark_type,
                    text=text_to_use,
                    font_size=font_size,
                    font_color=font_color,
                    opacity=opacity,
                    rotation=rotation,
                    position=position,
                    watermark_image_path=watermark_image_path,
                    image_scale=image_scale,
                )
                wm_cache[dim_key] = wm_bytes
            else:
                wm_bytes = wm_cache[dim_key]

            wm_reader = pypdf.PdfReader(io.BytesIO(wm_bytes))
            wm_page = wm_reader.pages[0]

            page.merge_page(wm_page, over=is_overlay)
            watermarked_count += 1

        writer.add_page(page)

    temp_merged_path = output_pdf_path.with_name(f"temp_wm_{output_pdf_path.name}")
    with open(temp_merged_path, "wb") as f_out:
        writer.write(f_out)

    # Linearização e Fast Web View com PikePDF
    try:
        with pikepdf.open(temp_merged_path) as pdf:
            pdf.save(output_pdf_path, linearize=linearize)
        if temp_merged_path.exists():
            temp_merged_path.unlink(missing_ok=True)
    except Exception as pike_err:
        logger.warning(f"Aviso de linearização PikePDF: {pike_err}. Mantendo arquivo gerado.")
        if temp_merged_path.exists():
            if output_pdf_path.exists():
                output_pdf_path.unlink(missing_ok=True)
            temp_merged_path.rename(output_pdf_path)

    duration = round(time.time() - start_time, 2)
    output_bytes = output_pdf_path.stat().st_size

    return {
        "success": True,
        "total_pages": total_pages,
        "pages_watermarked": watermarked_count,
        "watermark_type": watermark_type,
        "position": position,
        "layer": layer,
        "output_filename": output_pdf_path.name,
        "output_path": str(output_pdf_path),
        "output_bytes": output_bytes,
        "duration_seconds": duration,
    }
