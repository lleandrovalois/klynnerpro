"""
Gerenciamento de armazenamento temporário e streaming em disco.
Garante que arquivos PDF de qualquer tamanho (centenas de MBs ou GBs)
sejam gravados e lidos diretamente do disco sem sobrecarregar a memória RAM.
"""

import asyncio
import os
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional
import uuid
from fastapi import UploadFile
import pikepdf
import pypdf

# Diretório base para armazenamento temporário isolado por sessão
BASE_TEMP_DIR = Path(__file__).resolve().parent.parent / "temp_workspaces"
BASE_TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Limite de tempo de vida de sessões inativas (1 hora em segundos)
SESSION_TTL_SECONDS = 3600


def get_session_dir(session_id: str) -> Path:
    """Retorna o diretório isolado de uma sessão específica."""
    session_dir = BASE_TEMP_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


async def save_uploaded_file_stream(
    upload_file: UploadFile,
    session_id: str,
    target_filename: Optional[str] = None,
    chunk_size: int = 1024 * 1024  # 1 MB por chunk
) -> Dict:
    """
    Grava o arquivo recebido em streaming direto para o disco rígido em chunks.
    Isso assegura que o consumo de memória RAM do servidor permaneça na ordem
    de megabytes mesmo para arquivos de múltiplos gigabytes.
    """
    session_dir = get_session_dir(session_id)
    safe_filename = target_filename or upload_file.filename or f"upload_{uuid.uuid4().hex[:8]}.pdf"
    
    # Previne path traversal
    safe_filename = Path(safe_filename).name
    destination_path = session_dir / safe_filename
    
    # Preserva a extensão original do arquivo
    ext = destination_path.suffix or ".pdf"
    counter = 1
    base_stem = destination_path.stem
    while destination_path.exists():
        destination_path = session_dir / f"{base_stem}_{counter}{ext}"
        counter += 1

    total_bytes = 0
    # Grava no disco em blocos (streaming)
    with open(destination_path, "wb") as buffer:
        while True:
            chunk = await upload_file.read(chunk_size)
            if not chunk:
                break
            buffer.write(chunk)
            total_bytes += len(chunk)

    # Extração rápida de metadados (número de páginas)
    page_count = extract_page_count(destination_path)

    return {
        "id": destination_path.name,
        "name": upload_file.filename,
        "saved_filename": destination_path.name,
        "path": str(destination_path),
        "size": total_bytes,
        "page_count": page_count,
        "extension": ext.lower(),
    }


def extract_page_count(file_path: Path) -> int:
    """
    Obtém a contagem de páginas de forma ultra-rápida.
    Para PDFs, usa pikepdf/pypdf. Para Word (.docx), estima páginas baseadas em parágrafos.
    """
    ext = file_path.suffix.lower()
    if ext in [".docx", ".doc"]:
        try:
            import docx
            doc = docx.Document(str(file_path))
            # Estima 1 página para cada ~25 parágrafos (mínimo 1)
            p_count = len([p for p in doc.paragraphs if p.text.strip()])
            return max(1, (p_count // 25) + (1 if p_count % 25 else 0))
        except Exception:
            return 1

    if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"]:
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                return getattr(img, "n_frames", 1)
        except Exception:
            return 1

    try:
        with pikepdf.open(file_path) as pdf:
            return len(pdf.pages)
    except Exception:
        try:
            reader = pypdf.PdfReader(str(file_path))
            return len(reader.pages)
        except Exception:
            return 0


def delete_session_files(session_id: str) -> bool:
    """Remove completamente os arquivos temporários da sessão."""
    session_dir = BASE_TEMP_DIR / session_id
    if session_dir.exists() and session_dir.is_dir():
        try:
            shutil.rmtree(session_dir)
            return True
        except Exception:
            return False
    return False


def cleanup_expired_sessions() -> int:
    """
    Varre o diretório temporário e remove sessões com mais de SESSION_TTL_SECONDS.
    Retorna o número de sessões limpas.
    """
    now = time.time()
    cleaned = 0
    if not BASE_TEMP_DIR.exists():
        return 0

    for item in BASE_TEMP_DIR.iterdir():
        if item.is_dir():
            try:
                dir_age = now - item.stat().st_mtime
                if dir_age > SESSION_TTL_SECONDS:
                    shutil.rmtree(item)
                    cleaned += 1
            except Exception:
                continue
    return cleaned
