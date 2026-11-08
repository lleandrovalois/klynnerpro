"""
Módulo de Conversão de Documentos PDF para Formato Kindle (EPUB / MOBI).
Implementa reflow dinâmico de texto, detecção de capítulos/bookmarks, remoção de
cabeçalhos/rodapés repetitivos, extração de capa (cover.jpg), sanitização XHTML/CSS
e suporte tanto a EPUB (padrão Amazon Send to Kindle) quanto MOBI.
"""

import asyncio
import html
import io
import logging
import os
from pathlib import Path
import re
import struct
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid
import zipfile

from PIL import Image
import pikepdf
import pymupdf

logger = logging.getLogger("pdf_to_kindle")

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB (RN-04)

# Gerenciador de jobs em memória para acompanhamento assíncrono de progresso
KINDLE_JOBS: Dict[str, Dict[str, Any]] = {}


def get_kindle_job(job_id: str) -> Optional[Dict[str, Any]]:
    return KINDLE_JOBS.get(job_id)


def update_kindle_job(job_id: str, progress: int, step: str, status: str = "processing", result: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
    if job_id in KINDLE_JOBS:
        KINDLE_JOBS[job_id]["progress"] = progress
        KINDLE_JOBS[job_id]["step"] = step
        KINDLE_JOBS[job_id]["status"] = status
        if result:
            KINDLE_JOBS[job_id]["result"] = result
        if error:
            KINDLE_JOBS[job_id]["error"] = error
        KINDLE_JOBS[job_id]["updated_at"] = time.time()


def check_pdf_encryption(file_path: Path) -> None:
    """
    Verifica se o arquivo PDF está protegido por senha.
    Levanta ValueError com mensagem padronizada (Cenário 2).
    """
    try:
        with pikepdf.open(file_path):
            pass
    except (pikepdf.PasswordError, pikepdf.PdfError) as e:
        if "password" in str(e).lower() or isinstance(e, pikepdf.PasswordError):
            raise ValueError("O arquivo enviado está protegido por senha. Remova a senha antes de converter.")

    doc = pymupdf.open(str(file_path))
    try:
        if doc.is_encrypted or doc.needs_pass:
            raise ValueError("O arquivo enviado está protegido por senha. Remova a senha antes de converter.")
    finally:
        doc.close()


def analyze_pdf_for_kindle(session_dir: Path, file_id: str) -> Dict[str, Any]:
    """
    Analisa previamente o PDF para verificar limitações de operação (RN-04),
    segurança contra senhas (Cenário 2), camada de texto/OCR (Cenário 3) e metadados.
    """
    safe_name = Path(file_id).name
    file_path = session_dir / safe_name
    if not file_path.exists() and (session_dir / "output" / safe_name).exists():
        file_path = session_dir / "output" / safe_name
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo '{file_id}' não encontrado na sessão.")

    # 1. Limite de tamanho (RN-04: máx 50 MB)
    file_size = file_path.stat().st_size
    if file_size > MAX_FILE_SIZE_BYTES:
        raise ValueError(f"O arquivo enviado possui {file_size / (1024*1024):.1f} MB, excedendo o limite operacional de 50 MB.")

    # 2. Verificação de senha / criptografia (Cenário 2)
    check_pdf_encryption(file_path)

    doc = pymupdf.open(str(file_path))
    try:
        total_pages = len(doc)
        if total_pages == 0:
            raise ValueError("O arquivo PDF não contém páginas.")

        # Metadados
        meta = doc.metadata or {}
        raw_title = (meta.get("title") or "").strip()
        raw_author = (meta.get("author") or "").strip()

        # Limpa título ou usa nome do arquivo
        suggested_title = raw_title if raw_title and len(raw_title) > 2 else file_path.stem.replace("_", " ").replace("-", " ").title()
        suggested_author = raw_author if raw_author and len(raw_author) > 1 else "Autor Desconhecido"

        # Bookmarks / TOC do PDF
        pdf_toc = doc.get_toc()
        chapters_count = len(pdf_toc)

        # 3. Análise da camada de texto vs Imagens (Cenário 3 / RN-04)
        total_chars = 0
        total_images = 0
        sample_pages = min(total_pages, 10)
        for i in range(sample_pages):
            p = doc[i]
            t = p.get_text().strip()
            total_chars += len(t)
            total_images += len(p.get_images())

        avg_chars_per_page = total_chars / max(1, sample_pages)
        is_scanned = (avg_chars_per_page < 30 and (total_images > 0 or total_chars < 50))

        warning_message = None
        if is_scanned:
            warning_message = "Este documento não possui camada de texto editável. A formatação no Kindle pode não suportar ajuste dinâmico de fonte."

        return {
            "success": True,
            "filename": safe_name,
            "filesize": file_size,
            "total_pages": total_pages,
            "suggested_title": suggested_title,
            "suggested_author": suggested_author,
            "has_bookmarks": chapters_count > 0,
            "chapters_count": chapters_count,
            "is_scanned": is_scanned,
            "warning_message": warning_message,
        }
    finally:
        doc.close()


def detect_repeated_headers_footers(doc: pymupdf.Document) -> Tuple[Set[str], Set[str]]:
    """
    Detecta cabeçalhos e rodapés repetitivos que ocorrem em múltiplas páginas (RN-02)
    para descartá-los do fluxo narrativo do livro Kindle.
    """
    top_candidates: Dict[str, int] = {}
    bottom_candidates: Dict[str, int] = {}
    total_pages = len(doc)
    if total_pages < 2:
        return set(), set()

    for page in doc:
        rect = page.rect
        page_h = rect.height
        blocks = page.get_text("blocks")
        for b in blocks:
            if len(b) < 5:
                continue
            x0, y0, x1, y1, text = b[0], b[1], b[2], b[3], b[4].strip()
            if not text or len(text) > 120:
                continue

            # Cabeçalho: topo 12% da página
            if y1 < page_h * 0.12:
                cleaned = " ".join(text.split())
                top_candidates[cleaned] = top_candidates.get(cleaned, 0) + 1

            # Rodapé: base 12% da página
            elif y0 > page_h * 0.88:
                cleaned = " ".join(text.split())
                bottom_candidates[cleaned] = bottom_candidates.get(cleaned, 0) + 1

    # Cabeçalho repetido em pelo menos 2 páginas
    min_occ = 2 if total_pages <= 4 else max(2, int(total_pages * 0.25))
    repeated_headers = {k for k, v in top_candidates.items() if v >= min_occ}
    repeated_footers = {k for k, v in bottom_candidates.items() if v >= min_occ}

    return repeated_headers, repeated_footers


def is_page_number(text: str) -> bool:
    """Verifica se o texto representa número de página avulso (ex.: '1', '- 12 -', 'Página 5')."""
    t = text.strip()
    if re.match(r"^\d{1,5}$", t):
        return True
    if re.match(r"^[-–—\s]*\d{1,5}[-–—\s]*$", t):
        return True
    if re.match(r"^p[aá]g(?:ina)?\.?\s*\d{1,5}(?:\s*/\s*\d{1,5})?$", t, re.IGNORECASE):
        return True
    return False


def clean_and_reflow_blocks(
    blocks: List[Any],
    page_height: float,
    repeated_headers: Set[str],
    repeated_footers: Set[str],
) -> List[Dict[str, Any]]:
    """
    Processa blocos de texto da página, realizando descarte de cabeçalhos/rodapés,
    ordenação multi-coluna (RN-02) e normalização de parágrafos.
    """
    text_blocks = []
    for b in blocks:
        if len(b) < 7:
            continue
        x0, y0, x1, y1, text, block_no, block_type = b[:7]
        if block_type != 0:  # 0 = texto
            continue
        cleaned_text = text.strip()
        if not cleaned_text:
            continue

        normalized_line = " ".join(cleaned_text.split())

        # Descarte de cabeçalhos e rodapés repetitivos (RN-02)
        if y1 < page_height * 0.12:
            if normalized_line in repeated_headers or is_page_number(normalized_line):
                continue
        elif y0 > page_height * 0.88:
            if normalized_line in repeated_footers or is_page_number(normalized_line):
                continue

        text_blocks.append({
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1,
            "raw_text": cleaned_text,
        })

    if not text_blocks:
        return []

    # Detecção e ordenação multi-coluna:
    # Se houver duas colunas nítidas, agrupa blocos por coluna antes de ordenar por y
    min_x = min(b["x0"] for b in text_blocks)
    max_x = max(b["x1"] for b in text_blocks)
    width = max_x - min_x
    mid_x = min_x + (width / 2.0)

    is_multi_column = False
    col1 = []
    col2 = []
    if width > 300:
        for b in text_blocks:
            if b["x1"] <= mid_x + 20:
                col1.append(b)
            elif b["x0"] >= mid_x - 20:
                col2.append(b)
        if len(col1) >= 2 and len(col2) >= 2 and (len(col1) + len(col2)) >= int(len(text_blocks) * 0.75):
            is_multi_column = True

    if is_multi_column:
        col1.sort(key=lambda b: (b["y0"], b["x0"]))
        col2.sort(key=lambda b: (b["y0"], b["x0"]))
        ordered_blocks = col1 + col2
    else:
        # Ordenação padrão ocidental: topo para base, esquerda para direita
        ordered_blocks = sorted(text_blocks, key=lambda b: (round(b["y0"], -1), b["x0"]))

    return ordered_blocks


def reflow_text_to_html_paragraphs(raw_text: str) -> str:
    """
    Unifica quebras de linha indevidas de PDFs (desfazendo hifenização e hard line wraps),
    produzindo parágrafos semânticos <p>...</p> com reflow fluido.
    """
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    if not lines:
        return ""

    merged_paragraphs = []
    current_para = []

    for i, line in enumerate(lines):
        if not current_para:
            current_para.append(line)
            continue

        prev_line = current_para[-1]

        # Se a linha anterior termina com hífen, junta a palavra quebrada
        if prev_line.endswith("-") and len(prev_line) > 1 and not prev_line.endswith(" -"):
            current_para[-1] = prev_line[:-1] + line
        # Se a linha anterior termina sem pontuação de término de sentença, une com espaço
        elif not re.search(r'[.!?:;—"”\']$', prev_line):
            current_para[-1] = prev_line + " " + line
        else:
            # Caso contrário, inicia novo parágrafo
            merged_paragraphs.append(" ".join(current_para))
            current_para = [line]

    if current_para:
        merged_paragraphs.append(" ".join(current_para))

    html_parts = []
    for p in merged_paragraphs:
        clean_p = p.strip()
        if not clean_p:
            continue
        # Detecção de títulos curtos ou capítulos
        if (len(clean_p) < 80 and re.match(r'^(?:cap[ií]tulo|chapter|se[çc][aã]o|parte|volume|\d+\.?\s+[A-ZÀ-Ú])', clean_p, re.IGNORECASE)):
            html_parts.append(f"<h2>{html.escape(clean_p)}</h2>")
        else:
            html_parts.append(f"<p>{html.escape(clean_p)}</p>")

    return "\n".join(html_parts)


def extract_cover_image(doc: pymupdf.Document, output_path: Path) -> Path:
    """
    Extrai a primeira página do PDF e salva como imagem de capa (cover.jpg) em alta definição (RN-03).
    """
    page = doc[0]
    # Renderiza em 2x escala para alta nitidez em telas Retina / E-ink Carta HD
    mat = pymupdf.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat, alpha=False)

    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "JPEG", quality=92, optimize=True)
    return output_path


KINDLE_CSS_CONTENT = """
@charset "utf-8";
@page {
  margin: 1.2em 1.0em;
}
body {
  font-family: "Bookerly", "Georgia", "Palatino", serif;
  font-size: 1.05rem;
  line-height: 1.5;
  text-align: justify;
  margin: 0;
  padding: 0;
  color: #111111;
  background-color: transparent;
}
h1 {
  font-family: "Amazon Ember", "Helvetica Neue", "Arial", sans-serif;
  font-size: 1.6rem;
  font-weight: bold;
  text-align: center;
  margin-top: 2.0em;
  margin-bottom: 1.0em;
  page-break-before: always;
  break-before: page;
}
h2 {
  font-family: "Amazon Ember", "Helvetica Neue", "Arial", sans-serif;
  font-size: 1.3rem;
  font-weight: bold;
  text-align: center;
  margin-top: 1.6em;
  margin-bottom: 0.8em;
  page-break-before: always;
  break-before: page;
}
h3 {
  font-size: 1.15rem;
  font-weight: bold;
  margin-top: 1.2em;
  margin-bottom: 0.4em;
}
p {
  text-indent: 1.4em;
  margin-top: 0;
  margin-bottom: 0.4em;
  text-align: justify;
}
p.no-indent {
  text-indent: 0;
}
.cover-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 98vh;
  text-align: center;
  margin: 0;
  padding: 0;
}
.cover-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  display: block;
  margin: 0 auto;
}
.fixed-page-container {
  text-align: center;
  page-break-after: always;
  break-after: page;
  margin: 0;
  padding: 0;
}
.fixed-page-image {
  max-width: 100%;
  max-height: 96vh;
  object-fit: contain;
  display: block;
  margin: 0 auto;
}
nav#toc ol {
  list-style-type: none;
  padding-left: 0;
}
nav#toc li {
  margin: 0.8em 0;
  line-height: 1.4;
}
nav#toc a {
  text-decoration: none;
  color: inherit;
}
"""


def build_epub_file(
    out_path: Path,
    title: str,
    author: str,
    cover_image_path: Optional[Path],
    chapters: List[Dict[str, Any]],
    lang: str = "pt-BR",
) -> None:
    """
    Compila um arquivo .epub (EPUB 3 / 2 hibrido para compatibilidade total com Amazon Send to Kindle).
    Gera mimetype uncompressed, META-INF/container.xml, OEBPS/content.opf, toc.ncx, nav.xhtml,
    styles.css, cover.xhtml e os capítulos.
    """
    book_id = str(uuid.uuid4())

    with zipfile.ZipFile(out_path, "w") as zf:
        # 1. mimetype como primeiro arquivo obrigatório sem compressão (ZIP_STORED)
        zf.writestr("mimetype", b"application/epub+zip", compress_type=zipfile.ZIP_STORED)

        # 2. META-INF/container.xml
        container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""
        zf.writestr("META-INF/container.xml", container_xml.encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED)

        # 3. OEBPS/styles.css
        zf.writestr("OEBPS/styles.css", KINDLE_CSS_CONTENT.encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED)

        manifest_items = [
            '<item id="css" href="styles.css" media-type="text/css"/>',
            '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
            '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        ]
        spine_items = []

        # 4. Capa
        has_cover = cover_image_path and cover_image_path.exists()
        if has_cover:
            with open(cover_image_path, "rb") as f_cov:
                zf.writestr("OEBPS/images/cover.jpg", f_cov.read(), compress_type=zipfile.ZIP_DEFLATED)
            manifest_items.append('<item id="cover-image" href="images/cover.jpg" media-type="image/jpeg" properties="cover-image"/>')

            cover_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{lang}">
<head>
  <title>Capa - {html.escape(title)}</title>
  <link rel="stylesheet" href="styles.css" type="text/css"/>
</head>
<body>
  <div class="cover-container">
    <img src="images/cover.jpg" alt="Capa" class="cover-image"/>
  </div>
</body>
</html>"""
            zf.writestr("OEBPS/cover.xhtml", cover_xhtml.encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED)
            manifest_items.append('<item id="cover-page" href="cover.xhtml" media-type="application/xhtml+xml"/>')
            spine_items.append('<itemref idref="cover-page"/>')

        # 5. Capítulos
        nav_points_ncx = []
        nav_li_epub3 = []

        for idx, ch in enumerate(chapters, start=1):
            ch_id = f"chapter_{idx}"
            filename = f"{ch_id}.xhtml"
            ch_title = ch.get("title") or f"Capítulo {idx}"
            content_html = ch.get("html", "")
            img_file = ch.get("image_file")

            if img_file and Path(img_file).exists():
                img_name = Path(img_file).name
                with open(img_file, "rb") as fi:
                    zf.writestr(f"OEBPS/images/{img_name}", fi.read(), compress_type=zipfile.ZIP_DEFLATED)
                manifest_items.append(f'<item id="img_{idx}" href="images/{img_name}" media-type="image/jpeg"/>')
                body_content = content_html
            else:
                body_content = f"<h1>{html.escape(ch_title)}</h1>\n  {content_html}"

            ch_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{lang}">
<head>
  <title>{html.escape(ch_title)}</title>
  <link rel="stylesheet" href="styles.css" type="text/css"/>
</head>
<body>
  {body_content}
</body>
</html>"""
            zf.writestr(f"OEBPS/{filename}", ch_xhtml.encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED)
            manifest_items.append(f'<item id="{ch_id}" href="{filename}" media-type="application/xhtml+xml"/>')
            spine_items.append(f'<itemref idref="{ch_id}"/>')

            # NCX navPoint
            nav_points_ncx.append(f"""    <navPoint id="navPoint-{idx}" playOrder="{idx}">
      <navLabel><text>{html.escape(ch_title)}</text></navLabel>
      <content src="{filename}"/>
    </navPoint>""")
            # EPUB3 nav li
            nav_li_epub3.append(f'      <li><a href="{filename}">{html.escape(ch_title)}</a></li>')

        # 6. OEBPS/nav.xhtml (EPUB 3 Table of Contents)
        nav_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{lang}">
<head>
  <title>Sumário</title>
  <link rel="stylesheet" href="styles.css" type="text/css"/>
</head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>Sumário</h1>
    <ol>
{chr(10).join(nav_li_epub3)}
    </ol>
  </nav>
</body>
</html>"""
        zf.writestr("OEBPS/nav.xhtml", nav_xhtml.encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED)

        # 7. OEBPS/toc.ncx (EPUB 2 / Kindle Classic NCX)
        toc_ncx = f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="urn:uuid:{book_id}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>{html.escape(title)}</text></docTitle>
  <docAuthor><text>{html.escape(author)}</text></docAuthor>
  <navMap>
{chr(10).join(nav_points_ncx)}
  </navMap>
</ncx>"""
        zf.writestr("OEBPS/toc.ncx", toc_ncx.encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED)

        # 8. OEBPS/content.opf
        manifest_str = "\n    ".join(manifest_items)
        spine_str = "\n    ".join(spine_items)
        cover_meta = '<meta name="cover" content="cover-image"/>' if has_cover else ''

        content_opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="BookId">urn:uuid:{book_id}</dc:identifier>
    <dc:title>{html.escape(title)}</dc:title>
    <dc:creator>{html.escape(author)}</dc:creator>
    <dc:language>{lang}</dc:language>
    <dc:publisher>Klynner Pro PDF Converter</dc:publisher>
    <meta property="dcterms:modified">{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}</meta>
    {cover_meta}
  </metadata>
  <manifest>
    {manifest_str}
  </manifest>
  <spine toc="ncx">
    {spine_str}
  </spine>
  <guide>
    {'<reference type="cover" title="Capa" href="cover.xhtml"/>' if has_cover else ''}
    <reference type="toc" title="Sumário" href="nav.xhtml"/>
  </guide>
</package>"""
        zf.writestr("OEBPS/content.opf", content_opf.encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED)


def build_mobi_file(
    out_path: Path,
    title: str,
    author: str,
    cover_image_path: Optional[Path],
    chapters: List[Dict[str, Any]],
) -> None:
    """
    Compila um arquivo binário .mobi (Mobipocket PalmDOC + EXTH metadata)
    para compatibilidade com e-readers Kindle clássicos e transferência direta via USB (RN-01).
    """
    # Constrói documento HTML unificado com sumário interno e capítulos
    toc_links = []
    chapters_content = []

    for idx, ch in enumerate(chapters, start=1):
        ch_title = ch.get("title") or f"Capítulo {idx}"
        ch_html = ch.get("html", "")
        toc_links.append(f'<li><a href="#ch_{idx}">{html.escape(ch_title)}</a></li>')
        chapters_content.append(f"""
<div id="ch_{idx}">
  <h1 style="page-break-before:always; text-align:center;">{html.escape(ch_title)}</h1>
  {ch_html}
</div>
""")

    mobi_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>{html.escape(title)}</title>
</head>
<body style="font-family:serif; line-height:1.45; text-align:justify;">
  <div style="text-align:center; margin-bottom:2em;">
    <h1 style="margin-top:1em;">{html.escape(title)}</h1>
    <h3>Por: {html.escape(author)}</h3>
  </div>
  <div style="page-break-before:always;">
    <h2>Sumário</h2>
    <ul>
      {"".join(toc_links)}
    </ul>
  </div>
  {"".join(chapters_content)}
</body>
</html>"""

    html_bytes = mobi_html.encode("utf-8")
    chunks = [html_bytes[i:i + 4096] for i in range(0, len(html_bytes), 4096)] or [b""]

    # 1. PalmDOC header (16 bytes)
    palmdoc_hdr = struct.pack(">HHIHHI", 1, 0, len(html_bytes), len(chunks), 4096, 0)

    # 2. MOBI header (232 bytes)
    header_len = 232
    mobi_hdr = bytearray(header_len)
    mobi_hdr[0:4] = b"MOBI"
    struct.pack_into(">IIII", mobi_hdr, 4, header_len, 2, 65001, int(time.time()))
    struct.pack_into(">I", mobi_hdr, 20, 6)  # Versão MOBI 6

    first_non_book_record = len(chunks) + 1
    struct.pack_into(">I", mobi_hdr, 80, first_non_book_record)

    title_bytes = title.encode("utf-8")
    title_offset = len(palmdoc_hdr) + header_len
    struct.pack_into(">II", mobi_hdr, 84, title_offset, len(title_bytes))

    # EXTH header para metadados (Título e Autor)
    exth_records = [
        (100, author.encode("utf-8")),  # Autor
        (503, title_bytes),             # Título
    ]
    exth_body = bytearray()
    for rec_type, rec_val in exth_records:
        rec_len = 8 + len(rec_val)
        exth_body.extend(struct.pack(">II", rec_type, rec_len))
        exth_body.extend(rec_val)

    pad_len = (4 - (len(exth_body) % 4)) % 4
    exth_body.extend(b"\x00" * pad_len)
    exth_header = b"EXTH" + struct.pack(">II", 12 + len(exth_body), len(exth_records)) + exth_body

    # Ativa flag EXTH no cabeçalho MOBI (bit 6 do offset 128)
    struct.pack_into(">I", mobi_hdr, 128, 0x40)

    record0 = palmdoc_hdr + bytes(mobi_hdr) + title_bytes + exth_header

    records = [record0] + chunks

    # Se houver capa, adiciona como registro de imagem
    if cover_image_path and cover_image_path.exists():
        with open(cover_image_path, "rb") as fc:
            records.append(fc.read())

    records.append(b"\xe9\x8e\r\n")  # Registro EOF delimitador

    # Palm Database Header
    pdb_name = title[:31].encode("ascii", errors="replace").ljust(32, b"\x00")
    num_records = len(records)
    c_time = int(time.time())
    header = struct.pack(
        ">32sHHIIIIII4s4sIIH",
        pdb_name, 0, 0, c_time, c_time, 0,
        0, 0, 0, b"BOOK", b"MOBI",
        num_records, 0, num_records,
    )

    record_list_size = num_records * 8 + 2
    curr_offset = len(header) + record_list_size

    rec_list = bytearray()
    for idx, r in enumerate(records):
        rec_list.extend(struct.pack(">I", curr_offset))
        rec_list.extend(struct.pack(">B", 0))
        rec_list.extend(struct.pack(">BBB", (idx >> 16) & 0xFF, (idx >> 8) & 0xFF, idx & 0xFF))
        curr_offset += len(r)
    rec_list.extend(b"\x00\x00")

    with open(out_path, "wb") as f_out:
        f_out.write(header + bytes(rec_list) + b"".join(records))


def execute_pdf_to_kindle(
    session_dir: Path,
    file_id: str,
    output_format: str = "epub",
    custom_title: Optional[str] = None,
    custom_author: Optional[str] = None,
    output_basename: Optional[str] = None,
    force_fixed_layout: bool = False,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Motor principal de conversão de PDF para formato Kindle (.epub / .mobi).
    Orquestra análise, extração de capa, reflow de texto, estruturação de capítulos
    e compilação do e-book.
    """
    t0 = time.time()
    if job_id:
        update_kindle_job(job_id, 5, "Iniciando análise do PDF e validação de segurança...")

    safe_name = Path(file_id).name
    file_path = session_dir / safe_name
    if not file_path.exists() and (session_dir / "output" / safe_name).exists():
        file_path = session_dir / "output" / safe_name
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo '{file_id}' não encontrado na sessão.")

    # 1. Validação de senha / criptografia (Cenário 2)
    check_pdf_encryption(file_path)

    doc = pymupdf.open(str(file_path))
    try:
        total_pages = len(doc)
        if total_pages == 0:
            raise ValueError("O documento PDF está vazio.")

        meta = doc.metadata or {}
        raw_title = custom_title or meta.get("title") or file_path.stem.replace("_", " ").replace("-", " ").title()
        raw_author = custom_author or meta.get("author") or "Autor Desconhecido"
        title = raw_title.strip() or "E-book Kindle"
        author = raw_author.strip() or "Autor Desconhecido"

        output_dir = session_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        clean_stem = (output_basename or file_path.stem).strip()
        clean_stem = Path(clean_stem).stem

        fmt = output_format.lower().strip()
        if fmt not in ["epub", "mobi"]:
            fmt = "epub"

        out_filename = f"{clean_stem}.{fmt}"
        out_path = output_dir / out_filename

        # 2. Extração de Capa (cover.jpg) da Página 1 (RN-03)
        if job_id:
            update_kindle_job(job_id, 20, "Extraindo primeira página como imagem de capa (cover.jpg)...")

        cover_path = session_dir / f"cover_{uuid.uuid4().hex[:6]}.jpg"
        extract_cover_image(doc, cover_path)

        # 3. Análise de cabeçalhos/rodapés repetitivos (RN-02)
        if job_id:
            update_kindle_job(job_id, 35, "Analisando estrutura de páginas e cabeçalhos repetitivos...")

        repeated_headers, repeated_footers = detect_repeated_headers_footers(doc)

        # 4. Extração de Capítulos / Bookmarks
        pdf_toc = doc.get_toc()  # [[lvl, title, page], ...]
        chapters: List[Dict[str, Any]] = []

        # Se for PDF puramente escaneado sem OCR e o usuário solicitou layout fixo
        if force_fixed_layout:
            if job_id:
                update_kindle_job(job_id, 50, "Processando páginas em layout fixo de alta fidelidade...")

            for page_idx in range(total_pages):
                page = doc[page_idx]
                mat = pymupdf.Matrix(1.5, 1.5)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Salva imagem da página
                img_path = session_dir / f"page_{page_idx + 1}.jpg"
                img.save(str(img_path), "JPEG", quality=85)
                
                page_html = f"""<div class="fixed-page-container">
  <img src="images/page_{page_idx + 1}.jpg" alt="Página {page_idx + 1}" class="fixed-page-image"/>
</div>"""
                chapters.append({
                    "title": f"Página {page_idx + 1}",
                    "html": page_html,
                    "image_file": img_path,
                })
        else:
            # Modo Reflow de Texto Inteligente (RN-02)
            if job_id:
                update_kindle_job(job_id, 50, "Extraindo fluxo textual, parágrafos e realizando reflow dinâmico...")

            # Mapeia marcadores para páginas se existirem
            page_to_chapter_title: Dict[int, str] = {}
            for item in pdf_toc:
                if len(item) >= 3:
                    lvl, c_title, c_page = item[0], item[1], item[2]
                    # PyMuPDF usa 1-based para TOC
                    c_page_idx = max(0, c_page - 1)
                    if c_page_idx not in page_to_chapter_title:
                        page_to_chapter_title[c_page_idx] = c_title

            current_chapter_title = page_to_chapter_title.get(0) or "Início"
            current_chapter_html_parts: List[str] = []

            for page_idx in range(total_pages):
                if job_id and total_pages > 1:
                    pct = 50 + int((page_idx / total_pages) * 35)
                    update_kindle_job(job_id, pct, f"Processando página {page_idx + 1} de {total_pages}...")

                # Verifica se esta página inicia um novo capítulo baseado em marcadores
                if page_idx in page_to_chapter_title and page_idx > 0:
                    if current_chapter_html_parts:
                        chapters.append({
                            "title": current_chapter_title,
                            "html": "\n".join(current_chapter_html_parts),
                        })
                        current_chapter_html_parts = []
                    current_chapter_title = page_to_chapter_title[page_idx]

                page = doc[page_idx]
                page_h = page.rect.height
                blocks = page.get_text("blocks")
                ordered_blocks = clean_and_reflow_blocks(blocks, page_h, repeated_headers, repeated_footers)

                page_text_pieces = []
                for b in ordered_blocks:
                    raw_text = b["raw_text"]
                    p_html = reflow_text_to_html_paragraphs(raw_text)
                    if p_html:
                        page_text_pieces.append(p_html)

                if page_text_pieces:
                    current_chapter_html_parts.append("\n".join(page_text_pieces))

            # Adiciona o último capítulo
            if current_chapter_html_parts:
                chapters.append({
                    "title": current_chapter_title,
                    "html": "\n".join(current_chapter_html_parts),
                })

            # Se não detectou nenhum texto ou capítulos vazios, cria capítulo de fallback
            if not chapters or not any(c.get("html") for c in chapters):
                chapters = [{
                    "title": title,
                    "html": "<p>O documento PDF não possui texto editável extraível ou consiste primariamente em imagens.</p>",
                }]

        # 5. Compilação do arquivo de saída (.epub ou .mobi) (RN-01)
        if job_id:
            update_kindle_job(job_id, 90, f"Compilando e-book no formato {fmt.upper()} otimizado para Kindle...")

        if fmt == "mobi":
            build_mobi_file(
                out_path=out_path,
                title=title,
                author=author,
                cover_image_path=cover_path,
                chapters=chapters,
            )
        else:
            build_epub_file(
                out_path=out_path,
                title=title,
                author=author,
                cover_image_path=cover_path,
                chapters=chapters,
            )

        elapsed = time.time() - t0
        filesize = out_path.stat().st_size

        metrics = {
            "output_filename": out_filename,
            "format": fmt,
            "title": title,
            "author": author,
            "filesize": filesize,
            "total_pages": total_pages,
            "chapters_count": len(chapters),
            "duration_seconds": round(elapsed, 3),
            "has_cover": cover_path.exists(),
            "is_fixed_layout": force_fixed_layout,
        }

        if job_id:
            update_kindle_job(job_id, 100, "Conversão concluída com sucesso!", status="completed", result=metrics)

        logger.info(
            f"PDF convertido para Kindle ({fmt.upper()}) com sucesso: '{out_filename}', "
            f"{filesize} bytes em {elapsed:.2f}s"
        )

        return metrics
    except Exception as e:
        logger.error(f"Erro na conversão PDF para Kindle: {e}", exc_info=True)
        if job_id:
            update_kindle_job(job_id, 0, "Falha na conversão", status="error", error=str(e))
        raise
    finally:
        doc.close()
