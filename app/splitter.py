"""
Motor de divisão (Split) de arquivos PDF de alta performance.
Suporta:
1. Divisão por intervalos (ex: "1-5, 6-10" ou faixas personalizadas).
2. Exportação de todas as páginas como arquivos avulsos (Burst / Páginas individuais).
3. Separação de páginas específicas.
Gera arquivo único ou pacote compactado (.ZIP) com compressão otimizada.
"""

import logging
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional, Tuple
import zipfile

import pikepdf

logger = logging.getLogger("pdf_splitter")


def parse_page_ranges(range_str: str, max_pages: int) -> List[Tuple[int, int]]:
    """
    Analisa uma string de intervalos no formato '1-5, 6-10, 12'
    Retorna lista de tuplas (start_page_1based, end_page_1based).
    """
    ranges: List[Tuple[int, int]] = []
    tokens = [t.strip() for t in range_str.split(",") if t.strip()]

    for token in tokens:
        match_range = re.match(r"^(\d+)\s*-\s*(\d+)$", token)
        if match_range:
            start_p = int(match_range.group(1))
            end_p = int(match_range.group(2))
            if start_p > end_p:
                start_p, end_p = end_p, start_p
            start_p = max(1, min(start_p, max_pages))
            end_p = max(1, min(end_p, max_pages))
            ranges.append((start_p, end_p))
        else:
            match_single = re.match(r"^(\d+)$", token)
            if match_single:
                p = int(match_single.group(1))
                if 1 <= p <= max_pages:
                    ranges.append((p, p))

    return ranges


def execute_pdf_split(
    input_pdf_path: Path,
    session_dir: Path,
    mode: str = "ranges",  # "ranges" | "all_pages" | "specific"
    range_input: Optional[str] = None,
    custom_ranges: Optional[List[Dict[str, int]]] = None,
    output_basename: Optional[str] = None,
    linearize: bool = True,
) -> Dict[str, Any]:
    """
    Executa a divisão de um arquivo PDF.
    
    Retorna dicionário contendo:
    - total_pages: int
    - files_generated: int
    - output_filename: str (.pdf ou .zip)
    - output_path: str
    - duration_seconds: float
    - is_zip: bool
    """
    start_time = time.time()
    out_dir = session_dir / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    base_name = output_basename or input_pdf_path.stem or "documento_dividido"
    # Remove qualquer extensão .pdf ou .zip indesejada no stem
    base_name = re.sub(r"\.(pdf|zip)$", "", base_name, flags=re.IGNORECASE)

    temp_split_dir = session_dir / "split_parts"
    if temp_split_dir.exists():
        import shutil
        shutil.rmtree(temp_split_dir, ignore_errors=True)
    temp_split_dir.mkdir(parents=True, exist_ok=True)

    generated_pdf_files: List[Path] = []

    with pikepdf.open(input_pdf_path) as source_pdf:
        total_pages = len(source_pdf.pages)
        if total_pages == 0:
            raise ValueError("O documento PDF não contém nenhuma página.")

        if mode == "all_pages":
            # Exporta cada página como um arquivo avulso
            digit_count = max(2, len(str(total_pages)))
            for i in range(total_pages):
                page_num = i + 1
                part_pdf = pikepdf.Pdf.new()
                part_pdf.pages.append(source_pdf.pages[i])
                part_name = f"{base_name}_pag_{page_num:0{digit_count}d}.pdf"
                part_path = temp_split_dir / part_name
                part_pdf.save(part_path, linearize=linearize)
                generated_pdf_files.append(part_path)

        elif mode in ("ranges", "specific"):
            # Analisa intervalos
            parsed_ranges: List[Tuple[int, int]] = []

            if custom_ranges:
                for r in custom_ranges:
                    s = max(1, min(r.get("start", 1), total_pages))
                    e = max(1, min(r.get("end", total_pages), total_pages))
                    if s > e:
                        s, e = e, s
                    parsed_ranges.append((s, e))
            elif range_input:
                parsed_ranges = parse_page_ranges(range_input, total_pages)
            else:
                # Padrão: divide ao meio ou por página única
                parsed_ranges = [(1, total_pages)]

            if not parsed_ranges:
                raise ValueError("Nenhum intervalo de páginas válido foi informado.")

            for idx, (start_p, end_p) in enumerate(parsed_ranges, start=1):
                part_pdf = pikepdf.Pdf.new()
                # 1-based para 0-based
                for p_num in range(start_p - 1, end_p):
                    part_pdf.pages.append(source_pdf.pages[p_num])
                
                if start_p == end_p:
                    range_label = f"pag_{start_p}"
                else:
                    range_label = f"pags_{start_p}-{end_p}"
                
                part_name = f"{base_name}_parte_{idx:02d}_{range_label}.pdf"
                part_path = temp_split_dir / part_name
                part_pdf.save(part_path, linearize=linearize)
                generated_pdf_files.append(part_path)

        else:
            raise ValueError(f"Modo de divisão desconhecido: '{mode}'")

    if not generated_pdf_files:
        raise ValueError("Nenhum arquivo resultante foi gerado.")

    # Se apenas 1 arquivo PDF foi gerado, disponibiliza diretamente como .pdf
    if len(generated_pdf_files) == 1:
        final_pdf_path = out_dir / generated_pdf_files[0].name
        import shutil
        shutil.copy2(generated_pdf_files[0], final_pdf_path)
        final_filename = final_pdf_path.name
        is_zip = False
        final_bytes = final_pdf_path.stat().st_size
    else:
        # Múltiplos arquivos: empacota em um arquivo .ZIP
        final_zip_name = f"{base_name}_dividido.zip"
        final_zip_path = out_dir / final_zip_name

        with zipfile.ZipFile(final_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_out:
            for pdf_file in generated_pdf_files:
                zip_out.write(pdf_file, arcname=pdf_file.name)

        final_filename = final_zip_name
        final_pdf_path = final_zip_path
        is_zip = True
        final_bytes = final_zip_path.stat().st_size

    duration = round(time.time() - start_time, 2)

    return {
        "success": True,
        "total_source_pages": total_pages,
        "files_generated": len(generated_pdf_files),
        "output_filename": final_filename,
        "output_path": str(final_pdf_path),
        "output_bytes": final_bytes,
        "duration_seconds": duration,
        "is_zip": is_zip,
    }
