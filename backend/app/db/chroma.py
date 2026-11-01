import os
import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class TimeoutHTTPAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        self.timeout = kwargs.pop("timeout", 15.0)
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        return super().send(request, **kwargs)

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))

BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
DEFAULT_CHROMA_DIR = os.path.join(BASE_DIR, ".chroma_data")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", DEFAULT_CHROMA_DIR)

# Global singleton client & collection
_chroma_client = None
_collection = None

def get_chroma_client():
    """Initializes and returns a ChromaDB client with automatic fallback."""
    global _chroma_client
    if _chroma_client is not None:
        return _chroma_client

    # 1. Attempt connection to HTTP ChromaDB server (Docker / remote)
    try:
        client = chromadb.HttpClient(
            host=CHROMA_HOST, 
            port=CHROMA_PORT,
            settings=Settings(anonymized_telemetry=False)
        )

        # Enforce explicit timeouts and retries on the underlying session
        if hasattr(client, "_admin_client") and hasattr(client._admin_client, "_server") and hasattr(client._admin_client._server, "_session"):
             session = client._admin_client._server._session
             retry_strategy = Retry(
                 total=3,
                 backoff_factor=0.3,
                 status_forcelist=[429, 500, 502, 503, 504],
                 allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
             )
             adapter = TimeoutHTTPAdapter(timeout=15.0, max_retries=retry_strategy)
             session.mount("http://", adapter)
             session.mount("https://", adapter)

        client.heartbeat()
        _chroma_client = client
        logger.info(f"Connected to remote ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}")
        return _chroma_client
    except Exception as http_err:
        logger.warning(
            f"Could not connect to remote ChromaDB ({http_err}). "
            f"Falling back to local persistent ChromaDB at '{CHROMA_PERSIST_DIR}'."
        )

    # 2. Fallback to local persistent ChromaDB client for zero-docker development & testing
    try:
        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIR,
            settings=Settings(anonymized_telemetry=False)
        )
        logger.info(f"Initialized local persistent ChromaDB at {CHROMA_PERSIST_DIR}")
        return _chroma_client
    except Exception as persist_err:
        logger.warning(
            f"Persistent ChromaDB failed ({persist_err}). "
            "Falling back to in-memory Ephemeral ChromaDB client."
        )

    # 3. Final fallback: in-memory ephemeral client
    _chroma_client = chromadb.EphemeralClient(settings=Settings(anonymized_telemetry=False))
    return _chroma_client

def get_collection():
    """Returns the WhatsApp messages vector collection."""
    global _collection
    if _collection is not None:
        return _collection

    client = get_chroma_client()
    try:
        _collection = client.get_or_create_collection(
            name="whatsapp_messages",
            metadata={"hnsw:space": "cosine"}
        )
        return _collection
    except Exception as e:
        logger.error(f"Failed to get/create ChromaDB collection: {e}")
        raise

def store_message_embedding(message_id: str, content: str, metadata: dict) -> None:
    """Store or update message text and metadata in the vector database."""
    if not content or not content.strip():
        return

    try:
        coll = get_collection()
        clean_metadata = {k: v for k, v in metadata.items() if v is not None}
        coll.upsert(
            documents=[content],
            metadatas=[clean_metadata],
            ids=[message_id]
        )
    except Exception as e:
        logger.error(f"ChromaDB Error while storing message {message_id}: {e}")
        raise

def search_message_embeddings(
    query_text: str,
    n_results: int = 10,
    where: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Performs semantic vector search across messages.
    Returns list of dicts with message_id, content, metadata, distance, and similarity score.
    """
    if not query_text or not query_text.strip():
        return []

    try:
        coll = get_collection()
        count = coll.count()
        if count == 0:
            return []

        limit = min(n_results, count)
        kwargs: Dict[str, Any] = {
            "query_texts": [query_text],
            "n_results": limit
        }
        if where:
            clean_where = {k: v for k, v in where.items() if v is not None}
            if clean_where:
                kwargs["where"] = clean_where

        results = coll.query(**kwargs)

        items = []
        if results and results.get("ids") and results["ids"][0]:
            ids = results["ids"][0]
            docs = results["documents"][0] if results.get("documents") else [""] * len(ids)
            metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(ids)
            dists = results["distances"][0] if results.get("distances") else [0.0] * len(ids)

            for msg_id, doc, meta, dist in zip(ids, docs, metas, dists):
                sim = max(0.0, min(1.0, 1.0 - float(dist)))
                items.append({
                    "message_id": msg_id,
                    "content": doc,
                    "metadata": meta,
                    "distance": float(dist),
                    "similarity": round(sim, 4)
                })

        return items
    except Exception as e:
        logger.error(f"Semantic search error in ChromaDB: {e}")
        return []

def get_collection_stats() -> Dict[str, Any]:
    """Returns vector collection statistics."""
    try:
        coll = get_collection()
        return {
            "collection_name": coll.name,
            "total_embeddings": coll.count(),
            "status": "online"
        }
    except Exception as e:
        return {
            "collection_name": "whatsapp_messages",
            "total_embeddings": 0,
            "status": f"offline ({e})"
        }
