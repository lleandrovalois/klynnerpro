"""
Módulo de Feedback, Sugestões e Comentários para o Klynner PRO.
Armazena mensagens dos usuários em SQLite local com anonimização LGPD.
"""

from datetime import datetime, timezone
import hashlib
import hmac
import html
import logging
import os
from pathlib import Path
import sqlite3
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger("feedback")

DB_DIR = Path("data")
DB_PATH = DB_DIR / "analytics.db"

# Chave secreta de moderação (configurável via variável de ambiente ADMIN_KEY)
ADMIN_SECRET_KEY = os.environ.get("ADMIN_KEY", "klynneradmin")

_db_lock = threading.Lock()


def is_valid_admin_key(key: Optional[str]) -> bool:
    """Verifica de forma segura em tempo constante se a chave fornecida corresponde à do administrador."""
    if not key or not isinstance(key, str):
        return False
    return hmac.compare_digest(key.strip().encode("utf-8"), ADMIN_SECRET_KEY.strip().encode("utf-8"))


def get_db_connection() -> sqlite3.Connection:
    """Cria e retorna conexão com o banco SQLite."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_feedback_db() -> None:
    """Inicializa a tabela de feedbacks se não existir e aplica migrações não destrutivas."""
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

            # Migração segura e não destrutiva para respostas da moderação (preserva dados de produção)
            cursor.execute("PRAGMA table_info(user_feedbacks);")
            columns = {row["name"] for row in cursor.fetchall()}
            if "admin_reply" not in columns:
                cursor.execute("ALTER TABLE user_feedbacks ADD COLUMN admin_reply TEXT;")
            if "replied_at" not in columns:
                cursor.execute("ALTER TABLE user_feedbacks ADD COLUMN replied_at TIMESTAMP;")
            if "replied_by" not in columns:
                cursor.execute("ALTER TABLE user_feedbacks ADD COLUMN replied_by TEXT;")
            if "email_sent" not in columns:
                cursor.execute("ALTER TABLE user_feedbacks ADD COLUMN email_sent INTEGER DEFAULT 0;")
            if "last_email_sent_at" not in columns:
                cursor.execute("ALTER TABLE user_feedbacks ADD COLUMN last_email_sent_at TIMESTAMP;")
            if "email_error" not in columns:
                cursor.execute("ALTER TABLE user_feedbacks ADD COLUMN email_error TEXT;")

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


def get_recent_feedbacks(limit: int = 6, is_admin: bool = False) -> List[Dict[str, Any]]:
    """Retorna os feedbacks mais recentes para exibição comunitária (ou com dados de moderação se is_admin=True)."""
    with _db_lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, category, name, email, rating, message, tool_context, created_at,
                       admin_reply, replied_at, replied_by, email_sent, last_email_sent_at, email_error
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
            # Exibe primeiro nome e inicial do sobrenome para privacidade pública
            parts = name_val.split()
            if len(parts) > 1:
                display_name = f"{parts[0]} {parts[1][0]}."
            else:
                display_name = parts[0]

        row_keys = r.keys()
        item = {
            "id": r["id"],
            "category": r["category"],
            "name": display_name,
            "rating": r["rating"],
            "message": r["message"],
            "tool_context": r["tool_context"],
            "created_at": r["created_at"],
            "admin_reply": r["admin_reply"] if "admin_reply" in row_keys else None,
            "replied_at": r["replied_at"] if "replied_at" in row_keys else None,
            "replied_by": r["replied_by"] if "replied_by" in row_keys else None,
        }

        # Dados adicionais para administradores/moderadores
        if is_admin:
            item["full_name"] = name_val or "Usuário Anônimo"
            item["email"] = r["email"] if "email" in row_keys else None
            item["email_sent"] = bool(r["email_sent"]) if "email_sent" in row_keys and r["email_sent"] else False
            item["last_email_sent_at"] = r["last_email_sent_at"] if "last_email_sent_at" in row_keys else None
            item["email_error"] = r["email_error"] if "email_error" in row_keys else None

        results.append(item)
    return results


def get_feedback_by_id(feedback_id: int) -> Optional[Dict[str, Any]]:
    """Busca um feedback específico pelo ID com todos os campos disponíveis."""
    with _db_lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, category, name, email, rating, message, tool_context, created_at,
                       admin_reply, replied_at, replied_by, email_sent, last_email_sent_at, email_error
                FROM user_feedbacks
                WHERE id = ?
            """, (int(feedback_id),))
            r = cursor.fetchone()
            if not r:
                return None

            row_keys = r.keys()
            return {
                "id": r["id"],
                "category": r["category"],
                "name": r["name"] or "Usuário Anônimo",
                "email": r["email"] if "email" in row_keys else None,
                "rating": r["rating"],
                "message": r["message"],
                "tool_context": r["tool_context"],
                "created_at": r["created_at"],
                "admin_reply": r["admin_reply"] if "admin_reply" in row_keys else None,
                "replied_at": r["replied_at"] if "replied_at" in row_keys else None,
                "replied_by": r["replied_by"] if "replied_by" in row_keys else None,
                "email_sent": bool(r["email_sent"]) if "email_sent" in row_keys and r["email_sent"] else False,
                "last_email_sent_at": r["last_email_sent_at"] if "last_email_sent_at" in row_keys else None,
                "email_error": r["email_error"] if "email_error" in row_keys else None,
            }


def save_feedback_reply(
    feedback_id: int,
    reply_text: str,
    replied_by: Optional[str] = "Equipe Klynner",
    email_sent: Optional[bool] = None,
    email_error: Optional[str] = None,
) -> bool:
    """Salva ou atualiza a resposta oficial de moderação para um comentário."""
    clean_reply = html.escape(reply_text.strip())
    clean_author = html.escape(replied_by.strip()) if replied_by and replied_by.strip() else "Equipe Klynner"
    now_iso = datetime.now(timezone.utc).isoformat()

    with _db_lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if email_sent is not None:
                email_sent_int = 1 if email_sent else 0
                sent_at = now_iso if email_sent else None
                cursor.execute("""
                    UPDATE user_feedbacks
                    SET admin_reply = ?, replied_at = ?, replied_by = ?,
                        email_sent = ?, last_email_sent_at = ?, email_error = ?
                    WHERE id = ?
                """, (clean_reply, now_iso, clean_author, email_sent_int, sent_at, email_error, int(feedback_id)))
            else:
                cursor.execute("""
                    UPDATE user_feedbacks
                    SET admin_reply = ?, replied_at = ?, replied_by = ?
                    WHERE id = ?
                """, (clean_reply, now_iso, clean_author, int(feedback_id)))
            updated = cursor.rowcount > 0
            conn.commit()

    if updated:
        logger.info(f"Feedback #{feedback_id} respondido com sucesso por '{clean_author}' (email_sent={email_sent}).")
    return updated


def delete_feedback_reply(feedback_id: int) -> bool:
    """Remove a resposta oficial de um comentário sem excluir o comentário original do usuário."""
    with _db_lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_feedbacks
                SET admin_reply = NULL, replied_at = NULL, replied_by = NULL,
                    email_sent = 0, last_email_sent_at = NULL, email_error = NULL
                WHERE id = ?
            """, (int(feedback_id),))
            cleared = cursor.rowcount > 0
            conn.commit()

    if cleared:
        logger.info(f"Resposta do Feedback #{feedback_id} removida pela moderação.")
    return cleared


def get_feedback_count() -> int:
    """Retorna a contagem total de feedbacks recebidos."""
    with _db_lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS total FROM user_feedbacks")
            row = cursor.fetchone()
            return int(row["total"]) if row else 0


def delete_feedback(feedback_id: int) -> bool:
    """Remove permanentemente um comentário do banco pelo seu ID."""
    with _db_lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_feedbacks WHERE id = ?", (int(feedback_id),))
            deleted = cursor.rowcount > 0
            conn.commit()

    if deleted:
        logger.info(f"Feedback #{feedback_id} foi excluído com sucesso pela moderação.")
    return deleted


# Inicialização segura das tabelas mesmo se o lifespan do ASGI não tiver sido acionado
try:
    init_feedback_db()
except Exception:
    pass

