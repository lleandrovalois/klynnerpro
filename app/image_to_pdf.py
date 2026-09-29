"""
Motor de conversão de imagens para PDF com suporte a múltiplos formatos,
orientação automática, ajuste de página (A4, Carta, Ajustar à Imagem),
controle de margens e otimização binária QPDF.
"""

import io
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

from PIL import Image, ImageOps
import pikepdf
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

logger = logging.getLogger("image_to_pdf")

# Dimensões padrão em pontos (1 pt = 1/72 polegada)
PAGE_SIZES = {
    "a4": A4,  # (595.27, 841.89)
    "letter": letter,  # (612.0, 792.0)
}

MARGIN_SIZES = {
    "none": 0.0,
    "small": 20.0,  # ~7 mm
    "big": 45.0,  # ~16 mm
}


def _process_image_frame(pil_img: Image.Image) -> Image.Image:
    """Corrige rotação EXIF e assegura espaço de cor compatível."""
    try:
        pil_img = ImageOps.exif_transpose(pil_img)
    except Exception:
        pass

    if pil_img.mode in ("RGBA", "LA") or (pil_img.mode == "P" and "transparency" in pil_img.info):
        # Mantém transparência se PNG ou compõe sobre fundo branco
        bg = Image.new("RGBA", pil_img.size, (255, 255, 255, 255))
        converted = pil_img.convert("RGBA")
        bg.paste(converted, mask=converted.split()[3])
        return bg.convert("RGB")
    elif pil_img.mode not in ("RGB", "L"):
        return pil_img.convert("RGB")

    return pil_img


def execute_image_to_pdf(
    image_paths: List[Path],
    output_pdf_path: Path,
    page_size: str = "a4",
    orientation: str = "auto",
    margin: str = "none",
    linearize: bool = True,
) -> Dict[str, Any]:
    """
    Converte uma ou múltiplas imagens para um documento PDF único.
    
    - image_paths: lista ordenada de caminhos para as imagens (.png, .jpg, .jpeg, .webp, .bmp, .tiff, etc.)
    - page_size: 'a4', 'letter', ou 'fit' (ajusta dimensões exatas da imagem)
    - orientation: 'auto' (baseada nas dimensões da imagem), 'portrait', ou 'landscape'
    - margin: 'none', 'small' (20pt), 'big' (45pt)
    - linearize: aplica Fast Web View (linearização binária) via QPDF/PikePDF
    """
    start_time = time.time()
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    if not image_paths:
        raise ValueError("Nenhuma imagem fornecida para conversão.")

    temp_pdf_path = output_pdf_path.with_name(f"temp_img_{output_pdf_path.name}")
    margin_pt = MARGIN_SIZES.get(margin.lower(), 0.0)
    total_pages = 0

    c = canvas.Canvas(str(temp_pdf_path))

    for img_path in image_paths:
        if not img_path.exists():
            continue

        try:
            with Image.open(img_path) as raw_img:
                # Trata arquivos TIFF ou GIF multi-quadro
                frame_count = getattr(raw_img, "n_frames", 1)

                for frame_idx in range(frame_count):
                    try:
                        raw_img.seek(frame_idx)
                    except EOFError:
                        break

                    img = _process_image_frame(raw_img)
                    img_w, img_h = img.size

                    # Determina tamanho e orientação da página
                    if page_size.lower() == "fit":
                        # Dimensão idêntica à proporção da imagem sem margens forçadas
                        p_width = float(img_w)
                        p_height = float(img_h)
                    else:
                        base_w, base_h = PAGE_SIZES.get(page_size.lower(), A4)

                        if orientation.lower() == "auto":
                            is_landscape = img_w > img_h
                        elif orientation.lower() == "landscape":
                            is_landscape = True
                        else:
                            is_landscape = False

                        if is_landscape:
                            p_width, p_height = max(base_w, base_h), min(base_w, base_h)
                        else:
                            p_width, p_height = min(base_w, base_h), max(base_w, base_h)

                    c.setPageSize((p_width, p_height))

                    # Área disponível após dedução das margens
                    avail_w = max(10.0, p_width - (2 * margin_pt))
                    avail_h = max(10.0, p_height - (2 * margin_pt))

                    # Ajusta escala proporcional da imagem
                    scale = min(avail_w / img_w, avail_h / img_h)
                    draw_w = img_w * scale
                    draw_h = img_h * scale

                    # Centraliza na área útil
                    pos_x = margin_pt + (avail_w - draw_w) / 2.0
                    pos_y = margin_pt + (avail_h - draw_h) / 2.0

                    # Salva imagem processada em buffer de memória para o ReportLab
                    img_buf = io.BytesIO()
                    img.save(img_buf, format="JPEG", quality=95, optimize=True)
                    img_buf.seek(0)

                    c.drawImage(
                        ImageReader(img_buf),
                        pos_x,
                        pos_y,
                        width=draw_w,
                        height=draw_h,
                        preserveAspectRatio=True,
                    )
                    c.showPage()
                    total_pages += 1

        except Exception as e:
            logger.error(f"Erro ao processar imagem '{img_path.name}': {e}", exc_info=True)
            raise ValueError(f"Não foi possível processar a imagem '{img_path.name}': {str(e)}")

    if total_pages == 0:
        if temp_pdf_path.exists():
            temp_pdf_path.unlink(missing_ok=True)
        raise ValueError("Nenhuma página válida pôde ser gerada a partir das imagens.")

    c.save()

    # Linearização e otimização com PikePDF
    try:
        with pikepdf.open(temp_pdf_path) as pdf:
            pdf.save(output_pdf_path, linearize=linearize)
        if temp_pdf_path.exists():
            temp_pdf_path.unlink(missing_ok=True)
    except Exception as pike_err:
        logger.warning(f"Aviso de linearização PikePDF: {pike_err}. Mantendo arquivo gerado.")
        if temp_pdf_path.exists():
            if output_pdf_path.exists():
                output_pdf_path.unlink(missing_ok=True)
            temp_pdf_path.rename(output_pdf_path)

    duration = round(time.time() - start_time, 2)
    output_bytes = output_pdf_path.stat().st_size

    return {
        "success": True,
        "total_images": len(image_paths),
        "total_pages": total_pages,
        "output_filename": output_pdf_path.name,
        "output_path": str(output_pdf_path),
        "output_bytes": output_bytes,
        "duration_seconds": duration,
    }
