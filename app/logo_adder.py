"""
Motor de inserção de Logotipos e Marcas Institucionais em documentos PDF.
Utiliza PyMuPDF (fitz) para renderização e posicionamento milimétrico de alta fidelidade
e PikePDF para otimização e linearização (Fast Web View).
"""

import io
import logging
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional, Set

from PIL import Image, ImageOps
import pikepdf
import pymupdf  # PyMuPDF

logger = logging.getLogger("pdf_logo_adder")


def parse_logo_page_range(range_str: str, total_pages: int) -> Set[int]:
    """
    Interpreta especificações de páginas como:
    - 'all' ou 'todas': todas as páginas
    - 'first' ou '1': apenas a primeira página
    - 'except-first' ou 'sem-capa': páginas 2 até total_pages
    - '1-3, 5, 8-10': páginas selecionadas
    """
    clean_str = (range_str or "all").strip().lower()
    if clean_str in ("all", "todas", "*"):
        return set(range(1, total_pages + 1))
    if clean_str in ("first", "primeira", "capa", "1"):
        return {1} if total_pages >= 1 else set()
    if clean_str in ("except-first", "sem-capa", "internas", "sem_capa"):
        if total_pages <= 1:
            return {1}
        return set(range(2, total_pages + 1))

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


def execute_add_logo(
    input_pdf_path: Path,
    output_pdf_path: Path,
    logo_image_path: Path,
    position: str = "top-right",
    scale: float = 0.20,
    margin_x: float = 36.0,
    margin_y: float = 36.0,
    opacity: float = 1.0,
    layer: str = "overlay",
    pages: str = "all",
    linearize: bool = True,
) -> Dict[str, Any]:
    """
    Insere logotipo (PNG com transparência, JPG, WebP) em posições estratégicas de um PDF.

    Args:
        input_pdf_path: Caminho do arquivo PDF de entrada
        output_pdf_path: Caminho do arquivo PDF gerado
        logo_image_path: Caminho da imagem do logotipo
        position: 'top-left', 'top-center', 'top-right',
                  'center-left', 'center', 'center-right',
                  'bottom-left', 'bottom-center', 'bottom-right'
        scale: Proporção da largura da página (0.05 a 0.80)
        margin_x: Margem horizontal em pontos (afastamento da borda)
        margin_y: Margem vertical em pontos (afastamento da borda)
        opacity: Nível de opacidade da imagem (0.05 a 1.0)
        layer: 'overlay' (sobreposto/frente) ou 'underlay' (atrás do conteúdo)
        pages: 'all', 'first', 'except-first', ou intervalos numéricos (ex: '1-3, 5')
        linearize: Otimização Fast Web View com PikePDF
    """
    t0 = time.time()
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_pdf_path.exists():
        raise FileNotFoundError(f"Arquivo PDF de entrada não encontrado: {input_pdf_path}")
    if not logo_image_path.exists():
        raise FileNotFoundError(f"Arquivo de imagem do logotipo não encontrado: {logo_image_path}")

    # Normalização de parâmetros
    norm_pos = (position or "top-right").strip().lower()
    valid_positions = {
        "top-left", "top-center", "top-right",
        "center-left", "center", "center-right",
        "bottom-left", "bottom-center", "bottom-right",
    }
    if norm_pos not in valid_positions:
        norm_pos = "top-right"

    safe_scale = max(0.05, min(0.85, float(scale)))
    safe_opacity = max(0.05, min(1.0, float(opacity)))
    safe_margin_x = max(0.0, float(margin_x))
    safe_margin_y = max(0.0, float(margin_y))
    is_overlay = (layer.strip().lower() != "underlay")

    # Prepara a imagem do logotipo em memória aplicando rotação EXIF e opacidade se necessário
    try:
        with Image.open(logo_image_path) as raw_img:
            raw_img = ImageOps.exif_transpose(raw_img)
            img = raw_img.convert("RGBA")
            orig_w, orig_h = img.size

            if orig_w <= 0 or orig_h <= 0:
                raise ValueError("Dimensões inválidas da imagem do logotipo.")

            if safe_opacity < 0.999:
                r, g, b, a = img.split()
                adjusted_a = a.point(lambda p: int(p * safe_opacity))
                img.putalpha(adjusted_a)

            buf = io.BytesIO()
            img.save(buf, format="PNG")
            logo_png_bytes = buf.getvalue()
    except Exception as img_err:
        logger.error(f"Falha ao processar arquivo do logotipo: {img_err}", exc_info=True)
        raise ValueError(f"Não foi possível processar a imagem do logotipo: {str(img_err)}")

    temp_path = output_pdf_path.parent / f"tmp_{output_pdf_path.name}"

    doc = pymupdf.open(str(input_pdf_path))
    total_pages = len(doc)
    if total_pages == 0:
        doc.close()
        raise ValueError("O documento PDF não possui páginas.")

    target_pages = parse_logo_page_range(pages, total_pages)
    pages_applied = 0

    try:
        for idx in range(total_pages):
            page_num_1based = idx + 1
            if page_num_1based not in target_pages:
                continue

            page = doc[idx]
            page_w = page.rect.width
            page_h = page.rect.height

            # Calcula dimensões proporcionais
            target_w = page_w * safe_scale
            aspect_ratio = orig_h / orig_w
            target_h = target_w * aspect_ratio

            # Proteção caso a imagem seja muito alta para a folha
            max_h_allowed = page_h * 0.85
            if target_h > max_h_allowed:
                target_h = max_h_allowed
                target_w = target_h / aspect_ratio

            # Cálculo das coordenadas (x0, y0) baseado no posicionamento
            if norm_pos == "top-left":
                x0 = safe_margin_x
                y0 = safe_margin_y
            elif norm_pos == "top-center":
                x0 = (page_w - target_w) / 2.0
                y0 = safe_margin_y
            elif norm_pos == "top-right":
                x0 = page_w - safe_margin_x - target_w
                y0 = safe_margin_y
            elif norm_pos == "center-left":
                x0 = safe_margin_x
                y0 = (page_h - target_h) / 2.0
            elif norm_pos == "center":
                x0 = (page_w - target_w) / 2.0
                y0 = (page_h - target_h) / 2.0
            elif norm_pos == "center-right":
                x0 = page_w - safe_margin_x - target_w
                y0 = (page_h - target_h) / 2.0
            elif norm_pos == "bottom-left":
                x0 = safe_margin_x
                y0 = page_h - safe_margin_y - target_h
            elif norm_pos == "bottom-center":
                x0 = (page_w - target_w) / 2.0
                y0 = page_h - safe_margin_y - target_h
            elif norm_pos == "bottom-right":
                x0 = page_w - safe_margin_x - target_w
                y0 = page_h - safe_margin_y - target_h
            else:
                x0 = page_w - safe_margin_x - target_w
                y0 = safe_margin_y

            rect = pymupdf.Rect(x0, y0, x0 + target_w, y0 + target_h)

            if not is_overlay:
                # Modo 'Por trás do Texto':
                # 1. Extrai todos os operadores de texto originais (BT...ET) da página
                orig_contents = page.get_contents()
                orig_bytes = b"\n".join([doc.xref_stream(x) for x in orig_contents])
                text_matches = re.findall(rb"BT[\s\S]*?ET", orig_bytes)
                text_stream = (b"\nq\n" + b"\n".join(text_matches) + b"\nQ\n") if text_matches else b""

                # 2. Insere a imagem com overlay=True para que ela nunca fique oculta
                #    sob planos de fundo sólidos, faixas de cabeçalho ou telas Canva/PowerPoint
                page.insert_image(
                    rect,
                    stream=logo_png_bytes,
                    keep_proportion=True,
                    overlay=True,
                )

                # 3. Se houver texto na página, executa o stream de texto sobre o logotipo,
                #    garantindo que qualquer texto/título permaneça nítido e na frente da imagem
                if text_stream:
                    contents_after = page.get_contents()
                    if contents_after:
                        img_xref = contents_after[-1]
                        img_bytes = doc.xref_stream(img_xref)
                        doc.update_stream(img_xref, img_bytes + b"\n" + text_stream)
            else:
                page.insert_image(
                    rect,
                    stream=logo_png_bytes,
                    keep_proportion=True,
                    overlay=True,
                )

            pages_applied += 1

        doc.save(str(temp_path))
    finally:
        doc.close()

    # Otimização e linearização Fast Web View via PikePDF
    with pikepdf.open(temp_path) as pdoc:
        pdoc.save(str(output_pdf_path), linearize=linearize)
    temp_path.unlink(missing_ok=True)

    elapsed = time.time() - t0
    filesize = output_pdf_path.stat().st_size

    logger.info(
        f"Logotipo adicionado com sucesso: '{output_pdf_path.name}', "
        f"{pages_applied}/{total_pages} páginas, {filesize} bytes em {elapsed:.2f}s"
    )

    return {
        "output_filename": output_pdf_path.name,
        "filesize": filesize,
        "output_bytes": filesize,
        "pages": total_pages,
        "total_pages": total_pages,
        "pages_applied": pages_applied,
        "position": norm_pos,
        "scale": safe_scale,
        "opacity": safe_opacity,
        "linearized": linearize,
        "time_seconds": round(elapsed, 3),
        "duration_seconds": round(elapsed, 3),
    }
