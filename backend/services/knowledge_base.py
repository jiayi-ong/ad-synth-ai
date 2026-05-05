"""
In-memory knowledge base for the chatbot assistant.

Loads data/chatbot_knowledge.json at module init, embeds all entries using
gemini-embedding-001, and supports fast cosine similarity search via numpy.

If data/chatbot_knowledge_vectors.npy exists it is loaded directly to skip
the embedding API call on every cold start.
"""
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger("chatbot")

_KNOWLEDGE_JSON = Path("data/chatbot_knowledge.json")
_VECTORS_NPY = Path("data/chatbot_knowledge_vectors.npy")
_EMBED_MODEL = "gemini-embedding-001"
_EMBED_DIM = 3072

_entries: list[dict[str, Any]] = []
_matrix: np.ndarray | None = None  # shape (N, _EMBED_DIM), L2-normalised


def _get_genai_client():
    from google import genai
    from backend.core.config import settings
    if settings.google_genai_use_vertexai:
        return genai.Client(vertexai=True, project=settings.gcp_project_id, location=settings.gcp_region)
    return genai.Client(api_key=settings.google_api_key)


def _embed_texts(texts: list[str], task_type: str) -> np.ndarray:
    """Embed a batch of texts; returns L2-normalised float32 matrix (N, _EMBED_DIM)."""
    client = _get_genai_client()
    resp = client.models.embed_content(
        model=_EMBED_MODEL,
        contents=texts,
        config={"task_type": task_type},
    )
    vecs = np.array([e.values for e in resp.embeddings], dtype=np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return vecs / norms


def _embed_query(text: str) -> np.ndarray:
    """Embed a single query string; returns L2-normalised float32 vector."""
    client = _get_genai_client()
    resp = client.models.embed_content(
        model=_EMBED_MODEL,
        contents=[text],
        config={"task_type": "RETRIEVAL_QUERY"},
    )
    vec = np.array(resp.embeddings[0].values, dtype=np.float32)
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def _load_entries() -> list[dict[str, Any]]:
    if not _KNOWLEDGE_JSON.exists():
        logger.warning("chatbot_knowledge.json not found at %s", _KNOWLEDGE_JSON)
        return []
    with open(_KNOWLEDGE_JSON, encoding="utf-8") as f:
        return json.load(f)


def _build_matrix(entries: list[dict[str, Any]], embed_on_startup: bool) -> np.ndarray:
    if _VECTORS_NPY.exists():
        try:
            mat = np.load(str(_VECTORS_NPY))
            if mat.shape == (len(entries), _EMBED_DIM):
                logger.info("knowledge_base: loaded precomputed vectors from %s", _VECTORS_NPY)
                return mat.astype(np.float32)
            logger.warning("knowledge_base: .npy shape %s does not match %d entries — re-embedding", mat.shape, len(entries))
        except Exception as exc:
            logger.warning("knowledge_base: could not load .npy: %s", exc)

    if not embed_on_startup:
        logger.info("knowledge_base: chatbot_embed_on_startup=false, search will be disabled")
        return np.zeros((len(entries), _EMBED_DIM), dtype=np.float32)

    logger.info("knowledge_base: embedding %d entries via Gemini", len(entries))
    texts = [e["content"] for e in entries]
    mat = _embed_texts(texts, task_type="RETRIEVAL_DOCUMENT")
    try:
        np.save(str(_VECTORS_NPY), mat)
        logger.info("knowledge_base: saved vectors to %s", _VECTORS_NPY)
    except Exception as exc:
        logger.warning("knowledge_base: could not save vectors: %s", exc)
    return mat


def initialise(embed_on_startup: bool = True) -> None:
    """Called once at application startup. Idempotent."""
    global _entries, _matrix
    _entries = _load_entries()
    if not _entries:
        _matrix = np.zeros((0, _EMBED_DIM), dtype=np.float32)
        return
    _matrix = _build_matrix(_entries, embed_on_startup)
    logger.info("knowledge_base: ready — %d entries", len(_entries))


def search(query: str, top_k: int = 3, threshold: float = 0.82) -> list[dict[str, Any]]:
    """
    Return up to top_k entries with cosine similarity >= threshold, sorted descending.
    Returns empty list on any error.
    """
    if _matrix is None or _matrix.shape[0] == 0:
        return []
    try:
        q_vec = _embed_query(query)
    except Exception as exc:
        logger.warning("knowledge_base: query embedding failed: %s", exc)
        return []

    scores = (_matrix @ q_vec).tolist()
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    results = []
    for idx, score in ranked:
        if score < threshold or len(results) >= top_k:
            break
        results.append({**_entries[idx], "_score": round(float(score), 4)})
    return results


def get_entry_by_state_key(state_key: str | None) -> dict[str, Any] | None:
    """Retrieve the knowledge entry linked to a pipeline state key."""
    if state_key is None:
        return None
    for entry in _entries:
        if entry.get("related_state_key") == state_key:
            return entry
    return None
