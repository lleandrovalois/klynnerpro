"""
Servidor FastAPI e APIs REST para unificação e manipulação de arquivos PDF com Menu de Documentos.
"""

import asyncio
from contextlib import asynccontextmanager
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import uuid
import urllib.parse

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.merger import execute_pdf_merge
from app.storage import (
    BASE_TEMP_DIR,
    cleanup_expired_sessions,
    delete_session_files,
    get_session_dir,
    save_uploaded_file_stream,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("pdf_merger_api")

CURRENT_DIR = Path(__file__).resolve().parent
STATIC_DIR = CURRENT_DIR / "static"
TEMPLATES_DIR = CURRENT_DIR / "templates"


async def periodic_cleanup_task():
    """Tarefa em segundo plano para limpar sessões inativas periodicamente."""
    while True:
        try:
            cleaned = cleanup_expired_sessions()
            if cleaned > 0:
                logger.info(f"Limpeza periódica: {cleaned} sessões expiradas removidas.")
        except Exception as e:
            logger.error(f"Erro na limpeza periódica: {e}")
        await asyncio.sleep(600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_task = asyncio.create_task(periodic_cleanup_task())
    logger.info("Klynner PDF iniciado com suporte a Menu de Documentos e QPDF C++.")
    yield
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Klynner PDF",
    description="Sistema de alta performance para união limpa e estruturada de grandes arquivos PDF.",
    version="1.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class MergeRequest(BaseModel):
    session_id: str
    file_order: List[Union[Dict[str, Any], str]] = Field(
        ...,
        description="Lista ordenada dos arquivos. Pode conter dicionários com {id, menu_title} ou strings de IDs."
    )
    output_filename: Optional[str] = Field(default="documento_unificado.pdf")
    create_visual_menu: bool = Field(
        default=True,
        description="Gera uma página de sumário/menu visual no início do documento com links clicáveis"
    )
    add_bookmarks: bool = Field(
        default=True,
        description="Gera menu lateral de navegação (marcadores) que abre automaticamente no leitor"
    )
    linearize: bool = Field(
        default=True,
        description="Fast Web View para carregamento imediato em PDFs gigantes"
    )


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = TEMPLATES_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Template index.html não encontrado")
    return index_file.read_text(encoding="utf-8")


@app.post("/api/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    session_id: Optional[str] = Form(None),
):
    if not session_id:
        session_id = str(uuid.uuid4())

    uploaded_files_info = []

    for file in files:
        if not file.filename:
            continue
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"O arquivo '{file.filename}' não é um documento PDF válido."
            )
        
        try:
            file_info = await save_uploaded_file_stream(file, session_id)
            # Limpa o nome para sugerir como título padrão de menu
            clean_menu_title = Path(file.filename).stem.replace("_", " ").replace("-", " ")
            file_info["suggested_menu_title"] = clean_menu_title
            uploaded_files_info.append(file_info)
        except Exception as e:
            logger.error(f"Erro ao salvar arquivo '{file.filename}': {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao processar o upload do arquivo '{file.filename}': {str(e)}"
            )

    return JSONResponse({
        "success": True,
        "session_id": session_id,
        "files": uploaded_files_info,
        "count": len(uploaded_files_info),
    })


@app.post("/api/merge")
async def merge_files(request: MergeRequest):
    session_dir = get_session_dir(request.session_id)
    if not session_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão não encontrada ou expirada. Por favor, envie os arquivos novamente."
        )

    # Processa a ordem e os títulos de menu fornecidos
    ordered_files_info = []

    for item in request.file_order:
        if isinstance(item, dict):
            file_id = item.get("id") or item.get("saved_filename")
            menu_title = item.get("menu_title")
        else:
            file_id = str(item)
            menu_title = None

        if not file_id:
            continue

        safe_name = Path(file_id).name
        file_path = session_dir / safe_name

        if file_path.exists() and file_path.is_file():
            # Se não tiver título customizado, usa o nome do arquivo limpo
            if not menu_title:
                menu_title = file_path.stem.replace("_", " ").replace("-", " ")

            ordered_files_info.append({
                "path": file_path,
                "menu_title": menu_title.strip(),
            })

    if len(ordered_files_info) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="São necessários ao menos 2 arquivos PDF válidos para unificação."
        )

    clean_output_name = Path(request.output_filename or "documento_unificado.pdf").name
    if not clean_output_name.lower().endswith(".pdf"):
        clean_output_name += ".pdf"

    output_path = session_dir / "output" / clean_output_name

    try:
        result = await asyncio.to_thread(
            execute_pdf_merge,
            ordered_files_info=ordered_files_info,
            output_file_path=output_path,
            create_visual_menu=request.create_visual_menu,
            add_bookmarks=request.add_bookmarks,
            linearize=request.linearize,
        )

        return JSONResponse({
            "success": True,
            "session_id": request.session_id,
            "output_filename": clean_output_name,
            "download_url": f"/api/download/{request.session_id}?filename={urllib.parse.quote(clean_output_name)}",
            "preview_url": f"/api/preview/{request.session_id}?filename={urllib.parse.quote(clean_output_name)}",
            "metrics": result,
        })
    except Exception as e:
        logger.error(f"Erro durante a unificação de PDFs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao unificar os arquivos: {str(e)}"
        )


@app.get("/api/download/{session_id}")
async def download_merged_pdf(session_id: str, filename: Optional[str] = "documento_unificado.pdf"):
    clean_name = Path(filename).name
    session_dir = get_session_dir(session_id)
    output_path = session_dir / "output" / clean_name

    if not output_path.exists():
        out_dir = session_dir / "output"
        if out_dir.exists():
            pdfs = list(out_dir.glob("*.pdf"))
            if pdfs:
                output_path = pdfs[0]
                clean_name = output_path.name

    if not output_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo unificado não encontrado para esta sessão."
        )

    encoded_filename = urllib.parse.quote(clean_name)
    headers = {
        "Content-Disposition": f"attachment; filename=\"{clean_name}\"; filename*=UTF-8''{encoded_filename}",
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-cache, no-store, must-revalidate",
    }

    return FileResponse(
        path=str(output_path),
        media_type="application/pdf",
        headers=headers,
    )


@app.get("/api/preview/{session_id}")
async def preview_merged_pdf(session_id: str, filename: Optional[str] = "documento_unificado.pdf"):
    clean_name = Path(filename).name
    session_dir = get_session_dir(session_id)
    output_path = session_dir / "output" / clean_name

    if not output_path.exists():
        out_dir = session_dir / "output"
        if out_dir.exists():
            pdfs = list(out_dir.glob("*.pdf"))
            if pdfs:
                output_path = pdfs[0]
                clean_name = output_path.name

    if not output_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo unificado não encontrado para pré-visualização."
        )

    encoded_filename = urllib.parse.quote(clean_name)
    headers = {
        "Content-Disposition": f"inline; filename=\"{clean_name}\"; filename*=UTF-8''{encoded_filename}",
        "Accept-Ranges": "bytes",
    }

    return FileResponse(
        path=str(output_path),
        media_type="application/pdf",
        headers=headers,
    )


@app.delete("/api/session/{session_id}")
async def cleanup_session(session_id: str):
    success = delete_session_files(session_id)
    return JSONResponse({"success": success, "session_id": session_id})


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Klynner PDF",
        "storage_dir": str(BASE_TEMP_DIR),
        "engines": ["PikePDF/QPDF (C++)", "PyPDF (Fallback)"],
        "streaming_upload": "Ativo (Zero-RAM Chunking)",
        "menu_system": "Ativo (Página de Menu Visual + Marcadores com UseOutlines)",
        "linearization": "Suportado (Fast Web View)",
    }
