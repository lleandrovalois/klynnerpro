"""
Motor de conversão de documentos PDF para Imagens (PNG/JPEG).
Desenvolvido para Klynner Suite (Módulo: Conversão).

Regras de Negócio Implementadas:
- RN-01: Seleção de Modo (A: Páginas Individuais / ZIP se > 1 página; B: Imagem Única Unificada contínua).
- RN-02: Formato de Saída (PNG padrão de alta fidelidade ou JPEG otimizado).
- RN-03: Resolução / DPI configurável (150 DPI padrão balanceado, 300 DPI alta definição, 72 DPI tela leve).
- RN-04: Proteção contra estouro de memória e limites de dimensões de imagem.
"""

import io
import logging
import os
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import zipfile

import fitz  # PyMuPDF
from PIL import Image

logger = logging.getLogger("pdf_to_image")

# Previne limitações arbitrárias de descompressão do Pillow para imagens unificadas longas
Image.MAX_IMAGE_PIXELS = 250_000_000

# Limite máximo de altura para imagem contínua (JPEG tem limite rígido de 65.535px no padrão JFIF)
MAX_SAFE_CANVAS_HEIGHT = 65_000


def parse_page_range(range_str: Optional[str], total_pages: int) -> List[int]:
    """
    Analisa uma string de intervalo de páginas (ex: '1-3, 5, 8-10') e retorna
    uma lista ordenada de índices 0-based de páginas válidas.
    Se 'all', None ou vazia, retorna todas as páginas [0, 1, ..., total_pages - 1].
    """
    if not range_str or range_str.strip().lower() == "all":
        return list(range(total_pages))

    selected: Set[int] = set()
    parts = [p.strip() for p in range_str.split(",") if p.strip()]

    for part in parts:
        if "-" in part:
            sub = part.split("-")
            if len(sub) == 2:
                try:
                    start = int(sub[0].strip())
                    end = int(sub[1].strip())
                    if start > end:
                        start, end = end, start
                    for p in range(start, end + 1):
                        if 1 <= p <= total_pages:
                            selected.add(p - 1)
                except ValueError:
                    continue
        else:
            try:
                p = int(part.strip())
                if 1 <= p <= total_pages:
                    selected.add(p - 1)
            except ValueError:
                continue

    ordered = sorted(list(selected))
    if not ordered:
        return list(range(total_pages))
    return ordered


def execute_pdf_to_image(
    pdf_path: Path,
    output_dir: Path,
    mode: str = "individual",
    image_format: str = "png",
    dpi: int = 150,
    page_range: str = "all",
    output_filename: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executa a conversão de um documento PDF em imagens de alta definição.

    - pdf_path: caminho para o PDF original
    - output_dir: diretório onde os arquivos de saída serão criados
    - mode: 'individual' (Modo A) ou 'unified' (Modo B - Imagem Única Contínua)
    - image_format: 'png' ou 'jpeg'/'jpg'
    - dpi: 72, 150 (padrão) ou 300
    - page_range: 'all' ou intervalo (ex: '1-5, 8')
    - output_filename: nome base sugerido para o arquivo de saída
    """
    start_time = time.time()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not pdf_path.exists():
        raise FileNotFoundError(f"Arquivo PDF não encontrado: {pdf_path}")

    # Normalização de parâmetros
    clean_mode = (mode or "individual").strip().lower()
    if clean_mode not in ("individual", "unified", "single"):
        clean_mode = "individual"

    clean_fmt = (image_format or "png").strip().lower()
    if clean_fmt in ("jpg", "jpeg"):
        save_fmt = "JPEG"
        ext = "jpg"
    else:
        save_fmt = "PNG"
        ext = "png"

    clean_dpi = int(dpi or 150)
    if clean_dpi not in (72, 150, 300):
        clean_dpi = 150

    base_stem = Path(output_filename or pdf_path.stem).stem
    # Remove caracteres potencialmente problemáticos no nome do arquivo
    clean_stem = re.sub(r'[^\w\s\.-]', '_', base_stem).strip() or "documento"

    doc = fitz.open(str(pdf_path))
    total_doc_pages = len(doc)

    if total_doc_pages == 0:
        doc.close()
        raise ValueError("O documento PDF está vazio e não contém páginas para renderizar.")

    pages_to_render = parse_page_range(page_range, total_doc_pages)
    selected_count = len(pages_to_render)

    logger.info(
        f"Iniciando conversão de PDF para Imagem: {pdf_path.name} | "
        f"Modo={clean_mode} | Formato={save_fmt} | DPI={clean_dpi} | "
        f"Páginas={selected_count}/{total_doc_pages}"
    )

    # Fator de escala a partir de 72 DPI (escala padrão de pontos do PDF)
    zoom = clean_dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    rendered_images: List[Tuple[int, Image.Image]] = []

    try:
        for idx, page_num in enumerate(pages_to_render):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            rendered_images.append((page_num + 1, img))
    finally:
        doc.close()

    if not rendered_images:
        raise ValueError("Nenhuma página pôde ser renderizada do documento PDF.")

    # -------------------------------------------------------------
    # MODO B: IMAGEM ÚNICA UNIFICADA (Páginas Concatenadas Verticalmente)
    # -------------------------------------------------------------
    if clean_mode in ("unified", "single"):
        max_width = max(img.width for _, img in rendered_images)
        total_height = sum(img.height for _, img in rendered_images)

        # RN-04: Tratamento de limites de tamanho
        if total_height > MAX_SAFE_CANVAS_HEIGHT:
            raise ValueError(
                f"A imagem unificada ultrapassaria o limite seguro de altura "
                f"({total_height:,}px > {MAX_SAFE_CANVAS_HEIGHT:,}px). "
                f"Para documentos extensos ({selected_count} páginas), "
                f"utilize o modo 'Páginas Individuais (.ZIP)' ou reduza a resolução para 150 DPI."
            )

        # Cria imagem contínua com fundo branco
        composite_img = Image.new("RGB", (max_width, total_height), (255, 255, 255))

        current_y = 0
        for _, img in rendered_images:
            # Centraliza horizontalmente se as páginas tiverem larguras diferentes
            x_offset = (max_width - img.width) // 2
            composite_img.paste(img, (x_offset, current_y))
            current_y += img.height

        final_filename = f"{clean_stem}_completo.{ext}"
        final_path = output_dir / final_filename

        if save_fmt == "JPEG":
            composite_img.save(str(final_path), format="JPEG", quality=92, optimize=True)
        else:
            composite_img.save(str(final_path), format="PNG", optimize=True)

        elapsed = round(time.time() - start_time, 2)
        file_size = final_path.stat().st_size

        logger.info(f"Imagem única gerada com sucesso: {final_filename} ({file_size} bytes, {elapsed}s).")
        return {
            "success": True,
            "mode": "unified",
            "format": ext,
            "dpi": clean_dpi,
            "output_filename": final_filename,
            "is_zip": False,
            "page_count": selected_count,
            "width": max_width,
            "height": total_height,
            "file_size": file_size,
            "execution_time_seconds": elapsed,
        }

    # -------------------------------------------------------------
    # MODO A: PÁGINAS INDIVIDUAIS (1 página = imagem direta; >1 = arquivo ZIP)
    # -------------------------------------------------------------
    # Caso 1: Apenas 1 página selecionada -> Download direto da imagem única
    if selected_count == 1:
        page_num, single_img = rendered_images[0]
        final_filename = f"{clean_stem}_pagina_{page_num}.{ext}"
        final_path = output_dir / final_filename

        if save_fmt == "JPEG":
            single_img.save(str(final_path), format="JPEG", quality=92, optimize=True)
        else:
            single_img.save(str(final_path), format="PNG", optimize=True)

        elapsed = round(time.time() - start_time, 2)
        file_size = final_path.stat().st_size

        logger.info(f"Página única exportada diretamente: {final_filename} ({file_size} bytes, {elapsed}s).")
        return {
            "success": True,
            "mode": "individual",
            "format": ext,
            "dpi": clean_dpi,
            "output_filename": final_filename,
            "is_zip": False,
            "page_count": 1,
            "file_size": file_size,
            "execution_time_seconds": elapsed,
        }

    # Caso 2: Múltiplas páginas -> Empacota em arquivo .ZIP
    final_zip_name = f"{clean_stem}_imagens.zip"
    final_zip_path = output_dir / final_zip_name

    with zipfile.ZipFile(str(final_zip_path), "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        digits = len(str(selected_count))
        digits = max(2, digits)

        for seq, (page_num, page_img) in enumerate(rendered_images, start=1):
            img_buffer = io.BytesIO()
            if save_fmt == "JPEG":
                page_img.save(img_buffer, format="JPEG", quality=92, optimize=True)
            else:
                page_img.save(img_buffer, format="PNG", optimize=True)

            img_bytes = img_buffer.getvalue()
            # Nomenclatura organizada dentro do ZIP
            inner_name = f"{clean_stem}_pagina_{seq:0{digits}d}.{ext}"
            zf.writestr(inner_name, img_bytes)

    elapsed = round(time.time() - start_time, 2)
    zip_size = final_zip_path.stat().st_size

    logger.info(f"Arquivo ZIP com {selected_count} imagens criado: {final_zip_name} ({zip_size} bytes, {elapsed}s).")
    return {
        "success": True,
        "mode": "individual",
        "format": ext,
        "dpi": clean_dpi,
        "output_filename": final_zip_name,
        "is_zip": True,
        "page_count": selected_count,
        "file_size": zip_size,
        "execution_time_seconds": elapsed,
    }
