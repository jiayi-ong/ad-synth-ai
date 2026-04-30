"""Hash-based research cache for competitor analysis results."""
import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

_DB_PATH = Path("data/research_cache.db")
_TTL_DAYS = 7


def _get_conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS research_cache (
            query_hash TEXT PRIMARY KEY,
            query_text TEXT NOT NULL,
            query_type TEXT NOT NULL,
            result     TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def _hash_query(query: str) -> str:
    return hashlib.sha256(query.strip().lower().encode()).hexdigest()


def check_research_cache(query: str) -> str | None:
    """Return cached research result for query if not expired, else None."""
    try:
        conn = _get_conn()
        now = datetime.utcnow().isoformat()
        row = conn.execute(
            "SELECT result FROM research_cache WHERE query_hash = ? AND expires_at > ?",
            (_hash_query(query), now),
        ).fetchone()
        conn.close()
        if row:
            logger.info("Research cache hit for query: %.60s", query)
            return row[0]
        return None
    except Exception as exc:
        logger.warning("research_cache check failed: %s", exc)
        return None


def store_research_cache(query: str, result: str, query_type: str = "competitors") -> None:
    """Store research result in cache with TTL."""
    try:
        conn = _get_conn()
        now = datetime.utcnow()
        conn.execute(
            """INSERT OR REPLACE INTO research_cache
               (query_hash, query_text, query_type, result, created_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                _hash_query(query),
                query[:500],
                query_type,
                result if isinstance(result, str) else json.dumps(result),
                now.isoformat(),
                (now + timedelta(days=_TTL_DAYS)).isoformat(),
            ),
        )
        conn.commit()
        conn.close()
        logger.info("Research cached for query: %.60s (TTL %d days)", query, _TTL_DAYS)
    except Exception as exc:
        logger.warning("research_cache store failed: %s", exc)
