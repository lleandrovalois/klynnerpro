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

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.analytics import get_current_stats, init_analytics_db, record_page_visit
from app.feedback import (
    delete_feedback,
    get_feedback_count,
    get_recent_feedbacks,
    init_feedback_db,
    is_valid_admin_key,
    save_feedback,
)
from app.merger import execute_pdf_merge
from app.splitter import execute_pdf_split
from app.organizer import execute_pdf_organize
from app.rotator import execute_pdf_rotate
from app.extractor import execute_pdf_extract
from app.protector import execute_pdf_protect, execute_pdf_unlock
from app.redactor import execute_pdf_redact
from app.pdf_to_word import execute_pdf_to_word
from app.word_to_pdf import execute_word_to_pdf
from app.image_to_pdf import execute_image_to_pdf
from app.watermark import execute_pdf_watermark
from app.footer_customizer import execute_pdf_footer
from app.footer_remover import execute_pdf_remove_footer
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
    init_analytics_db()
    init_feedback_db()
    cleanup_task = asyncio.create_task(periodic_cleanup_task())
    logger.info("Klynner PDF iniciado com suporte a Menu de Documentos, QPDF C++ e Analytics.")
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

@app.middleware("http")
async def add_cache_control_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
    elif request.url.path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

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
    menu_footer_text: Optional[str] = Field(
        default=None,
        description="Texto personalizado para o rodapé da página de menu/sumário"
    )


class SplitRequest(BaseModel):
    session_id: str
    file_id: str
    mode: str = Field(default="ranges", description="'ranges' | 'all_pages' | 'specific'")
    range_input: Optional[str] = Field(default=None, description="Ex: '1-5, 6-10'")
    custom_ranges: Optional[List[Dict[str, int]]] = None
    output_filename: Optional[str] = Field(default="documento_dividido")
    linearize: bool = Field(default=True)


class OrganizeRequest(BaseModel):
    session_id: str
    file_id: str
    page_actions: List[Dict[str, Any]] = Field(
        ...,
        description="Lista ordenada de páginas com rotação: [{'page': 1, 'rotation': 0}, ...]"
    )
    output_filename: Optional[str] = Field(default="documento_organizado.pdf")
    linearize: bool = Field(default=True)


class RotateRequest(BaseModel):
    session_id: str
    file_id: str
    page_rotations: Optional[Dict[str, int]] = Field(
        default=None,
        description="Mapeamento de página ('1', '2') -> graus adicionais (90, 180, 270)"
    )
    default_rotation: int = Field(default=0)
    output_filename: Optional[str] = Field(default="documento_rotacionado.pdf")
    linearize: bool = Field(default=True)


class ExtractRequest(BaseModel):
    session_id: str
    file_id: str
    selected_pages: List[int] = Field(..., description="Lista de páginas 1-based selecionadas")
    mode: str = Field(default="merge", description="'merge' para PDF ou 'split' para ZIP")
    output_filename: Optional[str] = Field(default="paginas_extraidas")
    linearize: bool = Field(default=True)


class ProtectRequest(BaseModel):
    session_id: str
    file_id: str
    user_password: Optional[str] = Field(default=None, description="Senha para abertura do PDF")
    owner_password: Optional[str] = Field(default=None, description="Senha mestra de permissões")
    encryption_level: Optional[str] = Field(default="aes-256", description="'aes-256' ou 'aes-128'")
    encryption_algorithm: Optional[str] = Field(default=None, description="Alias para encryption_level")
    allow_printing: bool = Field(default=False, description="Permite imprimir o PDF")
    allow_copying: bool = Field(default=False, description="Permite copiar/extrair textos e imagens")
    allow_modifying: bool = Field(default=False, description="Permite modificar o documento")
    allow_annotations: bool = Field(default=False, description="Permite anotações e preenchimento")
    permissions: Optional[Dict[str, bool]] = Field(default=None, description="Permissões em formato de dicionário")
    output_filename: Optional[str] = Field(default="documento_protegido.pdf")
    linearize: bool = Field(default=True)


class UnlockRequest(BaseModel):
    session_id: str
    file_id: str
    password: Optional[str] = Field(default=None, description="Senha conhecida do documento")
    output_filename: Optional[str] = Field(default="documento_desprotegido.pdf")
    linearize: bool = Field(default=True)


class RedactRequest(BaseModel):
    session_id: str
    file_id: str
    custom_terms: Optional[List[str]] = Field(default=None, description="Lista de termos ou nomes para tarjar")
    preset_patterns: Optional[List[str]] = Field(
        default=None,
        description="Filtros sensíveis pré-definidos: 'cpf', 'cnpj', 'email', 'phone', 'credit_card'"
    )
    patterns: Optional[List[str]] = Field(default=None, description="Alias para preset_patterns")
    clean_metadata: bool = Field(default=True, description="Remove dados de autor, criador e XMP")
    output_filename: Optional[str] = Field(default="documento_anonimizado.pdf")
    linearize: bool = Field(default=True)


class PdfToWordRequest(BaseModel):
    session_id: str
    file_id: str
    output_filename: Optional[str] = Field(default="documento_convertido.docx")
    start_page: Optional[int] = Field(default=None, description="Página inicial (1-based)")
    end_page: Optional[int] = Field(default=None, description="Página final (1-based)")


class WordToPdfRequest(BaseModel):
    session_id: str
    file_id: str
    output_filename: Optional[str] = Field(default="documento_convertido.pdf")
    linearize: bool = Field(default=True)


class ImageToPdfRequest(BaseModel):
    session_id: str
    image_files: List[str] = Field(..., description="Lista ordenada de nomes/IDs dos arquivos de imagem")
    page_size: str = Field(default="a4", description="'a4', 'letter', ou 'fit'")
    orientation: str = Field(default="auto", description="'auto', 'portrait', ou 'landscape'")
    margin: str = Field(default="none", description="'none', 'small', ou 'big'")
    output_filename: Optional[str] = Field(default="imagens_convertidas.pdf")
    linearize: bool = Field(default=True)


class WatermarkRequest(BaseModel):
    session_id: str
    file_id: str
    watermark_type: str = Field(default="text", description="'text' ou 'image'")
    text: Optional[str] = Field(default="CONFIDENCIAL")
    font_size: int = Field(default=48)
    font_color: str = Field(default="#DC2626")
    opacity: float = Field(default=0.25)
    rotation: int = Field(default=-45)
    position: str = Field(default="center", description="'center', 'top', 'bottom', ou 'tile'")
    watermark_image_id: Optional[str] = None
    image_scale: float = Field(default=0.5)
    layer: str = Field(default="overlay", description="'overlay' ou 'underlay'")
    pages: str = Field(default="all", description="'all', 'first', ou intervalos '1-3, 5'")
    output_filename: Optional[str] = Field(default="documento_marca_dagua.pdf")
    linearize: bool = Field(default=True)


class FooterRequest(BaseModel):
    session_id: str
    file_id: str
    footer_text: str = Field(default="{page}", description="Texto do rodapé com tags {page}, {total}, {date}, {file}")
    position: str = Field(default="footer", description="'footer' (inferior) ou 'header' (superior)")
    alignment: str = Field(default="center", description="'left', 'center', 'right'")
    font_size: float = Field(default=9.0)
    font_color: str = Field(default="#64748B")
    skip_first_page: bool = Field(default=False)
    page_start_number: int = Field(default=1)
    margin_offset: float = Field(default=25.0)
    output_filename: Optional[str] = Field(default="documento_com_rodape.pdf")
    linearize: bool = Field(default=True)


class RemoveFooterRequest(BaseModel):
    session_id: str
    file_id: str
    mode: str = Field(default="margin", description="'margin' (faixa inteira), 'text' (texto específico) ou 'both'")
    target_area: str = Field(default="footer", description="'footer', 'header' ou 'both'")
    margin_height: float = Field(default=35.0, description="Altura da margem a expurgar em pontos")
    fill_color: str = Field(default="#FFFFFF", description="Cor de preenchimento ou 'transparent'")
    custom_text: Optional[str] = Field(default=None, description="Texto específico a expurgar")
    remove_page_numbers: bool = Field(default=False, description="Detecta e remove automaticamente numeração de página")
    skip_first_page: bool = Field(default=False, description="Ignora a primeira página (capa)")
    pages: str = Field(default="all", description="'all', 'first', ou intervalos '1-5, 8'")
    output_filename: Optional[str] = Field(default="documento_sem_rodape.pdf")
    linearize: bool = Field(default=True)




@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = TEMPLATES_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Template index.html não encontrado")
    
    content = index_file.read_text(encoding="utf-8")
    
    # Versionamento dinâmico baseado na modificação dos arquivos estáticos para quebra de cache infalível
    import re
    css_path = STATIC_DIR / "css" / "style.css"
    js_path = STATIC_DIR / "js" / "app.js"
    v_css = int(css_path.stat().st_mtime) if css_path.exists() else 2100
    v_js = int(js_path.stat().st_mtime) if js_path.exists() else 2100
    
    content = re.sub(r'/static/css/style\.css(\?[^"\'\s>]*)?', f'/static/css/style.css?v={v_css}', content)
    content = re.sub(r'/static/js/app\.js(\?[^"\'\s>]*)?', f'/static/js/app.js?v={v_js}', content)
    
    return HTMLResponse(
        content=content,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )


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
        valid_exts = {
            ".pdf", ".docx", ".doc",
            ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"
        }
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in valid_exts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"O arquivo '{file.filename}' não possui um formato suportado (.pdf, .docx, .doc, imagens)."
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
            menu_footer_text=request.menu_footer_text,
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


@app.post("/api/split")
async def split_pdf_endpoint(request: SplitRequest):
    session_dir = get_session_dir(request.session_id)
    if not session_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão não encontrada ou expirada. Por favor, envie o arquivo novamente."
        )

    safe_name = Path(request.file_id).name
    file_path = session_dir / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arquivo '{safe_name}' não encontrado na sessão."
        )

    try:
        result = await asyncio.to_thread(
            execute_pdf_split,
            input_pdf_path=file_path,
            session_dir=session_dir,
            mode=request.mode,
            range_input=request.range_input,
            custom_ranges=request.custom_ranges,
            output_basename=request.output_filename,
            linearize=request.linearize,
        )

        out_name = result["output_filename"]
        is_zip = result.get("is_zip", False)
        preview_url = None if is_zip else f"/api/preview/{request.session_id}?filename={urllib.parse.quote(out_name)}"

        return JSONResponse({
            "success": True,
            "session_id": request.session_id,
            "output_filename": out_name,
            "download_url": f"/api/download/{request.session_id}?filename={urllib.parse.quote(out_name)}",
            "preview_url": preview_url,
            "is_zip": is_zip,
            "metrics": result,
        })
    except Exception as e:
        logger.error(f"Erro ao dividir PDF: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao dividir o PDF: {str(e)}"
        )


@app.post("/api/organize")
async def organize_pdf_endpoint(request: OrganizeRequest):
    session_dir = get_session_dir(request.session_id)
    if not session_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão não encontrada ou expirada. Por favor, envie o arquivo novamente."
        )

    safe_name = Path(request.file_id).name
    file_path = session_dir / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arquivo '{safe_name}' não encontrado na sessão."
        )

    clean_out_name = Path(request.output_filename or "documento_organizado.pdf").name
    if not clean_out_name.lower().endswith(".pdf"):
        clean_out_name += ".pdf"

    output_path = session_dir / "output" / clean_out_name

    try:
        result = await asyncio.to_thread(
            execute_pdf_organize,
            input_pdf_path=file_path,
            output_pdf_path=output_path,
            page_actions=request.page_actions,
            linearize=request.linearize,
        )

        return JSONResponse({
            "success": True,
            "session_id": request.session_id,
            "output_filename": clean_out_name,
            "download_url": f"/api/download/{request.session_id}?filename={urllib.parse.quote(clean_out_name)}",
            "preview_url": f"/api/preview/{request.session_id}?filename={urllib.parse.quote(clean_out_name)}",
            "is_zip": False,
            "metrics": result,
        })
    except Exception as e:
        logger.error(f"Erro ao organizar PDF: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao organizar o PDF: {str(e)}"
        )


@app.post("/api/rotate")
async def rotate_pdf_endpoint(request: RotateRequest):
    session_dir = get_session_dir(request.session_id)
    if not session_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão não encontrada ou expirada. Por favor, envie o arquivo novamente."
        )

    safe_name = Path(request.file_id).name
    file_path = session_dir / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arquivo '{safe_name}' não encontrado na sessão."
        )

    clean_out_name = Path(request.output_filename or "documento_rotacionado.pdf").name
    if not clean_out_name.lower().endswith(".pdf"):
        clean_out_name += ".pdf"

    output_path = session_dir / "output" / clean_out_name

    try:
        result = await asyncio.to_thread(
            execute_pdf_rotate,
            input_pdf_path=file_path,
            output_pdf_path=output_path,
            page_rotations=request.page_rotations,
            default_rotation=request.default_rotation,
            linearize=request.linearize,
        )

        return JSONResponse({
            "success": True,
            "session_id": request.session_id,
            "output_filename": clean_out_name,
            "download_url": f"/api/download/{request.session_id}?filename={urllib.parse.quote(clean_out_name)}",
            "preview_url": f"/api/preview/{request.session_id}?filename={urllib.parse.quote(clean_out_name)}",
            "is_zip": False,
            "metrics": result,
        })
    except Exception as e:
        logger.error(f"Erro ao rotacionar PDF: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao rotacionar o PDF: {str(e)}"
        )


@app.post("/api/extract")
async def extract_pdf_endpoint(request: ExtractRequest):
    session_dir = get_session_dir(request.session_id)
    if not session_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão não encontrada ou expirada. Por favor, envie o arquivo novamente."
        )

    safe_name = Path(request.file_id).name
    file_path = session_dir / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arquivo '{safe_name}' não encontrado na sessão."
        )

    try:
        result = await asyncio.to_thread(
            execute_pdf_extract,
            input_pdf_path=file_path,
            session_dir=session_dir,
            selected_pages=request.selected_pages,
            mode=request.mode,
            output_basename=request.output_filename,
            linearize=request.linearize,
        )

        out_name = result["output_filename"]
        is_zip = result.get("is_zip", False)
        preview_url = None if is_zip else f"/api/preview/{request.session_id}?filename={urllib.parse.quote(out_name)}"

        return JSONResponse({
            "success": True,
            "session_id": request.session_id,
            "output_filename": out_name,
            "download_url": f"/api/download/{request.session_id}?filename={urllib.parse.quote(out_name)}",
            "preview_url": preview_url,
            "is_zip": is_zip,
            "metrics": result,
        })
    except Exception as e:
        logger.error(f"Erro ao extrair páginas do PDF: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao extrair páginas: {str(e)}"
        )


@app.post("/api/protect")
async def protect_pdf(request: ProtectRequest):
    session_dir = get_session_dir(request.session_id)
    if not session_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão não encontrada ou expirada. Por favor, envie o arquivo novamente."
        )

    safe_name = Path(request.file_id).name
    file_path = session_dir / safe_name
    if not file_path.exists() and (session_dir / "output" / safe_name).exists():
        file_path = session_dir / "output" / safe_name
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arquivo '{safe_name}' não encontrado na sessão."
        )

    try:
        enc_level = request.encryption_algorithm or request.encryption_level or "aes-256"
        perms = request.permissions or {}
        allow_print = perms.get("allow_printing", request.allow_printing)
        allow_copy = perms.get("allow_copying", request.allow_copying)
        allow_modify = perms.get("allow_modifying", request.allow_modifying)
        allow_annot = perms.get("allow_annotating", perms.get("allow_annotations", request.allow_annotations))

        result = await asyncio.to_thread(
            execute_pdf_protect,
            session_dir=session_dir,
            file_id=safe_name,
            user_password=request.user_password,
            owner_password=request.owner_password,
            encryption_level=enc_level,
            allow_printing=allow_print,
            allow_copying=allow_copy,
            allow_modifying=allow_modify,
            allow_annotations=allow_annot,
            output_basename=request.output_filename,
            linearize=request.linearize,
        )

        out_name = result["output_filename"]
        return JSONResponse({
            "success": True,
            "session_id": request.session_id,
            "output_filename": out_name,
            "download_url": f"/api/download/{request.session_id}?filename={urllib.parse.quote(out_name)}",
            "preview_url": f"/api/preview/{request.session_id}?filename={urllib.parse.quote(out_name)}",
            "metrics": result,
        })
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Erro ao proteger PDF: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao proteger PDF: {str(e)}"
        )


@app.post("/api/unlock")
async def unlock_pdf(request: UnlockRequest):
    session_dir = get_session_dir(request.session_id)
    if not session_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão não encontrada ou expirada. Por favor, envie o arquivo novamente."
        )

    safe_name = Path(request.file_id).name
    file_path = session_dir / safe_name
    if not file_path.exists() and (session_dir / "output" / safe_name).exists():
        file_path = session_dir / "output" / safe_name
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arquivo '{safe_name}' não encontrado na sessão."
        )

    try:
        result = await asyncio.to_thread(
            execute_pdf_unlock,
            session_dir=session_dir,
            file_id=safe_name,
            password=request.password,
            output_basename=request.output_filename,
            linearize=request.linearize,
        )

        out_name = result["output_filename"]
        return JSONResponse({
            "success": True,
            "session_id": request.session_id,
            "output_filename": out_name,
            "download_url": f"/api/download/{request.session_id}?filename={urllib.parse.quote(out_name)}",
            "preview_url": f"/api/preview/{request.session_id}?filename={urllib.parse.quote(out_name)}",
            "metrics": result,
        })
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Erro ao desproteger PDF: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao desproteger PDF: {str(e)}"
        )


@app.post("/api/redact")
async def redact_pdf(request: RedactRequest):
    session_dir = get_session_dir(request.session_id)
    if not session_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão não encontrada ou expirada. Por favor, envie o arquivo novamente."
        )

    safe_name = Path(request.file_id).name
    file_path = session_dir / safe_name
    if not file_path.exists() and (session_dir / "output" / safe_name).exists():
        file_path = session_dir / "output" / safe_name
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arquivo '{safe_name}' não encontrado na sessão."
        )

    try:
        patterns_to_use = request.patterns if request.patterns is not None else request.preset_patterns
        if patterns_to_use is None:
            patterns_to_use = ["cpf", "email", "phone"]

        result = await asyncio.to_thread(
            execute_pdf_redact,
            session_dir=session_dir,
            file_id=safe_name,
            custom_terms=request.custom_terms,
            preset_patterns=patterns_to_use,
            clean_metadata=request.clean_metadata,
            output_basename=request.output_filename,
            linearize=request.linearize,
        )

        out_name = result["output_filename"]
        return JSONResponse({
            "success": True,
            "session_id": request.session_id,
            "output_filename": out_name,
            "download_url": f"/api/download/{request.session_id}?filename={urllib.parse.quote(out_name)}",
            "preview_url": f"/api/preview/{request.session_id}?filename={urllib.parse.quote(out_name)}",
            "metrics": result,
        })
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Erro ao redigir/anonimizar PDF: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao redigir/anonimizar PDF: {str(e)}"
        )


@app.post("/api/convert/pdf-to-word")
async def convert_pdf_to_word(request: PdfToWordRequest):
    session_dir = get_session_dir(request.session_id)
    if not session_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão não encontrada ou expirada. Por favor, envie o arquivo novamente."
        )

    safe_name = Path(request.file_id).name
    file_path = session_dir / safe_name
    if not file_path.exists() and (session_dir / "output" / safe_name).exists():
        file_path = session_dir / "output" / safe_name
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arquivo '{safe_name}' não encontrado na sessão."
        )

    try:
        result = await asyncio.to_thread(
            execute_pdf_to_word,
            session_dir=session_dir,
            file_id=safe_name,
            output_basename=request.output_filename,
            start_page=request.start_page,
            end_page=request.end_page,
        )

        out_name = result["output_filename"]
        return JSONResponse({
            "success": True,
            "session_id": request.session_id,
            "output_filename": out_name,
            "download_url": f"/api/download/{request.session_id}?filename={urllib.parse.quote(out_name)}",
            "preview_url": None,
            "is_docx": True,
            "metrics": result,
        })
    except Exception as e:
        logger.error(f"Erro ao converter PDF para Word: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao converter PDF para Word: {str(e)}"
        )


@app.post("/api/convert/word-to-pdf")
async def convert_word_to_pdf(request: WordToPdfRequest):
    session_dir = get_session_dir(request.session_id)
    if not session_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão não encontrada ou expirada. Por favor, envie o arquivo novamente."
        )

    safe_name = Path(request.file_id).name
    file_path = session_dir / safe_name
    if not file_path.exists() and (session_dir / "output" / safe_name).exists():
        file_path = session_dir / "output" / safe_name
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arquivo '{safe_name}' não encontrado na sessão."
        )

    try:
        result = await asyncio.to_thread(
            execute_word_to_pdf,
            session_dir=session_dir,
            file_id=safe_name,
            output_basename=request.output_filename,
            linearize=request.linearize,
        )

        out_name = result["output_filename"]
        return JSONResponse({
            "success": True,
            "session_id": request.session_id,
            "output_filename": out_name,
            "download_url": f"/api/download/{request.session_id}?filename={urllib.parse.quote(out_name)}",
            "preview_url": f"/api/preview/{request.session_id}?filename={urllib.parse.quote(out_name)}",
            "metrics": result,
        })
    except Exception as e:
        logger.error(f"Erro ao converter Word para PDF: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao converter Word para PDF: {str(e)}"
        )


@app.post("/api/convert/image-to-pdf")
async def convert_image_to_pdf(request: ImageToPdfRequest):
    session_dir = get_session_dir(request.session_id)
    if not session_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão não encontrada ou expirada. Por favor, envie as imagens novamente."
        )

    resolved_paths = []
    for img_name in request.image_files:
        safe_name = Path(img_name).name
        img_path = session_dir / safe_name
        if not img_path.exists() and (session_dir / "output" / safe_name).exists():
            img_path = session_dir / "output" / safe_name
        if img_path.exists() and img_path.is_file():
            resolved_paths.append(img_path)

    if not resolved_paths:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum arquivo de imagem válido encontrado para conversão."
        )

    clean_output_name = Path(request.output_filename or "imagens_convertidas.pdf").name
    if not clean_output_name.lower().endswith(".pdf"):
        clean_output_name += ".pdf"

    output_path = session_dir / "output" / clean_output_name

    try:
        result = await asyncio.to_thread(
            execute_image_to_pdf,
            image_paths=resolved_paths,
            output_pdf_path=output_path,
            page_size=request.page_size,
            orientation=request.orientation,
            margin=request.margin,
            linearize=request.linearize,
        )

        out_name = result["output_filename"]
        return JSONResponse({
            "success": True,
            "session_id": request.session_id,
            "output_filename": out_name,
            "download_url": f"/api/download/{request.session_id}?filename={urllib.parse.quote(out_name)}",
            "preview_url": f"/api/preview/{request.session_id}?filename={urllib.parse.quote(out_name)}",
            "metrics": result,
        })
    except Exception as e:
        logger.error(f"Erro ao converter Imagem para PDF: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao converter Imagem para PDF: {str(e)}"
        )


@app.post("/api/watermark")
async def add_pdf_watermark(request: WatermarkRequest):
    session_dir = get_session_dir(request.session_id)
    if not session_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão não encontrada ou expirada. Por favor, envie o arquivo novamente."
        )

    safe_name = Path(request.file_id).name
    file_path = session_dir / safe_name
    if not file_path.exists() and (session_dir / "output" / safe_name).exists():
        file_path = session_dir / "output" / safe_name
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arquivo '{safe_name}' não encontrado na sessão."
        )

    wm_img_path = None
    if request.watermark_type == "image" and request.watermark_image_id:
        safe_img = Path(request.watermark_image_id).name
        candidate = session_dir / safe_img
        if not candidate.exists() and (session_dir / "output" / safe_img).exists():
            candidate = session_dir / "output" / safe_img
        if candidate.exists() and candidate.is_file():
            wm_img_path = candidate

    clean_output_name = Path(request.output_filename or "documento_marca_dagua.pdf").name
    if not clean_output_name.lower().endswith(".pdf"):
        clean_output_name += ".pdf"

    output_path = session_dir / "output" / clean_output_name

    try:
        result = await asyncio.to_thread(
            execute_pdf_watermark,
            input_pdf_path=file_path,
            output_pdf_path=output_path,
            watermark_type=request.watermark_type,
            text=request.text,
            font_size=request.font_size,
            font_color=request.font_color,
            opacity=request.opacity,
            rotation=request.rotation,
            position=request.position,
            watermark_image_path=wm_img_path,
            image_scale=request.image_scale,
            layer=request.layer,
            pages=request.pages,
            linearize=request.linearize,
        )

        out_name = result["output_filename"]
        return JSONResponse({
            "success": True,
            "session_id": request.session_id,
            "output_filename": out_name,
            "download_url": f"/api/download/{request.session_id}?filename={urllib.parse.quote(out_name)}",
            "preview_url": f"/api/preview/{request.session_id}?filename={urllib.parse.quote(out_name)}",
            "metrics": result,
        })
    except Exception as e:
        logger.error(f"Erro ao inserir marca d'água no PDF: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao inserir marca d'água: {str(e)}"
        )


@app.post("/api/footer")
async def add_pdf_footer(request: FooterRequest):
    """
    Insere rodapé, cabeçalho e/ou numeração de páginas personalizada em um documento PDF.
    """
    session_dir = get_session_dir(request.session_id)
    if not session_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão não encontrada ou expirada."
        )

    try:
        result = await asyncio.to_thread(
            execute_pdf_footer,
            session_dir=session_dir,
            file_id=request.file_id,
            footer_text=request.footer_text,
            position=request.position,
            alignment=request.alignment,
            font_size=request.font_size,
            font_color=request.font_color,
            skip_first_page=request.skip_first_page,
            page_start_number=request.page_start_number,
            margin_offset=request.margin_offset,
            output_basename=request.output_filename,
            linearize=request.linearize,
        )

        out_name = result["output_filename"]
        return JSONResponse({
            "success": True,
            "session_id": request.session_id,
            "output_filename": out_name,
            "download_url": f"/api/download/{request.session_id}?filename={urllib.parse.quote(out_name)}",
            "preview_url": f"/api/preview/{request.session_id}?filename={urllib.parse.quote(out_name)}",
            "metrics": result,
        })
    except Exception as e:
        logger.error(f"Erro ao personalizar rodapé do PDF: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao personalizar rodapé: {str(e)}"
        )


@app.post("/api/remove-footer")
async def remove_pdf_footer(request: RemoveFooterRequest):
    """
    Remove fisicamente rodapés, cabeçalhos, textos específicos ou numeração de páginas de um PDF.
    """
    session_dir = get_session_dir(request.session_id)
    if not session_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão não encontrada ou expirada."
        )

    try:
        result = await asyncio.to_thread(
            execute_pdf_remove_footer,
            session_dir=session_dir,
            file_id=request.file_id,
            mode=request.mode,
            target_area=request.target_area,
            margin_height=request.margin_height,
            fill_color=request.fill_color,
            custom_text=request.custom_text,
            remove_page_numbers=request.remove_page_numbers,
            skip_first_page=request.skip_first_page,
            pages=request.pages,
            output_basename=request.output_filename,
            linearize=request.linearize,
        )

        out_name = result["output_filename"]
        return JSONResponse({
            "success": True,
            "session_id": request.session_id,
            "output_filename": out_name,
            "download_url": f"/api/download/{request.session_id}?filename={urllib.parse.quote(out_name)}",
            "preview_url": f"/api/preview/{request.session_id}?filename={urllib.parse.quote(out_name)}",
            "metrics": result,
        })
    except Exception as e:
        logger.error(f"Erro ao remover rodapé do PDF: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao remover rodapé: {str(e)}"
        )




@app.get("/api/download/{session_id}")
async def download_merged_pdf(session_id: str, filename: Optional[str] = "documento_unificado.pdf"):
    clean_name = Path(filename).name
    session_dir = get_session_dir(session_id)
    output_path = session_dir / "output" / clean_name

    if not output_path.exists():
        out_dir = session_dir / "output"
        if out_dir.exists():
            files = list(out_dir.glob("*.pdf")) + list(out_dir.glob("*.zip")) + list(out_dir.glob("*.docx"))
            if files:
                files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                output_path = files[0]
                clean_name = output_path.name

    if not output_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo resultante não encontrado para esta sessão."
        )

    is_zip = clean_name.lower().endswith(".zip")
    is_docx = clean_name.lower().endswith(".docx")
    if is_docx:
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif is_zip:
        media_type = "application/zip"
    else:
        media_type = "application/pdf"

    encoded_filename = urllib.parse.quote(clean_name)
    headers = {
        "Content-Disposition": f"attachment; filename=\"{clean_name}\"; filename*=UTF-8''{encoded_filename}",
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-cache, no-store, must-revalidate",
    }

    return FileResponse(
        path=str(output_path),
        media_type=media_type,
        headers=headers,
    )


@app.get("/api/preview/{session_id}")
async def preview_merged_pdf(session_id: str, filename: Optional[str] = "documento_unificado.pdf"):
    clean_name = Path(filename).name
    lower_name = clean_name.lower()
    if lower_name.endswith(".zip") or lower_name.endswith(".docx") or lower_name.endswith(".doc"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivos compactados (.ZIP) e documentos Word (.DOCX) não possuem pré-visualização inline no leitor. Baixe o arquivo para abrir."
        )

    session_dir = get_session_dir(session_id)
    output_path = session_dir / "output" / clean_name

    if not output_path.exists():
        out_dir = session_dir / "output"
        if out_dir.exists():
            pdfs = list(out_dir.glob("*.pdf"))
            if pdfs:
                pdfs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                output_path = pdfs[0]
                clean_name = output_path.name

    if not output_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo PDF não encontrado para pré-visualização."
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
        "service": "Klynner PDF PRO",
        "storage_dir": str(BASE_TEMP_DIR),
        "engines": ["PikePDF/QPDF (C++)", "PyMuPDF (C++)", "LibreOffice Headless", "pdf2docx", "ReportLab"],
        "features": [
            "Juntar PDF (Merge)",
            "Dividir PDF (Split)",
            "Organizar Páginas (Reorder)",
            "Girar Páginas (Rotate)",
            "Extrair Páginas (Extract)",
            "Proteger com Senha (Encrypt)",
            "Desproteger PDF (Decrypt)",
            "Redigir / Anonimizar (Redact)",
            "Converter PDF para Word (PDF to Word)",
            "Converter Word para PDF (Word to PDF)",
            "Converter Imagem para PDF (Image to PDF)",
            "Inserir Marca d'água (Watermark PDF)",
            "Personalizar Rodapé e Numeração (Footer Customizer)",
            "Remover Rodapé e Cabeçalho (Footer Remover)",
        ],
        "streaming_upload": "Ativo (Zero-RAM Chunking)",
        "menu_system": "Ativo (Página de Menu Visual + Marcadores com UseOutlines)",
        "linearization": "Suportado (Fast Web View)",
    }


class VisitRequest(BaseModel):
    visitor_token: Optional[str] = None


@app.post("/api/stats/visit")
async def record_visit_endpoint(request: Request, body: Optional[VisitRequest] = None):
    token = body.visitor_token if body else None
    client_ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "127.0.0.1")
    if "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    stats = await asyncio.to_thread(record_page_visit, token, client_ip)
    return JSONResponse({"success": True, "stats": stats})


@app.get("/api/stats")
async def get_stats_endpoint():
    stats = await asyncio.to_thread(get_current_stats)
    return JSONResponse({"success": True, "stats": stats})


class FeedbackRequest(BaseModel):
    category: str = Field("sugestao", description="Tipo do feedback (sugestao, bug, elogio, outro)")
    name: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=150)
    rating: int = Field(5, ge=1, le=5)
    message: str = Field(..., min_length=3, max_length=2000)
    tool_context: Optional[str] = Field(None, max_length=50)


@app.post("/api/feedback")
async def create_feedback_endpoint(request: Request, body: FeedbackRequest):
    client_ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "127.0.0.1")
    if "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()

    result = await asyncio.to_thread(
        save_feedback,
        category=body.category,
        message=body.message,
        name=body.name,
        email=body.email,
        rating=body.rating,
        tool_context=body.tool_context,
        client_ip=client_ip,
    )
    return JSONResponse(result)


@app.get("/api/feedback/recent")
async def get_recent_feedbacks_endpoint():
    feedbacks = await asyncio.to_thread(get_recent_feedbacks, 6)
    total_count = await asyncio.to_thread(get_feedback_count)
    return JSONResponse({"success": True, "feedbacks": feedbacks, "total": total_count})


class AdminAuthRequest(BaseModel):
    admin_key: str = Field(..., min_length=1)


@app.post("/api/feedback/verify-admin")
async def verify_admin_key_endpoint(body: AdminAuthRequest):
    if not is_valid_admin_key(body.admin_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave de administrador incorreta."
        )
    return JSONResponse({"success": True, "message": "Autenticado como moderador."})


@app.delete("/api/feedback/{feedback_id}")
async def delete_feedback_endpoint(feedback_id: int, request: Request):
    key = request.headers.get("x-admin-key") or request.query_params.get("admin_key")
    if not is_valid_admin_key(key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acesso não autorizado. Chave de moderação inválida."
        )

    deleted = await asyncio.to_thread(delete_feedback, feedback_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comentário não encontrado ou já excluído."
        )
    return JSONResponse({"success": True, "message": f"Comentário #{feedback_id} excluído com sucesso."})



