"""
Módulo de Analytics e Contador de Visitas Persistente para o Klynner PRO.
Armazena métricas agregadas em banco SQLite local (zero dependências externas),
em total conformidade com a LGPD (endereços IP são anonimizados com hash SHA-256).
"""

from datetime import datetime, timezone
import hashlib
import logging
from pathlib import Path
import sqlite3
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger("analytics")

DB_DIR = Path("data")
DB_PATH = DB_DIR / "analytics.db"

_db_lock = threading.Lock()


def get_db_connection() -> sqlite3.Connection:
    """Cria e retorna uma conexão com o SQLite garantindo diretório existente."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_analytics_db() -> None:
    """Inicializa as tabelas necessárias no SQLite se não existirem."""
    with _db_lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS site_visits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    visitor_token TEXT NOT NULL,
                    ip_hash TEXT NOT NULL,
                    date_str TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_visits_date ON site_visits(date_str);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_visits_visitor ON site_visits(visitor_token, date_str);
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS global_counters (
                    metric_key TEXT PRIMARY KEY,
                    count_value INTEGER NOT NULL DEFAULT 0
                );
            """)
            # Inicializa contador global se vazio
            cursor.execute("""
                INSERT OR IGNORE INTO global_counters (metric_key, count_value)
                VALUES ('total_visits', 0);
            """)
            conn.commit()


def hash_ip(ip_address: Optional[str]) -> str:
    """Anonimiza o IP do visitante com SHA-256 para estrito cumprimento da LGPD."""
    clean_ip = (ip_address or "127.0.0.1").strip()
    return hashlib.sha256(f"klynner_salt_{clean_ip}".encode("utf-8")).hexdigest()[:16]


def record_page_visit(visitor_token: Optional[str], client_ip: Optional[str]) -> Dict[str, Any]:
    """
    Registra um acesso à aplicação, deduplica visitas únicas do mesmo visitante no mesmo dia,
    e incrementa os contadores de visita total e diária.
    """
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ip_h = hash_ip(client_ip)
    token = (visitor_token or "").strip()
    if not token:
        token = f"vis_{ip_h}_{today_str}"

    with _db_lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Verifica se já registrou visita deste visitante hoje
            cursor.execute(
                "SELECT id FROM site_visits WHERE (visitor_token = ? OR ip_hash = ?) AND date_str = ? LIMIT 1",
                (token, ip_h, today_str)
            )
            already_visited_today = cursor.fetchone() is not None

            # Registra no log detalhado
            cursor.execute(
                "INSERT INTO site_visits (visitor_token, ip_hash, date_str) VALUES (?, ?, ?)",
                (token, ip_h, today_str)
            )

            # Incrementa o contador geral
            cursor.execute(
                "UPDATE global_counters SET count_value = count_value + 1 WHERE metric_key = 'total_visits'"
            )

            # Conta total geral acumulado
            cursor.execute("SELECT count_value FROM global_counters WHERE metric_key = 'total_visits'")
            row_total = cursor.fetchone()
            total_visits = row_total["count_value"] if row_total else 1

            # Conta total de visitas de hoje
            cursor.execute("SELECT COUNT(*) as count_today FROM site_visits WHERE date_str = ?", (today_str,))
            row_today = cursor.fetchone()
            today_views = row_today["count_today"] if row_today else 1

            # Conta visitantes únicos de hoje
            cursor.execute("SELECT COUNT(DISTINCT visitor_token) as count_unique FROM site_visits WHERE date_str = ?", (today_str,))
            row_unique = cursor.fetchone()
            unique_today = row_unique["count_unique"] if row_unique else 1

            conn.commit()

    return {
        "total_visits": total_visits,
        "today_views": today_views,
        "unique_today": unique_today,
        "is_new_today": not already_visited_today,
        "visitor_token": token,
    }


def get_current_stats() -> Dict[str, Any]:
    """Retorna as estatísticas atuais sem registrar uma nova visita."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with _db_lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT count_value FROM global_counters WHERE metric_key = 'total_visits'")
            row_total = cursor.fetchone()
            total_visits = row_total["count_value"] if row_total else 0

            cursor.execute("SELECT COUNT(*) as count_today FROM site_visits WHERE date_str = ?", (today_str,))
            row_today = cursor.fetchone()
            today_views = row_today["count_today"] if row_today else 0

            cursor.execute("SELECT COUNT(DISTINCT visitor_token) as count_unique FROM site_visits WHERE date_str = ?", (today_str,))
            row_unique = cursor.fetchone()
            unique_today = row_unique["count_unique"] if row_unique else 0

    return {
        "total_visits": total_visits,
        "today_views": today_views,
        "unique_today": unique_today,
    }
