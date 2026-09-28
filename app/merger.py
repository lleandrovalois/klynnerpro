"""
Motor de unificação de PDFs de alta performance com suporte a Menu de Documentos.
Gera tanto a Página Inicial de Menu Visual (com links clicáveis)
quanto o Menu de Navegação Lateral (Marcadores/Outlines com abertura automática UseOutlines).
"""

import io
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import pikepdf
import pypdf
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

logger = logging.getLogger("pdf_merger")


def generate_visual_menu_pdf(
    items: List[Dict[str, Any]],
    output_title: str = "Menu de Documentos"
) -> Tuple[io.BytesIO, List[Tuple[int, Tuple[float, float, float, float]]]]:
    """
    Cria uma página (ou múltiplas páginas) estilizada de Menu / Sumário Visual usando ReportLab.
    Retorna o buffer do PDF gerado e a lista com (page_index_do_menu, retangulo_clicavel).
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    # 13 itens por página para manter espaçamento generoso e legível
    items_per_page = 13
    total_pages = max(1, (len(items) + items_per_page - 1) // items_per_page)

    click_rects = []  # Tuplas de (menu_page_idx, (x1, y1, x2, y2))

    for page_idx in range(total_pages):
        start_idx = page_idx * items_per_page
        end_idx = min(start_idx + items_per_page, len(items))
        page_items = items[start_idx:end_idx]

        # Fundo branco limpo
        c.setFillColor(colors.HexColor("#FFFFFF"))
        c.rect(0, 0, width, height, fill=True, stroke=False)

        # Barra de Cabeçalho Superior
        c.setFillColor(colors.HexColor("#0F172A"))
        c.rect(0, height - 95, width, 95, fill=True, stroke=False)

        # Linha de destaque gradiente/violeta abaixo do cabeçalho
        c.setFillColor(colors.HexColor("#6366F1"))
        c.rect(0, height - 98, width, 3, fill=True, stroke=False)

        # Título do Menu
        c.setFillColor(colors.HexColor("#FFFFFF"))
        c.setFont("Helvetica-Bold", 20)
        c.drawString(45, height - 48, output_title)

        # Subtítulo explicativo
        c.setFillColor(colors.HexColor("#94A3B8"))
        c.setFont("Helvetica", 10)
        page_indicator = f" • Página {page_idx + 1} de {total_pages}" if total_pages > 1 else ""
        c.drawString(
            45,
            height - 70,
            f"Sumário Interativo • {len(items)} arquivos unificados • Clique no item para navegar{page_indicator}"
        )

        y = height - 145
        item_height = 42

        for i, item in enumerate(page_items):
            item_global_idx = start_idx + i + 1
            num_str = f"{item_global_idx:02d}"
            title = str(item.get("title") or f"Documento {item_global_idx}")
            target_page_display = item.get("target_page_display", 1)
            num_pages = item.get("pages_count", 0)

            # Card de fundo do item
            c.setFillColor(colors.HexColor("#F8FAFC"))
            c.setStrokeColor(colors.HexColor("#E2E8F0"))
            c.setLineWidth(0.8)
            card_x1 = 40
            card_y1 = y
            card_x2 = width - 40
            card_y2 = y + item_height - 6
            c.roundRect(card_x1, card_y1, card_x2 - card_x1, card_y2 - card_y1, 6, fill=True, stroke=True)

            # Badge do Número (Ícone circular/quadrado arredondado)
            c.setFillColor(colors.HexColor("#6366F1"))
            c.roundRect(50, y + 6, 26, 24, 4, fill=True, stroke=False)
            c.setFillColor(colors.HexColor("#FFFFFF"))
            c.setFont("Helvetica-Bold", 10)
            c.drawCentredString(63, y + 13, num_str)

            # Nome do Arquivo / Título do Menu (truncado caso seja muito longo)
            c.setFillColor(colors.HexColor("#0F172A"))
            c.setFont("Helvetica-Bold", 10.5)
            clean_title = title if len(title) <= 60 else title[:57] + "..."
            c.drawString(86, y + 18, clean_title)

            # Sub-info: Páginas do documento individual
            if num_pages > 0:
                c.setFillColor(colors.HexColor("#64748B"))
                c.setFont("Helvetica", 8.5)
                c.drawString(86, y + 7, f"{num_pages} página{'s' if num_pages > 1 else ''}")

            # Indicador da Página de Destino
            c.setFillColor(colors.HexColor("#4F46E5"))
            c.setFont("Helvetica-Bold", 10)
            page_text = f"Pág. {target_page_display}"
            c.drawRightString(width - 55, y + 14, page_text)

            # Seta sutil de navegação
            c.setFillColor(colors.HexColor("#94A3B8"))
            c.setFont("Helvetica", 11)
            c.drawString(width - 50, y + 14, "›")

            # Salva o retângulo clicável para anotação de link do PDF
            click_rects.append((page_idx, (card_x1, card_y1, card_x2, card_y2)))

            y -= item_height

        # Rodapé da Página de Menu
        c.setFillColor(colors.HexColor("#94A3B8"))
        c.setFont("Helvetica", 8.5)
        c.drawString(45, 30, "Klynner PDF • Gerado com motor C++/QPDF de alta performance")

        c.showPage()

    c.save()
    buf.seek(0)
    return buf, click_rects


def merge_pdfs_pikepdf(
    ordered_files_info: List[Dict[str, Any]],
    output_path: Path,
    create_visual_menu: bool = True,
    add_bookmarks: bool = True,
    linearize: bool = True,
) -> Dict:
    """
    Unificação ultra-rápida com motor QPDF via pikepdf.
    Gera:
      1. Página Inicial de Menu / Sumário (se create_visual_menu=True) com hiperlinks funcionais.
      2. Menu Lateral de Navegação (Outlines/Marcadores) com /PageMode /UseOutlines ativo.
    """
    start_time = time.perf_counter()
    total_original_bytes = sum(
        f["path"].stat().st_size for f in ordered_files_info if f["path"].exists()
    )

    # 1. Primeiro passo: Mede quantas páginas tem cada arquivo original
    # Usando abertura sob demanda rápida sem carregar conteúdo
    file_page_counts = []
    for item in ordered_files_info:
        file_path = item["path"]
        try:
            with pikepdf.open(file_path) as src:
                file_page_counts.append(len(src.pages))
        except Exception:
            file_page_counts.append(1)

    # 2. Se for criar o menu visual, determina quantas páginas de menu serão necessárias
    items_per_menu_page = 13
    num_files = len(ordered_files_info)
    menu_pages_count = max(1, (num_files + items_per_menu_page - 1) // items_per_menu_page) if create_visual_menu else 0

    # 3. Calcula a página inicial exata de cada arquivo no documento unificado
    # Páginas são 1-indexadas para exibição visual
    menu_items_data = []
    current_page_counter = menu_pages_count + 1

    for idx, item in enumerate(ordered_files_info):
        p_count = file_page_counts[idx]
        title = item.get("menu_title") or item["path"].stem
        menu_items_data.append({
            "title": title,
            "target_page_display": current_page_counter,
            "target_page_idx": current_page_counter - 1,  # 0-indexed para pikepdf
            "pages_count": p_count,
            "path": item["path"],
        })
        current_page_counter += p_count

    # 4. Cria o PDF final
    merged_pdf = pikepdf.Pdf.new()

    # Se ativado, gera a página de menu visual e insere no início
    click_rects = []
    if create_visual_menu:
        menu_buf, click_rects = generate_visual_menu_pdf(menu_items_data)
        with pikepdf.open(menu_buf) as menu_pdf:
            merged_pdf.pages.extend(menu_pdf.pages)

    # 5. Concatena os arquivos originais
    for item in ordered_files_info:
        file_path = item["path"]
        if not file_path.exists():
            continue
        with pikepdf.open(file_path) as src_doc:
            merged_pdf.pages.extend(src_doc.pages)

    total_pages = len(merged_pdf.pages)

    # 6. Adiciona os Hiperlinks clicáveis na Página de Menu
    if create_visual_menu and click_rects:
        for i, (menu_page_idx, rect) in enumerate(click_rects):
            if i < len(menu_items_data):
                target_page_idx = menu_items_data[i]["target_page_idx"]
                if target_page_idx < total_pages:
                    target_page_obj = merged_pdf.pages[target_page_idx]
                    
                    # Cria a anotação /Link compatível com o padrão ISO 32000 (PDF)
                    link_annot = pikepdf.Dictionary(
                        Type=pikepdf.Name.Annot,
                        Subtype=pikepdf.Name.Link,
                        Rect=pikepdf.Array(list(rect)),
                        Dest=pikepdf.Array([target_page_obj.obj, pikepdf.Name.Fit]),
                        Border=pikepdf.Array([0, 0, 0])
                    )
                    
                    target_menu_page = merged_pdf.pages[menu_page_idx]
                    if "/Annots" not in target_menu_page:
                        target_menu_page.Annots = merged_pdf.make_indirect(pikepdf.Array())
                    target_menu_page.Annots.append(merged_pdf.make_indirect(link_annot))

    # 7. Constrói o Menu Lateral de Navegação (Marcadores / Outlines)
    if add_bookmarks:
        try:
            with merged_pdf.open_outline() as outline:
                # Se tiver página de menu, cria item para o próprio Menu
                if create_visual_menu:
                    outline.root.append(pikepdf.OutlineItem("Menu Principal / Sumário", 0))

                # Cria um item de menu para cada arquivo unificado
                for m_item in menu_items_data:
                    title = m_item["title"]
                    target_idx = m_item["target_page_idx"]
                    if target_idx < total_pages:
                        outline.root.append(pikepdf.OutlineItem(title, target_idx))
        except Exception as e:
            logger.warning(f"Erro ao gerar marcadores de navegação: {e}")

    # 8. Ativa a abertura automática do Menu Lateral ao abrir o documento
    # /PageMode /UseOutlines instrui visualizadores (Acrobat, Edge, Chrome) a abrir o menu na lateral esquerda
    merged_pdf.Root.PageMode = pikepdf.Name.UseOutlines

    # Salva o arquivo no disco com Fast Web View
    merged_pdf.save(
        output_path,
        linearize=linearize,
        compress_streams=True,
    )
    merged_pdf.close()

    duration = time.perf_counter() - start_time
    merged_bytes = output_path.stat().st_size if output_path.exists() else 0

    return {
        "success": True,
        "engine": "PikePDF (Motor QPDF de Alta Performance)",
        "total_files": len(ordered_files_info),
        "total_pages": total_pages,
        "original_bytes": total_original_bytes,
        "merged_bytes": merged_bytes,
        "duration_seconds": round(duration, 3),
        "linearized": linearize,
        "menu_created": create_visual_menu,
        "menu_items": [item["title"] for item in menu_items_data],
    }


def merge_pdfs_pypdf_fallback(
    ordered_files_info: List[Dict[str, Any]],
    output_path: Path,
    add_bookmarks: bool = True,
) -> Dict:
    """
    Fallback usando pypdf para arquivos com corrupções que impeçam parsing estrito.
    """
    start_time = time.perf_counter()
    total_original_bytes = sum(
        f["path"].stat().st_size for f in ordered_files_info if f["path"].exists()
    )

    merger = pypdf.PdfMerger(strict=False)

    for item in ordered_files_info:
        file_path = item["path"]
        if not file_path.exists():
            continue
        title = item.get("menu_title") or file_path.stem
        merger.append(str(file_path), outline_item=title if add_bookmarks else None)

    with open(output_path, "wb") as f_out:
        merger.write(f_out)
    merger.close()

    total_pages = 0
    try:
        reader = pypdf.PdfReader(str(output_path))
        total_pages = len(reader.pages)
    except Exception:
        pass

    duration = time.perf_counter() - start_time
    merged_bytes = output_path.stat().st_size if output_path.exists() else 0

    return {
        "success": True,
        "engine": "PyPDF (Motor de Tolerância Fallback)",
        "total_files": len(ordered_files_info),
        "total_pages": total_pages,
        "original_bytes": total_original_bytes,
        "merged_bytes": merged_bytes,
        "duration_seconds": round(duration, 3),
        "linearized": False,
        "menu_created": False,
        "menu_items": [item.get("menu_title") or item["path"].stem for item in ordered_files_info],
    }


def execute_pdf_merge(
    ordered_files_info: List[Dict[str, Any]],
    output_file_path: Path,
    create_visual_menu: bool = True,
    add_bookmarks: bool = True,
    linearize: bool = True,
) -> Dict:
    """
    Ponto de entrada principal para fusão com suporte a Menu de Documentos.
    """
    if not ordered_files_info:
        raise ValueError("Nenhum arquivo fornecido para unificação.")

    output_file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        return merge_pdfs_pikepdf(
            ordered_files_info=ordered_files_info,
            output_path=output_file_path,
            create_visual_menu=create_visual_menu,
            add_bookmarks=add_bookmarks,
            linearize=linearize,
        )
    except Exception as primary_error:
        logger.warning(
            f"Motor principal (pikepdf) encontrou erro: {primary_error}. Tentando fallback pypdf..."
        )
        try:
            return merge_pdfs_pypdf_fallback(
                ordered_files_info=ordered_files_info,
                output_path=output_file_path,
                add_bookmarks=add_bookmarks,
            )
        except Exception as fallback_error:
            raise RuntimeError(
                f"Falha ao unificar os PDFs: {primary_error} / Fallback: {fallback_error}"
            )
