import json
import logging
import os
from pathlib import Path

import chromadb
import litellm
from dotenv import load_dotenv

load_dotenv()
litellm.suppress_debug_info = True

log = logging.getLogger(__name__)

EMBEDDING_MODEL = "openrouter/openai/text-embedding-3-small"
COLLECTION_NAME = "ecombot_kb"
DATA_DIR = Path(__file__).parent.parent.parent / "data"


def embed(texts: list[str]) -> list[list[float]]:
    response = litellm.embedding(
        model=EMBEDDING_MODEL,
        input=texts,
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )
    return [item["embedding"] for item in response.data]


def load_documents() -> list[dict]:
    """Load and merge product + FAQ documents from the data directory."""
    documents = []

    # Load products
    products_file = DATA_DIR / "products.json"
    if products_file.exists():
        with open(products_file) as f:
            products = json.load(f)
            for doc in products:
                doc["doc_type"] = "product"
                documents.append(doc)
        log.info("Loaded %d product documents", len(products))

    # Load FAQ
    faq_file = DATA_DIR / "faq.json"
    if faq_file.exists():
        with open(faq_file) as f:
            faqs = json.load(f)
            for doc in faqs:
                doc["doc_type"] = "faq"
                documents.append(doc)
        log.info("Loaded %d FAQ documents", len(faqs))

    return documents


def build_collection(documents: list[dict] | None = None) -> chromadb.Collection:
    """
    Build or rebuild the ChromaDB collection from documents.
    Uses ephemeral (in-memory) ChromaDB for simplicity.
    """
    if documents is None:
        documents = load_documents()

    if not documents:
        raise ValueError("No documents found to embed. Check data/ directory.")

    client = chromadb.EphemeralClient()

    # Delete existing collection if present
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(name=COLLECTION_NAME)

    # Prepare data
    ids = [doc["id"] for doc in documents]
    texts = [doc["text"] for doc in documents]
    metadatas = [
        {
            "doc_type": doc.get("doc_type", "unknown"),
            "category": doc.get("category", ""),
            "section": doc.get("section", ""),
            "source": "ecombot_kb",
        }
        for doc in documents
    ]

    # Embed and upsert
    log.info("Embedding %d documents...", len(texts))
    embeddings = embed(texts)

    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    log.info("Knowledge base built: %d chunks in collection '%s'", collection.count(), COLLECTION_NAME)

    return collection


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    collection = build_collection()
    print(f"✓ Knowledge base rebuilt: {collection.count()} chunks indexed.")
