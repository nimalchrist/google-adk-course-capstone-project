"""
retriever.py — Semantic search over eComBot's ChromaDB knowledge base
----------------------------------------------------------------------
Day 05-06: Retrieves the most relevant chunks for a user query.

Public API:
    semantic_search(query, top_k=3) → list[dict]

Each result dict contains: {"id", "text", "score", "metadata"}
"""

import logging
import os

import chromadb
import litellm
from dotenv import load_dotenv

load_dotenv()
litellm.suppress_debug_info = True

log = logging.getLogger(__name__)

EMBEDDING_MODEL = "openrouter/openai/text-embedding-3-small"
COLLECTION_NAME = "ecombot_kb"

# Singleton collection reference
_collection: chromadb.Collection | None = None


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts via OpenRouter's embedding endpoint."""
    response = litellm.embedding(
        model=EMBEDDING_MODEL,
        input=texts,
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )
    return [item["embedding"] for item in response.data]


def _get_collection() -> chromadb.Collection:
    """Return the lazily-built in-memory ChromaDB collection."""
    global _collection
    if _collection is None:
        try:
            from src.rag.embed_catalog import build_collection
            _collection = build_collection()
        except Exception as exc:
            log.warning("Failed to build knowledge base: %s", exc)
            # Return an empty collection as fallback
            client = chromadb.EphemeralClient()
            _collection = client.get_or_create_collection(name=COLLECTION_NAME)
    return _collection


def semantic_search(query: str, top_k: int = 3) -> list[dict]:
    """
    Return the top_k documents closest to the query by vector distance.

    Each result is a dict: {"id", "text", "score", "metadata"}
    where score is similarity in [0, 1] (higher = closer match).
    Returns an empty list for an empty query or if KB is unavailable.
    """
    if not query or not query.strip():
        return []

    try:
        collection = _get_collection()

        if collection.count() == 0:
            log.debug("Knowledge base is empty — no results.")
            return []

        query_embedding = embed([query.strip()])

        result = collection.query(
            query_embeddings=query_embedding,
            n_results=min(top_k, collection.count()),
        )

        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]

        return [
            {
                "id": doc_id,
                "text": text,
                "score": 1.0 / (1.0 + distance),
                "metadata": metadata,
            }
            for doc_id, text, distance, metadata in zip(ids, documents, distances, metadatas)
        ]

    except Exception as exc:
        log.warning("Semantic search failed: %s", exc)
        return []
