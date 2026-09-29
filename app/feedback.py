"""
Módulo de Feedback, Sugestões e Comentários para o Klynner PRO.
Armazena mensagens dos usuários em SQLite local com anonimização LGPD.
"""

from datetime import datetime, timezone
import hashlib
import html
import logging
from pathlib import Path
import sqlite3
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger("feedback")

DB_DIR = Path("data")
DB_PATH = DB_DIR / "analytics.db"

_db_lock = threading.Lock()


def get_db_connection() -> sqlite3.Connection:
    """Cria e retorna conexão com o banco SQLite."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_feedback_db() -> None:
    """Inicializa a tabela de feedbacks se não existir."""
    with _db_lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_feedbacks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    name TEXT,
                    email TEXT,
                    rating INTEGER DEFAULT 5,
                    message TEXT NOT NULL,
                    tool_context TEXT,
                    ip_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_created ON user_feedbacks(created_at DESC);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_cat ON user_feedbacks(category);
            """)
            conn.commit()


def hash_ip(ip_address: Optional[str]) -> str:
    """Anonimiza o IP do remetente com hash SHA-256."""
    clean_ip = (ip_address or "127.0.0.1").strip()
    return hashlib.sha256(f"klynner_feedback_{clean_ip}".encode("utf-8")).hexdigest()[:16]


def save_feedback(
    category: str,
    message: str,
    name: Optional[str] = None,
    email: Optional[str] = None,
    rating: int = 5,
    tool_context: Optional[str] = None,
    client_ip: Optional[str] = None,
) -> Dict[str, Any]:
    """Salva um novo feedback no banco de dados de forma segura."""
    clean_cat = (category or "sugestao").strip().lower()
    if clean_cat not in ("sugestao", "bug", "elogio", "outro"):
        clean_cat = "sugestao"

    clean_message = html.escape(message.strip())
    clean_name = html.escape(name.strip()) if name and name.strip() else None
    clean_email = email.strip() if email and email.strip() else None
    clean_rating = max(1, min(5, int(rating or 5)))
    clean_tool = (tool_context or "").strip()[:50]
    ip_h = hash_ip(client_ip)

    with _db_lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_feedbacks (category, name, email, rating, message, tool_context, ip_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (clean_cat, clean_name, clean_email, clean_rating, clean_message, clean_tool, ip_h))
            feedback_id = cursor.lastrowid
            conn.commit()

    logger.info(f"Feedback #{feedback_id} recebido com sucesso [{clean_cat}, rating={clean_rating}].")
    return {
        "success": True,
        "id": feedback_id,
        "message": "Feedback recebido com sucesso! Agradecemos sua colaboração.",
    }


def get_recent_feedbacks(limit: int = 6) -> List[Dict[str, Any]]:
    """Retorna os feedbacks mais recentes para exibição comunitária."""
    with _db_lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, category, name, rating, message, tool_context, created_at
                FROM user_feedbacks
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()

    results = []
    for r in rows:
        name_val = r["name"]
        if not name_val:
            display_name = "Usuário Anônimo"
        else:
            # Exibe primeiro nome e inicial do sobrenome para privacidade
            parts = name_val.split()
            if len(parts) > 1:
                display_name = f"{parts[0]} {parts[1][0]}."
            else:
                display_name = parts[0]

        results.append({
            "id": r["id"],
            "category": r["category"],
            "name": display_name,
            "rating": r["rating"],
            "message": r["message"],
            "tool_context": r["tool_context"],
            "created_at": r["created_at"],
        })
    return results


def get_feedback_count() -> int:
    """Retorna a contagem total de feedbacks recebidos."""
    with _db_lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS total FROM user_feedbacks")
            row = cursor.fetchone()
            return int(row["total"]) if row else 0
