"""
Multi-namespace knowledge store using sqlite-vec for vector similarity search.
Embeddings are generated using Gemini gemini-embedding-001 (3072 dimensions).

Namespaces:
  - "competitor"           competitor profiles, pricing, positioning
  - "market_research"      market sizing, segment attractiveness, dynamics
  - "pricing_benchmarks"   pricing data points and margin benchmarks
"""
import json
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

_STORE_DB = Path("data/knowledge_store.db")
_DIM = 3072
_SIMILARITY_THRESHOLD = 0.82

_VALID_NAMESPACES = {"competitor", "market_research", "pricing_benchmarks"}


def _get_conn() -> sqlite3.Connection:
    _STORE_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_STORE_DB))
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except Exception as e:
        logger.warning("sqlite-vec not available: %s — knowledge store disabled", e)
        return conn
    conn.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS ks_vectors USING vec0(embedding float[{_DIM}])"
    )
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ks_data (
            rowid      INTEGER PRIMARY KEY,
            namespace  TEXT NOT NULL,
            query      TEXT NOT NULL,
            result     TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def _embed(text: str) -> list[float] | None:
    try:
        from google import genai
        from backend.core.config import settings
        if settings.google_genai_use_vertexai:
            client = genai.Client(
                vertexai=True,
                project=settings.gcp_project_id,
                location=settings.gcp_region,
            )
        else:
            client = genai.Client(api_key=settings.google_api_key)
        resp = client.models.embed_content(
            model="gemini-embedding-001",
            contents=[text],
        )
        return resp.embeddings[0].values
    except Exception as e:
        logger.warning("Embedding failed: %s", e)
        return None


_CACHE_MISS_SENTINEL = "NO_CACHED_RESULT"


def check_knowledge_store(
    query: str,
    namespace: str = "market_research",
) -> str:
    """
    Check if similar content exists in the knowledge store for the given namespace.
    Valid namespaces: 'competitor', 'market_research', 'pricing_benchmarks'.
    Returns cached result string if found above similarity threshold, or the
    string 'NO_CACHED_RESULT' if not found (never returns None, to avoid
    confusing the LLM with a null function response).
    """
    if namespace not in _VALID_NAMESPACES:
        logger.warning("check_knowledge_store: unknown namespace '%s'", namespace)
        return _CACHE_MISS_SENTINEL
    try:
        vec = _embed(query)
        if not vec:
            return _CACHE_MISS_SENTINEL
        conn = _get_conn()
        rows = conn.execute(
            "SELECT rowid, distance FROM ks_vectors WHERE embedding MATCH ? AND k = 5",
            [json.dumps(vec)],
        ).fetchall()
        if not rows:
            return _CACHE_MISS_SENTINEL
        best_match = None
        best_similarity = 0.0
        for rowid, dist in rows:
            similarity = 1.0 - dist
            if similarity < _SIMILARITY_THRESHOLD:
                continue
            data = conn.execute(
                "SELECT namespace, result FROM ks_data WHERE rowid = ?", [rowid]
            ).fetchone()
            if data and data[0] == namespace and similarity > best_similarity:
                best_similarity = similarity
                best_match = data[1]
        if best_match:
            logger.info(
                "Knowledge store HIT ns=%s query=%.60s sim=%.3f",
                namespace, query, best_similarity,
            )
            return best_match
        return _CACHE_MISS_SENTINEL
    except Exception as e:
        logger.warning("check_knowledge_store error: %s", e)
    return _CACHE_MISS_SENTINEL


def store_knowledge_store(
    query: str,
    result: str,
    namespace: str = "market_research",
) -> None:
    """
    Store a result in the knowledge store under the given namespace.
    Valid namespaces: 'competitor', 'market_research', 'pricing_benchmarks'.
    """
    if namespace not in _VALID_NAMESPACES:
        logger.warning("store_knowledge_store: unknown namespace '%s'", namespace)
        return
    try:
        from datetime import datetime, timezone
        vec = _embed(query)
        if not vec:
            return
        conn = _get_conn()
        conn.execute(
            "INSERT INTO ks_data (namespace, query, result, created_at) VALUES (?, ?, ?, ?)",
            [namespace, query[:500], result, datetime.now(timezone.utc).isoformat()],
        )
        rowid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO ks_vectors (rowid, embedding) VALUES (?, ?)",
            [rowid, json.dumps(vec)],
        )
        conn.commit()
        logger.info("Knowledge store stored ns=%s query=%.60s", namespace, query)
    except Exception as e:
        logger.warning("store_knowledge_store error: %s", e)
