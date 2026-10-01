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
    output_title: str = "Menu de Documentos",
    menu_footer_text: Optional[str] = None,
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
        footer_to_draw = menu_footer_text if menu_footer_text is not None else "Klynner PDF • Gerado com motor C++/QPDF de alta performance"
        if footer_to_draw and footer_to_draw.strip():
            c.setFillColor(colors.HexColor("#94A3B8"))
            c.setFont("Helvetica", 8.5)
            c.drawString(45, 30, footer_to_draw.strip())

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
    menu_footer_text: Optional[str] = None,
    page_order: Optional[List[Dict[str, Any]]] = None,
) -> Dict:
    """
    Unificação ultra-rápida com motor QPDF via pikepdf.
    Gera:
      1. Página Inicial de Menu / Sumário (se create_visual_menu=True) com hiperlinks funcionais.
      2. Menu Lateral de Navegação (Outlines/Marcadores) com /PageMode /UseOutlines ativo.
      3. Suporte a reorganização granular página a página entre múltiplos arquivos (page_order).
    """
    start_time = time.perf_counter()
    total_original_bytes = sum(
        f["path"].stat().st_size for f in ordered_files_info if f["path"].exists()
    )

    open_docs: Dict[str, pikepdf.Pdf] = {}

    try:
        # Abre sob demanda os arquivos para consulta
        for item in ordered_files_info:
            fp = Path(item["path"])
            if fp.exists():
                doc = pikepdf.open(fp)
                open_docs[fp.name] = doc
                open_docs[fp.stem] = doc
                open_docs[str(fp)] = doc

        use_custom_pages = page_order is not None and len(page_order) > 0

        # Calcula a estrutura e destinos do Menu de Documentos
        items_per_menu_page = 13
        num_files = len(ordered_files_info)
        menu_pages_count = max(1, (num_files + items_per_menu_page - 1) // items_per_menu_page) if create_visual_menu else 0

        menu_items_data = []

        if not use_custom_pages:
            # Modo padrão: sequência inteira de arquivos
            file_page_counts = []
            for item in ordered_files_info:
                doc = open_docs.get(item["path"].name)
                file_page_counts.append(len(doc.pages) if doc else 1)

            current_page_counter = menu_pages_count + 1
            for idx, item in enumerate(ordered_files_info):
                p_count = file_page_counts[idx]
                title = item.get("menu_title") or item["path"].stem
                menu_items_data.append({
                    "title": title,
                    "target_page_display": current_page_counter,
                    "target_page_idx": current_page_counter - 1,
                    "pages_count": p_count,
                    "path": item["path"],
                })
                current_page_counter += p_count
        else:
            # Modo organizado por páginas: localiza a primeira aparição de cada arquivo
            def match_file_action(p_act: Dict[str, Any], file_item: Dict[str, Any]) -> bool:
                fid = str(p_act.get("file_id", "") or "").strip()
                if not fid or p_act.get("is_blank"):
                    return False
                path_obj = file_item["path"]
                return (
                    fid == path_obj.name
                    or fid == path_obj.stem
                    or fid == str(path_obj)
                    or Path(fid).name == path_obj.name
                    or fid in path_obj.name
                    or path_obj.stem in fid
                )

            for item in ordered_files_info:
                matching_indices = [
                    idx for idx, p_act in enumerate(page_order)
                    if match_file_action(p_act, item)
                ]
                if matching_indices:
                    first_idx = matching_indices[0]
                    pages_cnt = len(matching_indices)
                    target_display = menu_pages_count + first_idx + 1
                    title = item.get("menu_title") or item["path"].stem
                    menu_items_data.append({
                        "title": title,
                        "target_page_display": target_display,
                        "target_page_idx": menu_pages_count + first_idx,
                        "pages_count": pages_cnt,
                        "path": item["path"],
                    })

        # Cria o PDF final
        merged_pdf = pikepdf.Pdf.new()

        # Se ativado, gera a página de menu visual e insere no início
        click_rects = []
        if create_visual_menu and menu_items_data:
            menu_buf, click_rects = generate_visual_menu_pdf(menu_items_data, menu_footer_text=menu_footer_text)
            with pikepdf.open(menu_buf) as menu_pdf:
                merged_pdf.pages.extend(menu_pdf.pages)

        if not use_custom_pages:
            # Concatena os arquivos originais inteiros
            for item in ordered_files_info:
                doc = open_docs.get(item["path"].name)
                if doc:
                    merged_pdf.pages.extend(doc.pages)
        else:
            # Insere as páginas conforme a ordem personalizada pelo usuário
            for p_act in page_order:
                if p_act.get("is_blank"):
                    blank_doc = pikepdf.Pdf.new()
                    blank_doc.add_blank_page(page_size=(595.28, 841.89))
                    merged_pdf.pages.append(blank_doc.pages[0])
                else:
                    fid = str(p_act.get("file_id", "") or "").strip()
                    src_doc = open_docs.get(fid) or open_docs.get(Path(fid).name) or open_docs.get(Path(fid).stem)
                    if not src_doc:
                        for k, d in open_docs.items():
                            if fid in k or k in fid:
                                src_doc = d
                                break
                    if not src_doc:
                        logger.warning(f"Documento fonte não encontrado para '{fid}', ignorando página.")
                        continue

                    orig_p = int(p_act.get("page", 1)) - 1
                    if 0 <= orig_p < len(src_doc.pages):
                        merged_pdf.pages.append(src_doc.pages[orig_p])
                        rot_delta = int(p_act.get("rotation", 0))
                        if rot_delta != 0:
                            last_added = merged_pdf.pages[-1]
                            curr_rot = int(last_added.get("/Rotate", 0) or 0)
                            last_added.Rotate = (curr_rot + rot_delta) % 360

        total_pages = len(merged_pdf.pages)

        # Adiciona Hiperlinks clicáveis na Página de Menu
        if create_visual_menu and click_rects:
            for i, (menu_page_idx, rect) in enumerate(click_rects):
                if i < len(menu_items_data):
                    target_page_idx = menu_items_data[i]["target_page_idx"]
                    if target_page_idx < total_pages:
                        target_page_obj = merged_pdf.pages[target_page_idx]
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

        # Menu Lateral de Navegação (Marcadores / Outlines)
        if add_bookmarks:
            try:
                with merged_pdf.open_outline() as outline:
                    if create_visual_menu:
                        outline.root.append(pikepdf.OutlineItem("Menu Principal / Sumário", 0))
                    for m_item in menu_items_data:
                        title = m_item["title"]
                        target_idx = m_item["target_page_idx"]
                        if target_idx < total_pages:
                            outline.root.append(pikepdf.OutlineItem(title, target_idx))
            except Exception as e:
                logger.warning(f"Erro ao gerar marcadores de navegação: {e}")

        merged_pdf.Root.PageMode = pikepdf.Name.UseOutlines

        merged_pdf.save(
            output_path,
            linearize=linearize,
            compress_streams=True,
        )
        merged_pdf.close()

    finally:
        for doc in set(open_docs.values()):
            try:
                doc.close()
            except Exception:
                pass

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
    page_order: Optional[List[Dict[str, Any]]] = None,
) -> Dict:
    """
    Fallback usando pypdf para arquivos com corrupções que impeçam parsing estrito.
    """
    start_time = time.perf_counter()
    total_original_bytes = sum(
        f["path"].stat().st_size for f in ordered_files_info if f["path"].exists()
    )

    use_custom_pages = page_order is not None and len(page_order) > 0

    if not use_custom_pages:
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
    else:
        writer = pypdf.PdfWriter()
        readers = {}
        for item in ordered_files_info:
            fp = Path(item["path"])
            if fp.exists():
                r = pypdf.PdfReader(str(fp))
                readers[fp.name] = r
                readers[fp.stem] = r
                readers[str(fp)] = r

        for p_act in page_order:
            if p_act.get("is_blank"):
                writer.add_blank_page(width=595.28, height=841.89)
            else:
                fid = str(p_act.get("file_id", "") or "").strip()
                r = readers.get(fid) or readers.get(Path(fid).name) or readers.get(Path(fid).stem)
                if not r:
                    for k, v in readers.items():
                        if fid in k or k in fid:
                            r = v
                            break
                if not r:
                    continue
                orig_p = int(p_act.get("page", 1)) - 1
                if 0 <= orig_p < len(r.pages):
                    page = r.pages[orig_p]
                    rot = int(p_act.get("rotation", 0))
                    if rot != 0:
                        page.rotate(rot)
                    writer.add_page(page)

        with open(output_path, "wb") as f_out:
            writer.write(f_out)
        writer.close()

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
    menu_footer_text: Optional[str] = None,
    page_order: Optional[List[Dict[str, Any]]] = None,
) -> Dict:
    """
    Ponto de entrada principal para fusão com suporte a Menu de Documentos e reordenação de páginas.
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
            menu_footer_text=menu_footer_text,
            page_order=page_order,
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
                page_order=page_order,
            )
        except Exception as fallback_error:
            raise RuntimeError(
                f"Falha ao unificar os PDFs: {primary_error} / Fallback: {fallback_error}"
            )
