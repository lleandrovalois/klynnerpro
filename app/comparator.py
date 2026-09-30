"""
Módulo de Comparação Textual de Documentos PDF.
Utiliza PyMuPDF (fitz) para extração de texto estruturado e difflib para detecção de alterações,
adições, remoções e cálculo de métricas de similaridade entre duas versões de documentos.
"""

import difflib
import html
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

import pymupdf

logger = logging.getLogger("pdf_comparator")


def clean_text(text: str, ignore_whitespace: bool = True, ignore_case: bool = False) -> str:
    """Normaliza o texto conforme as opções de comparação."""
    if not text:
        return ""
    if ignore_case:
        text = text.lower()
    if ignore_whitespace:
        # Normaliza espaços múltiplos e quebras de linha preservando a estrutura
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
        # Remove linhas vazias consecutivas
        cleaned_lines = []
        last_empty = False
        for line in lines:
            if not line:
                if not last_empty:
                    cleaned_lines.append("")
                    last_empty = True
            else:
                cleaned_lines.append(line)
                last_empty = False
        return "\n".join(cleaned_lines)
    return text


def extract_page_texts(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Extrai texto página a página do documento PDF.
    Retorna uma lista com o número da página, texto puro e linhas.
    """
    pages_data = []
    doc = pymupdf.open(str(pdf_path))
    try:
        for idx, page in enumerate(doc):
            page_text = page.get_text("text") or ""
            pages_data.append({
                "page_num": idx + 1,
                "text": page_text,
                "lines": page_text.splitlines(),
                "word_count": len(page_text.split()),
            })
    finally:
        doc.close()
    return pages_data


def compute_word_diff(text_a: str, text_b: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]:
    """
    Calcula diferenças refinadas no nível de palavras entre duas strings.
    Retorna tokens para o lado A, tokens para o lado B e contadores estatísticos.
    """
    # Tokeniza preservando pontuação e espaços
    tokens_a = re.findall(r"\S+|\s+", text_a)
    tokens_b = re.findall(r"\S+|\s+", text_b)

    matcher = difflib.SequenceMatcher(None, tokens_a, tokens_b)
    chunks_a = []
    chunks_b = []
    added_words = 0
    removed_words = 0
    unchanged_words = 0

    for tag, alo, ahi, blo, bhi in matcher.get_opcodes():
        sub_a = "".join(tokens_a[alo:ahi])
        sub_b = "".join(tokens_b[blo:bhi])

        if tag == "equal":
            if sub_a:
                chunks_a.append({"type": "equal", "text": sub_a})
                chunks_b.append({"type": "equal", "text": sub_b})
                unchanged_words += len(sub_a.split())
        elif tag == "delete":
            if sub_a:
                chunks_a.append({"type": "delete", "text": sub_a})
                removed_words += len(sub_a.split())
        elif tag == "insert":
            if sub_b:
                chunks_b.append({"type": "insert", "text": sub_b})
                added_words += len(sub_b.split())
        elif tag == "replace":
            if sub_a:
                chunks_a.append({"type": "delete", "text": sub_a})
                removed_words += len(sub_a.split())
            if sub_b:
                chunks_b.append({"type": "insert", "text": sub_b})
                added_words += len(sub_b.split())

    stats = {
        "added_words": added_words,
        "removed_words": removed_words,
        "unchanged_words": unchanged_words,
    }
    return chunks_a, chunks_b, stats


def compute_line_diff(
    lines_a: List[str],
    lines_b: List[str],
    granularity: str = "word"
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Compara duas listas de linhas gerando uma estrutura pareada para visualização lado a lado.
    """
    matcher = difflib.SequenceMatcher(None, lines_a, lines_b)
    diff_rows = []
    total_added = 0
    total_removed = 0
    total_unchanged = 0
    total_modified = 0

    line_idx_a = 1
    line_idx_b = 1

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for a_line, b_line in zip(lines_a[i1:i2], lines_b[j1:j2]):
                w_count = len(a_line.split())
                total_unchanged += w_count
                diff_rows.append({
                    "type": "equal",
                    "num_a": line_idx_a,
                    "num_b": line_idx_b,
                    "text_a": a_line,
                    "text_b": b_line,
                    "chunks_a": [{"type": "equal", "text": a_line}],
                    "chunks_b": [{"type": "equal", "text": b_line}],
                })
                line_idx_a += 1
                line_idx_b += 1

        elif tag == "replace":
            count_a = i2 - i1
            count_b = j2 - j1
            max_len = max(count_a, count_b)

            for offset in range(max_len):
                curr_a = lines_a[i1 + offset] if offset < count_a else None
                curr_b = lines_b[j1 + offset] if offset < count_b else None

                curr_num_a = line_idx_a if curr_a is not None else None
                curr_num_b = line_idx_b if curr_b is not None else None

                if curr_a is not None and curr_b is not None:
                    total_modified += 1
                    if granularity == "word":
                        ca, cb, st = compute_word_diff(curr_a, curr_b)
                        total_added += st["added_words"]
                        total_removed += st["removed_words"]
                        total_unchanged += st["unchanged_words"]
                    else:
                        ca = [{"type": "delete", "text": curr_a}]
                        cb = [{"type": "insert", "text": curr_b}]
                        total_removed += len(curr_a.split())
                        total_added += len(curr_b.split())

                    diff_rows.append({
                        "type": "replace",
                        "num_a": curr_num_a,
                        "num_b": curr_num_b,
                        "text_a": curr_a,
                        "text_b": curr_b,
                        "chunks_a": ca,
                        "chunks_b": cb,
                    })
                    line_idx_a += 1
                    line_idx_b += 1

                elif curr_a is not None:
                    # Deletado da versão A
                    total_removed += len(curr_a.split())
                    diff_rows.append({
                        "type": "delete",
                        "num_a": curr_num_a,
                        "num_b": None,
                        "text_a": curr_a,
                        "text_b": "",
                        "chunks_a": [{"type": "delete", "text": curr_a}],
                        "chunks_b": [],
                    })
                    line_idx_a += 1

                elif curr_b is not None:
                    # Adicionado na versão B
                    total_added += len(curr_b.split())
                    diff_rows.append({
                        "type": "insert",
                        "num_a": None,
                        "num_b": curr_num_b,
                        "text_a": "",
                        "text_b": curr_b,
                        "chunks_a": [],
                        "chunks_b": [{"type": "insert", "text": curr_b}],
                    })
                    line_idx_b += 1

        elif tag == "delete":
            for a_line in lines_a[i1:i2]:
                total_removed += len(a_line.split())
                diff_rows.append({
                    "type": "delete",
                    "num_a": line_idx_a,
                    "num_b": None,
                    "text_a": a_line,
                    "text_b": "",
                    "chunks_a": [{"type": "delete", "text": a_line}],
                    "chunks_b": [],
                })
                line_idx_a += 1

        elif tag == "insert":
            for b_line in lines_b[j1:j2]:
                total_added += len(b_line.split())
                diff_rows.append({
                    "type": "insert",
                    "num_a": None,
                    "num_b": line_idx_b,
                    "text_a": "",
                    "text_b": b_line,
                    "chunks_a": [],
                    "chunks_b": [{"type": "insert", "text": b_line}],
                })
                line_idx_b += 1

    stats = {
        "added_words": total_added,
        "removed_words": total_removed,
        "unchanged_words": total_unchanged,
        "modified_lines": total_modified,
    }
    return diff_rows, stats


def generate_html_report(
    file_a_name: str,
    file_b_name: str,
    metrics: Dict[str, Any],
    pages_diff: List[Dict[str, Any]]
) -> str:
    """Gera um relatório de auditoria e comparação formatado e pronto para impressão ou download."""
    sim_pct = metrics["similarity_percentage"]
    total_added = metrics["words_added"]
    total_removed = metrics["words_removed"]
    pages_with_diff = metrics["pages_with_differences"]
    total_pages = metrics["total_pages_compared"]

    sim_badge_color = "#10B981" if sim_pct >= 90 else ("#F59E0B" if sim_pct >= 70 else "#EF4444")

    pages_html_parts = []
    for p in pages_diff:
        page_num = p["page_num"]
        has_ch = p["has_changes"]
        p_sim = p["similarity_score"]
        status_badge = (
            f'<span style="background:rgba(239,68,68,0.15);color:#EF4444;border:1px solid rgba(239,68,68,0.3);padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;">{p["stats"]["removed_words"]} removidas / {p["stats"]["added_words"]} adicionadas</span>'
            if has_ch else
            '<span style="background:rgba(16,185,129,0.15);color:#10B981;border:1px solid rgba(16,185,129,0.3);padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;">100% Idêntica</span>'
        )

        rows_html = []
        for row in p["diff_rows"]:
            rtype = row["type"]
            num_a = row["num_a"] or ""
            num_b = row["num_b"] or ""

            # Renderiza chunks A
            chunks_a_html = ""
            if row["chunks_a"]:
                for c in row["chunks_a"]:
                    escaped = html.escape(c["text"])
                    if c["type"] == "delete":
                        chunks_a_html += f'<mark style="background:rgba(239,68,68,0.25);color:#FCA5A5;text-decoration:line-through;border-radius:3px;padding:0 2px;">{escaped}</mark>'
                    else:
                        chunks_a_html += escaped
            else:
                chunks_a_html = "&nbsp;"

            # Renderiza chunks B
            chunks_b_html = ""
            if row["chunks_b"]:
                for c in row["chunks_b"]:
                    escaped = html.escape(c["text"])
                    if c["type"] == "insert":
                        chunks_b_html += f'<mark style="background:rgba(16,185,129,0.25);color:#6EE7B7;border-radius:3px;padding:0 2px;">{escaped}</mark>'
                    else:
                        chunks_b_html += escaped
            else:
                chunks_b_html = "&nbsp;"

            row_bg = "transparent"
            if rtype == "delete":
                row_bg = "rgba(239, 68, 68, 0.08)"
            elif rtype == "insert":
                row_bg = "rgba(16, 185, 129, 0.08)"
            elif rtype == "replace":
                row_bg = "rgba(245, 158, 11, 0.07)"

            rows_html.append(f"""
            <tr style="background:{row_bg};border-bottom:1px solid rgba(255,255,255,0.04);">
              <td style="width:36px;color:#64748B;font-family:monospace;font-size:11px;text-align:right;padding:4px 6px;user-select:none;border-right:1px solid rgba(255,255,255,0.06);">{num_a}</td>
              <td style="width:48%;padding:4px 8px;font-family:monospace;font-size:12px;line-height:1.4;word-break:break-word;vertical-align:top;border-right:1px solid rgba(255,255,255,0.08);">{chunks_a_html}</td>
              <td style="width:36px;color:#64748B;font-family:monospace;font-size:11px;text-align:right;padding:4px 6px;user-select:none;border-right:1px solid rgba(255,255,255,0.06);">{num_b}</td>
              <td style="width:48%;padding:4px 8px;font-family:monospace;font-size:12px;line-height:1.4;word-break:break-word;vertical-align:top;">{chunks_b_html}</td>
            </tr>
            """)

        pages_html_parts.append(f"""
        <div style="margin-bottom:30px;background:rgba(17,24,39,0.85);border:1px solid rgba(255,255,255,0.08);border-radius:12px;overflow:hidden;">
          <div style="background:rgba(30,41,59,0.8);padding:12px 18px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(255,255,255,0.08);">
            <div style="display:flex;align-items:center;gap:12px;">
              <strong style="color:#F8FAFC;font-size:14px;">Página {page_num}</strong>
              <span style="color:#94A3B8;font-size:12px;">Similaridade: {p_sim:.1f}%</span>
            </div>
            <div>{status_badge}</div>
          </div>
          <table style="width:100%;border-collapse:collapse;color:#E2E8F0;">
            <thead>
              <tr style="background:rgba(15,23,42,0.95);color:#94A3B8;font-size:11px;text-transform:uppercase;border-bottom:1px solid rgba(255,255,255,0.08);">
                <th colspan="2" style="padding:6px 10px;text-align:left;border-right:1px solid rgba(255,255,255,0.08);">Documento A: {html.escape(file_a_name)}</th>
                <th colspan="2" style="padding:6px 10px;text-align:left;">Documento B: {html.escape(file_b_name)}</th>
              </tr>
            </thead>
            <tbody>
              {''.join(rows_html)}
            </tbody>
          </table>
        </div>
        """)

    report = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Relatório de Comparação de PDFs - Klynner PDF PRO</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    @media print {{
      body {{ background:#fff !important; color:#111 !important; }}
      .no-print {{ display:none !important; }}
      table {{ page-break-inside:auto; }}
      tr {{ page-break-inside:avoid; page-break-after:auto; }}
    }}
    * {{ box-sizing:border-box; margin:0; padding:0; }}
    body {{
      font-family:'Plus Jakarta Sans',sans-serif;
      background:#090D16;
      color:#F8FAFC;
      line-height:1.5;
      padding:24px;
    }}
    .container {{
      max-width:1200px;
      margin:0 auto;
    }}
    .header {{
      background:rgba(17,24,39,0.9);
      border:1px solid rgba(255,255,255,0.1);
      border-radius:14px;
      padding:20px 24px;
      margin-bottom:24px;
      display:flex;
      justify-content:space-between;
      align-items:center;
      flex-wrap:wrap;
      gap:16px;
    }}
    .stat-badge {{
      display:inline-flex;
      align-items:center;
      gap:8px;
      padding:8px 14px;
      border-radius:10px;
      background:rgba(255,255,255,0.04);
      border:1px solid rgba(255,255,255,0.08);
      font-size:13px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div>
        <h1 style="font-size:22px;font-weight:800;color:#F8FAFC;margin-bottom:4px;">Relatório de Auditoria Textual de PDFs</h1>
        <p style="font-size:13px;color:#94A3B8;">Klynner PDF PRO &bull; Comparação precisa linha a linha e por palavras</p>
      </div>
      <div class="no-print" style="display:flex;gap:10px;">
        <button onclick="window.print()" style="padding:8px 16px;border-radius:8px;background:#6366F1;color:#fff;border:none;font-weight:600;cursor:pointer;">Imprimir / Salvar PDF</button>
      </div>
    </div>

    <!-- Cards de Resumo -->
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin-bottom:24px;">
      <div style="background:rgba(17,24,39,0.8);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:16px;">
        <div style="font-size:12px;color:#94A3B8;text-transform:uppercase;">Similaridade Global</div>
        <div style="font-size:28px;font-weight:800;color:{sim_badge_color};margin-top:4px;">{sim_pct:.1f}%</div>
        <div style="font-size:11px;color:#64748B;margin-top:2px;">Índice de proximidade textual</div>
      </div>
      <div style="background:rgba(17,24,39,0.8);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:16px;">
        <div style="font-size:12px;color:#94A3B8;text-transform:uppercase;">Palavras Adicionadas</div>
        <div style="font-size:28px;font-weight:800;color:#10B981;margin-top:4px;">+{total_added}</div>
        <div style="font-size:11px;color:#64748B;margin-top:2px;">Inserções no Documento B</div>
      </div>
      <div style="background:rgba(17,24,39,0.8);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:16px;">
        <div style="font-size:12px;color:#94A3B8;text-transform:uppercase;">Palavras Removidas</div>
        <div style="font-size:28px;font-weight:800;color:#EF4444;margin-top:4px;">-{total_removed}</div>
        <div style="font-size:11px;color:#64748B;margin-top:2px;">Exclusões em relação a A</div>
      </div>
      <div style="background:rgba(17,24,39,0.8);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:16px;">
        <div style="font-size:12px;color:#94A3B8;text-transform:uppercase;">Páginas com Diferenças</div>
        <div style="font-size:28px;font-weight:800;color:#38BDF8;margin-top:4px;">{pages_with_diff} / {total_pages}</div>
        <div style="font-size:11px;color:#64748B;margin-top:2px;">Páginas alteradas</div>
      </div>
    </div>

    <!-- Comparação Página a Página -->
    {''.join(pages_html_parts)}

    <div style="text-align:center;padding:20px;color:#64748B;font-size:12px;">
      Gerado automaticamente pelo Klynner PDF PRO &bull; Processamento seguro e isolado em disco.
    </div>
  </div>
</body>
</html>"""
    return report


def execute_pdf_compare(
    session_dir: Path,
    file_a_id: str,
    file_b_id: str,
    granularity: str = "word",
    ignore_whitespace: bool = True,
    ignore_case: bool = False,
    output_filename: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executa a comparação completa entre dois documentos PDF.
    Gera métricas, estrutura pareada de linhas e tokens, e cria o relatório HTML.
    """
    safe_a = Path(file_a_id).name
    safe_b = Path(file_b_id).name

    path_a = session_dir / safe_a
    if not path_a.exists() and (session_dir / "output" / safe_a).exists():
        path_a = session_dir / "output" / safe_a

    path_b = session_dir / safe_b
    if not path_b.exists() and (session_dir / "output" / safe_b).exists():
        path_b = session_dir / "output" / safe_b

    if not path_a.exists():
        raise FileNotFoundError(f"Documento A '{safe_a}' não encontrado na sessão.")
    if not path_b.exists():
        raise FileNotFoundError(f"Documento B '{safe_b}' não encontrado na sessão.")

    # 1. Extração estruturada de páginas
    pages_a = extract_page_texts(path_a)
    pages_b = extract_page_texts(path_b)

    total_pages_a = len(pages_a)
    total_pages_b = len(pages_b)
    max_pages = max(total_pages_a, total_pages_b)

    total_words_a = sum(p["word_count"] for p in pages_a)
    total_words_b = sum(p["word_count"] for p in pages_b)

    pages_diff = []
    global_added_words = 0
    global_removed_words = 0
    global_unchanged_words = 0
    global_modified_lines = 0
    pages_with_differences = 0

    full_text_a_parts = []
    full_text_b_parts = []

    for i in range(max_pages):
        page_num = i + 1
        data_a = pages_a[i] if i < total_pages_a else {"page_num": page_num, "text": "", "lines": [], "word_count": 0}
        data_b = pages_b[i] if i < total_pages_b else {"page_num": page_num, "text": "", "lines": [], "word_count": 0}

        cleaned_a = clean_text(data_a["text"], ignore_whitespace=ignore_whitespace, ignore_case=ignore_case)
        cleaned_b = clean_text(data_b["text"], ignore_whitespace=ignore_whitespace, ignore_case=ignore_case)

        full_text_a_parts.append(cleaned_a)
        full_text_b_parts.append(cleaned_b)

        lines_a = cleaned_a.splitlines()
        lines_b = cleaned_b.splitlines()

        diff_rows, page_stats = compute_line_diff(lines_a, lines_b, granularity=granularity)

        has_changes = (
            page_stats["added_words"] > 0
            or page_stats["removed_words"] > 0
            or page_stats["modified_lines"] > 0
            or (data_a["text"] != data_b["text"])
        )

        if has_changes:
            pages_with_differences += 1

        # Calcula a similaridade da página
        p_matcher = difflib.SequenceMatcher(None, cleaned_a, cleaned_b)
        p_similarity = round(p_matcher.ratio() * 100, 2)

        global_added_words += page_stats["added_words"]
        global_removed_words += page_stats["removed_words"]
        global_unchanged_words += page_stats["unchanged_words"]
        global_modified_lines += page_stats["modified_lines"]

        pages_diff.append({
            "page_num": page_num,
            "has_changes": has_changes,
            "similarity_score": p_similarity,
            "stats": page_stats,
            "diff_rows": diff_rows,
            "exists_in_a": i < total_pages_a,
            "exists_in_b": i < total_pages_b,
        })

    # Similaridade global
    global_text_a = "\n".join(full_text_a_parts)
    global_text_b = "\n".join(full_text_b_parts)
    global_matcher = difflib.SequenceMatcher(None, global_text_a, global_text_b)
    global_similarity = round(global_matcher.ratio() * 100, 2)

    metrics = {
        "similarity_percentage": global_similarity,
        "words_added": global_added_words,
        "words_removed": global_removed_words,
        "words_unchanged": global_unchanged_words,
        "total_words_a": total_words_a,
        "total_words_b": total_words_b,
        "total_pages_a": total_pages_a,
        "total_pages_b": total_pages_b,
        "total_pages_compared": max_pages,
        "pages_with_differences": pages_with_differences,
        "identical_pages": max_pages - pages_with_differences,
        "modified_lines_count": global_modified_lines,
    }

    # 3. Gera Relatório HTML
    out_dir = session_dir / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    report_basename = output_filename or "relatorio_comparacao.html"
    if not report_basename.lower().endswith(".html"):
        report_basename += ".html"
    safe_report_name = Path(report_basename).name
    report_path = out_dir / safe_report_name

    html_content = generate_html_report(safe_a, safe_b, metrics, pages_diff)
    report_path.write_text(html_content, encoding="utf-8")

    logger.info(
        f"Comparação concluída: '{safe_a}' vs '{safe_b}' -> "
        f"Similaridade: {global_similarity}%, +{global_added_words}, -{global_removed_words}"
    )

    return {
        "success": True,
        "file_a": safe_a,
        "file_b": safe_b,
        "metrics": metrics,
        "pages": pages_diff,
        "output_filename": safe_report_name,
        "report_url": f"/api/download/{session_dir.name}?filename={safe_report_name}",
    }
