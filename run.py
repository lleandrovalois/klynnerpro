"""
Script de inicialização do PDF Merger Pro.
Inicia o servidor Uvicorn com suporte a carregamento assíncrono e streaming de alta performance.
"""

import sys
from pathlib import Path

# Garante suporte a UTF-8 no console do Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import uvicorn

# Adiciona o diretório raiz ao PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def main():
    port = 8000
    host = "127.0.0.1"
    url = f"http://{host}:{port}"

    print("=" * 65)
    print("  [+] Klynner PDF - Uniao Inteligente de Documentos")
    print(f"  [*] Motor de Fusao: QPDF C++ (PikePDF) + PyPDF Fallback")
    print(f"  [*] Suporte a Arquivos Grandes: Streaming Zero-RAM Ativo")
    print(f"  [*] Menu de Documentos: Sumario Visual + Outlines Ativos")
    print(f"  [>] Acesse a aplicacao em: {url}")
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

