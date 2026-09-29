"""
Módulo de Remoção de Rodapé, Cabeçalho e Numeração de Páginas em Arquivos PDF.
Utiliza PyMuPDF (fitz) para expurgo físico de dados (redaction) e PikePDF para otimização e linearização.
"""

import logging
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF
import pikepdf

logger = logging.getLogger("footer_remover")


def parse_page_selection(pages_str: str, total_pages: int, skip_first_page: bool = False) -> List[int]:
    """
    Retorna a lista de índices de página (0-based) a serem processados.
    Suporta 'all', 'first', ou intervalos '1-5, 8, 10-12'.
    """
    clean_str = (pages_str or "all").strip().lower()
    selected_indices: set[int] = set()

    if clean_str in ("all", "*", ""):
        selected_indices = set(range(total_pages))
    elif clean_str == "first":
        selected_indices = {0}
    else:
        tokens = [t.strip() for t in clean_str.split(",") if t.strip()]
        for token in tokens:
            m_range = re.match(r"^(\d+)\s*-\s*(\d+)$", token)
            if m_range:
                start_p = int(m_range.group(1))
                end_p = int(m_range.group(2))
                if start_p > end_p:
                    start_p, end_p = end_p, start_p
                start_idx = max(0, min(start_p - 1, total_pages - 1))
                end_idx = max(0, min(end_p - 1, total_pages - 1))
                for i in range(start_idx, end_idx + 1):
                    selected_indices.add(i)
            else:
                m_single = re.match(r"^(\d+)$", token)
                if m_single:
                    p = int(m_single.group(1))
                    if 1 <= p <= total_pages:
                        selected_indices.add(p - 1)

    if skip_first_page and 0 in selected_indices:
        selected_indices.remove(0)

    result = sorted(list(selected_indices))
    return result


def parse_fill_color(fill_color: str) -> Optional[Tuple[float, float, float]]:
    """Converte string de cor hex ou 'transparent' para tupla RGB fitz."""
    if not fill_color or fill_color.lower() in ("transparent", "none"):
        return None
    clean = fill_color.strip().lstrip("#")
    if len(clean) == 6:
        try:
            r = int(clean[0:2], 16) / 255.0
            g = int(clean[2:4], 16) / 255.0
            b = int(clean[4:6], 16) / 255.0
            return (r, g, b)
        except ValueError:
            pass
    return (1.0, 1.0, 1.0)  # Branco por padrão


def execute_pdf_remove_footer(
    session_dir: Path,
    file_id: str,
    mode: str = "margin",  # "margin" | "text" | "both"
    target_area: str = "footer",  # "footer" | "header" | "both"
    margin_height: float = 35.0,  # Altura da faixa em pontos
    fill_color: str = "#FFFFFF",
    custom_text: Optional[str] = None,
    remove_page_numbers: bool = False,
    skip_first_page: bool = False,
    pages: str = "all",
    output_basename: Optional[str] = None,
    linearize: bool = True,
) -> Dict[str, Any]:
    """
    Remove fisicamente rodapé, cabeçalho ou numeração de páginas de um arquivo PDF.
    
    Args:
        session_dir: Diretório de trabalho da sessão
        file_id: Nome do arquivo original na sessão
        mode: 'margin' (limpa a faixa inteira), 'text' (limpa textos específicos) ou 'both'
        target_area: 'footer', 'header' ou 'both'
        margin_height: Altura da margem em pontos (ex: 35pt ~ 1.2cm)
        fill_color: Cor de preenchimento ('#FFFFFF' ou 'transparent')
        custom_text: Texto ou frase específica para buscar e expurgar
        remove_page_numbers: Se True, detecta e expurga padrões de número de página na faixa
        skip_first_page: Preserva a primeira página (útil para capa)
        pages: Intervalos de páginas ou 'all'
        output_basename: Nome do arquivo PDF gerado
        linearize: Otimiza com Fast Web View
    """
    start_time = time.perf_counter()
    input_path = session_dir / file_id
    if not input_path.exists():
        input_path = session_dir / "uploads" / file_id
    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo de entrada não encontrado: {file_id}")

    output_dir = session_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not output_basename:
        base_stem = Path(file_id).stem
        clean_name = f"{base_stem}_sem_rodape.pdf"
    else:
        clean_name = output_basename if output_basename.endswith(".pdf") else f"{output_basename}.pdf"

    temp_output_path = output_dir / f"tmp_rf_{clean_name}"
    final_output_path = output_dir / clean_name

    rgb_fill = parse_fill_color(fill_color)
    redact_count = 0

    try:
        doc = fitz.open(str(input_path))
        total_pages = len(doc)
        target_indices = parse_page_selection(pages, total_pages, skip_first_page=skip_first_page)

        # Regex para identificar padrões comuns de paginação em rodapé:
        # Ex: '1', 'Página 1', 'Pag. 1 de 10', '1/10', 'Page 1 of 5'
        page_num_regex = re.compile(
            r"^(?:p[aá]g(?:ina)?\.?|page)?\s*\d+\s*(?:(?:de|\/|of)\s*\d+)?$",
            re.IGNORECASE
        )

        for page_idx in target_indices:
            page = doc[page_idx]
            page_rect = page.rect
            page_w = page_rect.width
            page_h = page_rect.height

            # Faixas de interesse (rodapé = parte inferior; cabeçalho = parte superior)
            footer_rect = fitz.Rect(0, max(0, page_h - margin_height), page_w, page_h)
            header_rect = fitz.Rect(0, 0, page_w, min(page_h, margin_height))

            # 1. Modo por Margem (Faixa Completa)
            if mode in ("margin", "both"):
                if target_area in ("footer", "both"):
                    annot = page.add_redact_annot(footer_rect, fill=rgb_fill)
                    if annot:
                        redact_count += 1
                if target_area in ("header", "both"):
                    annot = page.add_redact_annot(header_rect, fill=rgb_fill)
                    if annot:
                        redact_count += 1

            # 2. Modo por Texto / Numeração Cirúrgica
            if mode in ("text", "both"):
                search_clips = []
                if target_area in ("footer", "both"):
                    # Faixa ampliada para busca de texto no rodapé (inferior 25%)
                    search_clips.append(fitz.Rect(0, page_h * 0.75, page_w, page_h))
                if target_area in ("header", "both"):
                    # Faixa ampliada para busca no cabeçalho (superior 20%)
                    search_clips.append(fitz.Rect(0, 0, page_w, page_h * 0.20))

                for clip in search_clips:
                    # Busca texto customizado exato (ex: "Klynner PDF ...")
                    if custom_text and custom_text.strip():
                        matched_rects = page.search_for(custom_text.strip(), clip=clip)
                        for mr in matched_rects:
                            # Pequeno padding de 1pt para corte limpo
                            expanded_rect = fitz.Rect(mr.x0 - 1, mr.y0 - 1, mr.x1 + 1, mr.y1 + 1)
                            page.add_redact_annot(expanded_rect, fill=rgb_fill)
                            redact_count += 1

                    # Busca numeração de páginas por palavras
                    if remove_page_numbers:
                        words = page.get_text("words", clip=clip)
                        # words formato: (x0, y0, x1, y1, word, block_no, line_no, word_no)
                        # Agrupa palavras por linha para pegar expressões como "Página 1 de 10"
                        lines_dict: Dict[int, List[Tuple[float, float, float, float, str]]] = {}
                        for w_info in words:
                            bx0, by0, bx1, by1, w_text, b_no, l_no, _ = w_info
                            line_key = (b_no * 1000) + l_no
                            if line_key not in lines_dict:
                                lines_dict[line_key] = []
                            lines_dict[line_key].append((bx0, by0, bx1, by1, w_text))

                        for l_key, w_list in lines_dict.items():
                            full_line_text = " ".join([w[4] for w in w_list]).strip()
                            if page_num_regex.match(full_line_text):
                                # Linha inteira é numeração de página
                                lx0 = min(w[0] for w in w_list) - 2
                                ly0 = min(w[1] for w in w_list) - 1
                                lx1 = max(w[2] for w in w_list) + 2
                                ly1 = max(w[3] for w in w_list) + 1
                                page.add_redact_annot(fitz.Rect(lx0, ly0, lx1, ly1), fill=rgb_fill)
                                redact_count += 1
                            else:
                                # Verifica palavras individuais (ex: número solto "12")
                                for bx0, by0, bx1, by1, w_text in w_list:
                                    if re.match(r"^\d{1,4}$", w_text):
                                        page.add_redact_annot(fitz.Rect(bx0 - 2, by0 - 1, bx1 + 2, by1 + 1), fill=rgb_fill)
                                        redact_count += 1

            # Aplica o expurgo físico permanente das anotações adicionadas nesta página
            page.apply_redactions()

        # Salva o arquivo temporário
        doc.save(str(temp_output_path), garbage=4, deflate=True)
        doc.close()

    except Exception as e:
        if temp_output_path.exists():
            temp_output_path.unlink()
        logger.error(f"Erro ao remover rodapé do PDF: {e}", exc_info=True)
        raise RuntimeError(f"Falha ao expurgar rodapé do documento: {str(e)}")

    # Otimização com PikePDF e Linearização (Fast Web View)
    try:
        if linearize:
            with pikepdf.Pdf.open(str(temp_output_path)) as p_doc:
                p_doc.save(str(final_output_path), linearize=True)
            if temp_output_path.exists():
                temp_output_path.unlink()
        else:
            if temp_output_path.exists():
                temp_output_path.replace(final_output_path)
    except Exception as e:
        logger.warning(f"Aviso na linearização PikePDF: {e}. Mantendo arquivo base.")
        if temp_output_path.exists():
            temp_output_path.replace(final_output_path)

    duration = time.perf_counter() - start_time
    file_size = final_output_path.stat().st_size if final_output_path.exists() else 0

    return {
        "success": True,
        "output_filename": clean_name,
        "output_bytes": file_size,
        "total_pages": total_pages,
        "pages_processed": len(target_indices),
        "mode": mode,
        "target_area": target_area,
        "margin_height": margin_height,
        "redact_count": redact_count,
        "duration_seconds": round(duration, 3),
    }
