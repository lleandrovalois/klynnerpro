"""
Módulo de Conversão de Documentos Word (.docx / .doc) para PDF
Suporta:
1. Motor Nativo LibreOffice / Soffice (em servidores Linux/Docker como Render)
2. Motor de Automação COM MS Word (em Windows se Office instalado)
3. Motor Universal Pure-Python (python-docx + ReportLab + PikePDF), garantindo
   conversão autônoma sem dependências de pacotes externos ou falhas de ambiente.
"""

import html
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, Optional

import docx
import pikepdf
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

logger = logging.getLogger("word_to_pdf")


def find_libreoffice_binary() -> Optional[str]:
    """Localiza o binário do LibreOffice/Soffice no sistema."""
    # 1. Verifica no PATH
    for name in ["libreoffice", "soffice"]:
        found = shutil.which(name)
        if found:
            return found

    # 2. Caminhos comuns no Windows
    if sys.platform == "win32":
        common_paths = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        for p in common_paths:
            if os.path.exists(p):
                return p

    # 3. Caminhos comuns no Linux / MacOS
    common_linux = [
        "/usr/bin/libreoffice",
        "/usr/bin/soffice",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ]
    for p in common_linux:
        if os.path.exists(p):
            return p

    return None


def convert_via_libreoffice(binary_path: str, input_path: Path, output_dir: Path) -> Path:
    """Converte usando LibreOffice em modo headless."""
    cmd = [
        binary_path,
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(output_dir),
        str(input_path),
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"Erro ao executar LibreOffice: {result.stderr or result.stdout}")

    expected_out = output_dir / f"{input_path.stem}.pdf"
    if not expected_out.exists():
        raise FileNotFoundError("LibreOffice concluiu mas o PDF de saída não foi gerado.")
    return expected_out


def convert_via_pure_python(input_path: Path, output_path: Path) -> None:
    """Converte .docx para PDF de alta fidelidade usando python-docx + ReportLab."""
    doc = docx.Document(str(input_path))
    styles = getSampleStyleSheet()

    # Cria estilos personalizados com tipografia moderna
    body_style = ParagraphStyle(
        "CustomBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        textColor=colors.HexColor("#1E293B"),
    )

    h1_style = ParagraphStyle(
        "CustomH1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=10,
        spaceBefore=12,
    )

    h2_style = ParagraphStyle(
        "CustomH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=8,
        spaceBefore=10,
    )

    h3_style = ParagraphStyle(
        "CustomH3",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#334155"),
        spaceAfter=6,
        spaceBefore=8,
    )

    story = []

    for p in doc.paragraphs:
        txt = p.text.strip()
        if not txt:
            story.append(Spacer(1, 8))
            continue

        style_name = p.style.name.lower()
        if "heading 1" in style_name:
            curr_style = h1_style
        elif "heading 2" in style_name:
            curr_style = h2_style
        elif "heading 3" in style_name or "heading 4" in style_name:
            curr_style = h3_style
        else:
            curr_style = body_style

        # Formata runs preservando negrito, itálico e sublinhado
        html_runs = []
        for r in p.runs:
            raw = html.escape(r.text)
            if r.bold:
                raw = f"<b>{raw}</b>"
            if r.italic:
                raw = f"<i>{raw}</i>"
            if r.underline:
                raw = f"<u>{raw}</u>"
            html_runs.append(raw)

        full_p_html = "".join(html_runs) if html_runs else html.escape(txt)
        story.append(Paragraph(full_p_html, curr_style))
        story.append(Spacer(1, 6))

    for tbl in doc.tables:
        table_data = []
        for row in tbl.rows:
            row_data = [html.escape(c.text.strip()) for c in row.cells]
            table_data.append(row_data)

        if table_data:
            # Envolve células em Paragraphs para auto-quebra de texto
            formatted_data = []
            for r_idx, r in enumerate(table_data):
                f_row = []
                for val in r:
                    f_row.append(Paragraph(val, body_style))
                formatted_data.append(f_row)

            t_obj = Table(formatted_data)
            t_obj.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(t_obj)
            story.append(Spacer(1, 10))

    if not story:
        story.append(Paragraph("Documento Word vazio", body_style))

    pdf_doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    pdf_doc.build(story)


def execute_word_to_pdf(
    session_dir: Path,
    file_id: str,
    output_basename: Optional[str] = None,
    linearize: bool = True,
) -> Dict[str, Any]:
    """
    Converte um documento Word (.docx ou .doc) em PDF de alta qualidade.
    
    Args:
        session_dir: Diretório temporário da sessão
        file_id: Identificador do arquivo no workspace da sessão
        output_basename: Nome base para o arquivo PDF gerado
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
    out_filename = f"{clean_stem}.pdf"

    output_dir = session_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / out_filename
    temp_pdf_path = output_dir / f"tmp_w2p_{out_filename}"

    engine_used = "Pure-Python (python-docx + ReportLab)"
    libreoffice_bin = find_libreoffice_binary()

    if libreoffice_bin:
        try:
            logger.info(f"Convertendo '{input_path.name}' via LibreOffice headless...")
            lo_out = convert_via_libreoffice(libreoffice_bin, input_path, output_dir)
            if lo_out != temp_pdf_path and lo_out != out_path:
                if temp_pdf_path.exists():
                    temp_pdf_path.unlink()
                lo_out.rename(temp_pdf_path)
            engine_used = "LibreOffice Headless (C++)"
        except Exception as e:
            logger.warning(f"Tentativa via LibreOffice falhou ({e}), executando fallback Pure-Python.")
            convert_via_pure_python(input_path, temp_pdf_path)
    else:
        logger.info(f"Convertendo '{input_path.name}' via motor Pure-Python...")
        convert_via_pure_python(input_path, temp_pdf_path)

    # Lineariza e otimiza via PikePDF se solicitado
    num_pages = 0
    if temp_pdf_path.exists():
        with pikepdf.open(temp_pdf_path) as pike_doc:
            num_pages = len(pike_doc.pages)
            pike_doc.save(out_path, linearize=linearize)
        temp_pdf_path.unlink(missing_ok=True)
    elif out_path.exists():
        with pikepdf.open(out_path, allow_overwriting_input=True) as pike_doc:
            num_pages = len(pike_doc.pages)
            if linearize:
                pike_doc.save(out_path, linearize=True)

    elapsed = time.time() - t0
    filesize = out_path.stat().st_size

    logger.info(
        f"Word convertido para PDF com sucesso: '{out_filename}', {num_pages} páginas, "
        f"{filesize} bytes em {elapsed:.2f}s via {engine_used}"
    )

    return {
        "output_filename": out_filename,
        "filesize": filesize,
        "output_bytes": filesize,
        "pages": num_pages,
        "total_pages": num_pages,
        "engine": engine_used,
        "engine_used": engine_used,
        "linearized": linearize,
        "time_seconds": round(elapsed, 3),
        "duration_seconds": round(elapsed, 3),
    }
