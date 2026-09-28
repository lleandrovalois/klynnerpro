"""
Módulo de Redação e Anonimização de PDFs (Redact & Anonymize)
Aplica tarjas pretas e remoção irreversível de informações sensíveis (textos e metadados)
utilizando PyMuPDF (fitz) e sanitização XMP com linearização via PikePDF.
"""

import logging
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional

import pikepdf
import pymupdf

logger = logging.getLogger("pdf_redactor")

# Padrões regex pré-configurados para dados sensíveis
REGEX_PATTERNS = {
    "cpf": re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
    "cnpj": re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(r"(?:\+55\s?)?(?:\(?\d{2}\)?\s?)?(?:9?\d{4}[-.\s]?\d{4})"),
    "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
}


def execute_pdf_redact(
    session_dir: Path,
    file_id: str,
    custom_terms: Optional[List[str]] = None,
    preset_patterns: Optional[List[str]] = None,
    clean_metadata: bool = True,
    output_basename: Optional[str] = None,
    linearize: bool = True,
) -> Dict[str, Any]:
    """
    Remove de forma permanente e irreversível termos e padrões de dados sensíveis,
    além de higienizar metadados ocultos do arquivo.

    Args:
        session_dir: Diretório temporário da sessão
        file_id: Identificador do arquivo no workspace da sessão
        custom_terms: Lista de palavras-chave, nomes ou expressões personalizadas a tarjar
        preset_patterns: Lista de presets ativos ('cpf', 'cnpj', 'email', 'phone', 'credit_card')
        clean_metadata: Se True, remove autor, criador, título e metadados XMP
        output_basename: Nome base para o arquivo resultante
        linearize: Ativa Fast Web View
    """
    t0 = time.time()
    input_path = session_dir / Path(file_id).name
    if not input_path.exists():
        input_path = session_dir / "output" / Path(file_id).name
    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo de origem '{file_id}' não encontrado na sessão.")

    terms_to_redact = [t.strip() for t in (custom_terms or []) if t and t.strip()]
    active_presets = [p.lower().strip() for p in (preset_patterns or []) if p and p.lower().strip() in REGEX_PATTERNS]

    if not terms_to_redact and not active_presets and not clean_metadata:
        raise ValueError("Selecione ao menos um termo, padrão sensível ou a limpeza de metadados para redigir.")

    # Abre com PyMuPDF para aplicação de anotações de redação e remoção física de glifos
    doc = pymupdf.open(str(input_path))
    total_redactions_applied = 0
    matched_terms_found = set()

    for page_idx, page in enumerate(doc):
        page_text = page.get_text()

        # 1. Busca termos personalizados
        for term in terms_to_redact:
            rects = page.search_for(term)
            if rects:
                matched_terms_found.add(term)
                for rect in rects:
                    page.add_redact_annot(rect, fill=(0, 0, 0))
                    total_redactions_applied += 1

        # 2. Busca padrões regex ativos (CPF, Email, etc.)
        for preset_name in active_presets:
            regex_obj = REGEX_PATTERNS[preset_name]
            for match in regex_obj.finditer(page_text):
                matched_str = match.group().strip()
                if not matched_str:
                    continue
                rects = page.search_for(matched_str)
                if rects:
                    matched_terms_found.add(f"[{preset_name.upper()}] {matched_str}")
                    for rect in rects:
                        page.add_redact_annot(rect, fill=(0, 0, 0))
                        total_redactions_applied += 1

        # Aplica a redação: remove permanentemente o conteúdo vetorial e de imagem subjacente
        page.apply_redactions()

    # 3. Limpeza irreversível de metadados do documento
    if clean_metadata:
        doc.set_metadata({
            "format": "PDF 1.7",
            "title": "",
            "author": "",
            "subject": "",
            "keywords": "",
            "creator": "",
            "producer": "",
            "creationDate": "",
            "modDate": "",
            "trapped": "",
        })
        try:
            doc.del_xml_metadata()
        except Exception:
            pass

    clean_stem = (output_basename or input_path.stem).strip()
    clean_stem = Path(clean_stem).stem
    if not clean_stem.endswith("_anonimizado") and not clean_stem.endswith("_redigido"):
        clean_stem = f"{clean_stem}_anonimizado"
    out_filename = f"{clean_stem}.pdf"

    output_dir = session_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    intermediate_path = output_dir / f"tmp_redact_{out_filename}"
    out_path = output_dir / out_filename

    # Salva com garbage collection e compactação do PyMuPDF
    doc.save(
        str(intermediate_path),
        garbage=4,
        deflate=True,
        clean=True,
    )
    doc.close()

    # Lineariza e otimiza via PikePDF se solicitado
    num_pages = 0
    if linearize:
        try:
            with pikepdf.open(intermediate_path) as pike_doc:
                num_pages = len(pike_doc.pages)
                pike_doc.save(out_path, linearize=True)
            if intermediate_path.exists():
                intermediate_path.unlink()
        except Exception as e:
            logger.warning(f"Linearização opcional falhou, mantendo arquivo do PyMuPDF: {e}")
            if intermediate_path.exists():
                if out_path.exists():
                    out_path.unlink()
                intermediate_path.rename(out_path)
    else:
        if intermediate_path.exists():
            if out_path.exists():
                out_path.unlink()
            intermediate_path.rename(out_path)

    if num_pages == 0 and out_path.exists():
        with pikepdf.open(out_path) as check_doc:
            num_pages = len(check_doc.pages)

    elapsed = time.time() - t0
    filesize = out_path.stat().st_size

    logger.info(
        f"PDF redigido/anonimizado: '{out_filename}', {total_redactions_applied} tarjas aplicadas, "
        f"metadados limpos={clean_metadata}, {filesize} bytes em {elapsed:.2f}s"
    )

    return {
        "output_filename": out_filename,
        "filesize": filesize,
        "output_bytes": filesize,
        "pages": num_pages,
        "total_pages": num_pages,
        "redactions_count": total_redactions_applied,
        "redactions_applied": total_redactions_applied,
        "matched_items": list(matched_terms_found)[:50],
        "metadata_cleared": clean_metadata,
        "linearized": linearize,
        "time_seconds": round(elapsed, 3),
        "duration_seconds": round(elapsed, 3),
    }
