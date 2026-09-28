"""
Módulo de Segurança e Criptografia de PDFs (Proteger e Desproteger)
Utiliza QPDF C++ (via pikepdf) para criptografia de nível bancário (AES-128 e AES-256)
e controle granular de permissões de impressão, cópia e edição.
"""

import logging
from pathlib import Path
import time
from typing import Any, Dict, Optional

import pikepdf

logger = logging.getLogger("pdf_protector")


def execute_pdf_protect(
    session_dir: Path,
    file_id: str,
    user_password: Optional[str] = None,
    owner_password: Optional[str] = None,
    encryption_level: str = "aes-256",
    allow_printing: bool = False,
    allow_copying: bool = False,
    allow_modifying: bool = False,
    allow_annotations: bool = False,
    output_basename: Optional[str] = None,
    linearize: bool = True,
) -> Dict[str, Any]:
    """
    Aplica criptografia de nível bancário e restrições de permissão ao PDF.
    
    Args:
        session_dir: Diretório temporário da sessão
        file_id: Nome ou identificador do arquivo no diretório da sessão
        user_password: Senha para abertura do documento
        owner_password: Senha mestra de controle de permissões
        encryption_level: 'aes-256' (R=6) ou 'aes-128' (R=4)
        allow_printing: Se True, permite impressão em alta e baixa resolução
        allow_copying: Se True, permite cópia/extração de texto e gráficos
        allow_modifying: Se True, permite alteração do conteúdo
        allow_annotations: Se True, permite anotações e preenchimento de formulários
        output_basename: Nome base para o arquivo resultante
        linearize: Ativa Fast Web View
    """
    t0 = time.time()
    input_path = session_dir / Path(file_id).name
    if not input_path.exists():
        input_path = session_dir / "output" / Path(file_id).name
    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo de origem '{file_id}' não encontrado na sessão.")

    # Se nenhuma senha foi fornecida, exige pelo menos uma para proteger
    u_pwd = (user_password or "").strip()
    o_pwd = (owner_password or "").strip()

    if not u_pwd and not o_pwd:
        raise ValueError("É necessário definir ao menos uma senha (de abertura ou de proprietário) para proteger o PDF.")

    # Se apenas a senha de usuário foi fornecida, usa a mesma como proprietário para garantir segurança
    if not o_pwd:
        o_pwd = u_pwd
    if not u_pwd:
        # Se só forneceu senha de proprietário, o arquivo abre sem senha, mas tem permissões restritas!
        u_pwd = ""

    # Determina o nível de criptografia
    r_val = 6 if encryption_level.lower() == "aes-256" else 4

    # Configura permissões
    permissions = pikepdf.Permissions(
        accessibility=True,  # Mantém acessibilidade para leitores de tela
        extract=allow_copying,
        modify_annotation=allow_annotations,
        modify_assembly=allow_modifying,
        modify_form=allow_annotations or allow_modifying,
        modify_other=allow_modifying,
        print_lowres=allow_printing,
        print_highres=allow_printing,
    )

    encryption_config = pikepdf.Encryption(
        owner=o_pwd,
        user=u_pwd,
        R=r_val,
        aes=True,
        metadata=True,
        allow=permissions,
    )

    # Define nome de saída
    clean_stem = (output_basename or input_path.stem).strip()
    clean_stem = Path(clean_stem).stem
    if not clean_stem.endswith("_protegido"):
        clean_stem = f"{clean_stem}_protegido"
    out_filename = f"{clean_stem}.pdf"

    output_dir = session_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / out_filename

    with pikepdf.open(input_path) as pdf:
        num_pages = len(pdf.pages)
        pdf.save(
            out_path,
            encryption=encryption_config,
            linearize=linearize,
        )

    elapsed = time.time() - t0
    filesize = out_path.stat().st_size

    logger.info(
        f"PDF protegido com sucesso: '{out_filename}', {num_pages} páginas, "
        f"{filesize} bytes, nível={encryption_level}, linearizado={linearize} em {elapsed:.2f}s"
    )

    return {
        "output_filename": out_filename,
        "filesize": filesize,
        "output_bytes": filesize,
        "pages": num_pages,
        "total_pages": num_pages,
        "encryption_level": encryption_level.upper(),
        "encryption_applied": encryption_level.upper(),
        "has_user_password": bool(u_pwd),
        "has_owner_password": bool(o_pwd),
        "allow_printing": allow_printing,
        "allow_copying": allow_copying,
        "allow_modifying": allow_modifying,
        "allow_annotations": allow_annotations,
        "linearized": linearize,
        "time_seconds": round(elapsed, 3),
        "duration_seconds": round(elapsed, 3),
    }


def execute_pdf_unlock(
    session_dir: Path,
    file_id: str,
    password: Optional[str] = None,
    output_basename: Optional[str] = None,
    linearize: bool = True,
) -> Dict[str, Any]:
    """
    Remove senhas e restrições de permissão de um PDF criptografado.
    
    Args:
        session_dir: Diretório temporário da sessão
        file_id: Nome ou identificador do arquivo no diretório da sessão
        password: Senha de abertura ou de proprietário
        output_basename: Nome base para o arquivo resultante
        linearize: Ativa Fast Web View
    """
    t0 = time.time()
    input_path = session_dir / Path(file_id).name
    if not input_path.exists():
        input_path = session_dir / "output" / Path(file_id).name
    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo de origem '{file_id}' não encontrado na sessão.")

    pwd = (password or "").strip()

    try:
        pdf = pikepdf.open(input_path, password=pwd)
    except pikepdf.PasswordError:
        raise ValueError("A senha fornecida está incorreta ou o documento exige senha para abertura.")
    except Exception as e:
        raise ValueError(f"Não foi possível abrir o PDF para desproteção: {str(e)}")

    with pdf:
        num_pages = len(pdf.pages)
        was_encrypted = pdf.is_encrypted

        clean_stem = (output_basename or input_path.stem).strip()
        clean_stem = Path(clean_stem).stem
        if not clean_stem.endswith("_desprotegido"):
            clean_stem = f"{clean_stem}_desprotegido"
        out_filename = f"{clean_stem}.pdf"

        output_dir = session_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / out_filename

        # Salva sem criptografia, removendo todas as restrições e senhas
        pdf.save(
            out_path,
            encryption=False,
            linearize=linearize,
        )

    elapsed = time.time() - t0
    filesize = out_path.stat().st_size

    logger.info(
        f"PDF desprotegido com sucesso: '{out_filename}', {num_pages} páginas, "
        f"{filesize} bytes em {elapsed:.2f}s"
    )

    return {
        "output_filename": out_filename,
        "filesize": filesize,
        "output_bytes": filesize,
        "pages": num_pages,
        "total_pages": num_pages,
        "was_encrypted": was_encrypted,
        "unlocked": True,
        "linearized": linearize,
        "time_seconds": round(elapsed, 3),
        "duration_seconds": round(elapsed, 3),
    }
