"""
RAG-based trend cache using sqlite-vec for vector similarity search.
Embeddings are generated using Gemini text-embedding-004 (768 dimensions).
"""
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CACHE_DB = Path("data/trend_cache.db")
_DIM = 768
_SIMILARITY_THRESHOLD = 0.85


def _get_conn() -> sqlite3.Connection:
    _CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_CACHE_DB))
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except Exception as e:
        logger.warning("sqlite-vec not available: %s — trend cache disabled", e)
        return conn
    conn.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS trend_cache USING vec0(embedding float[{_DIM}])"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS trend_cache_data (rowid INTEGER PRIMARY KEY, query TEXT, result TEXT)"
    )
    conn.commit()
    return conn


def _embed(text: str) -> list[float] | None:
    try:
        from google import genai
        from backend.core.config import settings
        client = genai.Client(
            api_key=settings.google_api_key if not settings.google_genai_use_vertexai else None,
            vertexai=settings.google_genai_use_vertexai,
            project=settings.gcp_project_id or None,
            location=settings.gcp_region,
        )
        resp = client.models.embed_content(
            model="text-embedding-004",
            contents=[text],
        )
        return resp.embeddings[0].values
    except Exception as e:
        logger.warning("Embedding failed: %s", e)
        return None


def check_trend_cache(query: str, similarity_threshold: float = _SIMILARITY_THRESHOLD) -> str | None:
    """
    Check if a similar trend query result exists in the cache.
    Returns the cached result string if found above the similarity threshold, else None.
    """
    try:
        vec = _embed(query)
        if not vec:
            return None
        conn = _get_conn()
        # sqlite-vec returns distance (lower = more similar); convert to cosine similarity
        rows = conn.execute(
            f"SELECT rowid, distance FROM trend_cache WHERE embedding MATCH ? AND k = 5",
            [json.dumps(vec)],
        ).fetchall()
        if not rows:
            return None
        best_rowid, best_dist = min(rows, key=lambda r: r[1])
        similarity = 1.0 - best_dist
        if similarity < similarity_threshold:
            return None
        data = conn.execute(
            "SELECT result FROM trend_cache_data WHERE rowid = ?", [best_rowid]
        ).fetchone()
        if data:
            logger.info("Trend cache HIT for query: %s (similarity=%.3f)", query, similarity)
            return data[0]
    except Exception as e:
        logger.warning("check_trend_cache error: %s", e)
    return None


def store_trend_cache(query: str, result: str) -> None:
    """
    Store a trend research result in the cache with its embedding.
    """
    try:
        vec = _embed(query)
        if not vec:
            return
        conn = _get_conn()
        conn.execute("INSERT INTO trend_cache_data (query, result) VALUES (?, ?)", [query, result])
        rowid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("INSERT INTO trend_cache (rowid, embedding) VALUES (?, ?)", [rowid, json.dumps(vec)])
        conn.commit()
        logger.info("Trend cache stored for query: %s", query)
    except Exception as e:
        logger.warning("store_trend_cache error: %s", e)
