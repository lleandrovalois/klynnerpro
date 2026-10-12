"""
Script de inicialização do PDF Merger Pro.
Inicia o servidor Uvicorn com suporte a carregamento assíncrono e streaming de alta performance.
"""

import os
import sys
from pathlib import Path

# Garante suporte a UTF-8 no console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent
# Suporte a venv no Windows (.venv/Lib/site-packages) e Linux (.venv/lib/pythonX.Y/site-packages)
VENV_WINDOWS = ROOT_DIR / ".venv" / "Lib" / "site-packages"
if VENV_WINDOWS.exists() and str(VENV_WINDOWS) not in sys.path:
    sys.path.insert(0, str(VENV_WINDOWS))

VENV_LINUX_PARENT = ROOT_DIR / ".venv" / "lib"
if VENV_LINUX_PARENT.exists():
    for p in VENV_LINUX_PARENT.glob("python*/site-packages"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import uvicorn


def main():
    # Render e provedores cloud injetam a variável PORT
    port = int(os.environ.get("PORT", 8000))
    # Em produção/cloud escuta em 0.0.0.0; localmente em 127.0.0.1
    host = os.environ.get("HOST", "0.0.0.0" if "PORT" in os.environ else "127.0.0.1")
    url = f"http://{host}:{port}"

    print("=" * 65)
    print("  [+] Klynner PDF - Uniao Inteligente de Documentos")
    print(f"  [*] Motor de Fusao: QPDF C++ (PikePDF) + PyPDF Fallback")
    print(f"  [*] Suporte a Arquivos Grandes: Streaming Zero-RAM Ativo")
    print(f"  [*] Menu de Documentos: Sumario Visual + Outlines Ativos")
    print(f"  [>] Servidor rodando em: {url} (Host: {host}, Port: {port})")
    print("=" * 65)

    # Executa o servidor uvicorn
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
        timeout_keep_alive=120,
    )


if __name__ == "__main__":
    main()

