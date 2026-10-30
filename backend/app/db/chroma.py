import os
import logging
import chromadb
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import chromadb.api.fastapi

logger = logging.getLogger(__name__)

# Enforce external client timeouts and retries to prevent worker starvation
class TimeoutHTTPAdapter(HTTPAdapter):
    def __init__(self, timeout=None, max_retries=0, *args, **kwargs):
        self.timeout = timeout
        if max_retries:
            retry_strategy = Retry(
                total=max_retries,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
            )
            kwargs["max_retries"] = retry_strategy
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)

_original_fastapi_init = chromadb.api.fastapi.FastAPI.__init__

def _patched_fastapi_init(self, system):
    _original_fastapi_init(self, system)
    timeout_adapter = TimeoutHTTPAdapter(timeout=5.0, max_retries=3)
    self._session.mount("http://", timeout_adapter)
    self._session.mount("https://", timeout_adapter)

chromadb.api.fastapi.FastAPI.__init__ = _patched_fastapi_init


CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))

# Lazy initialization for the ChromaDB client to avoid crash at import
_chroma_client = None
_collection = None

def get_collection():
    global _chroma_client, _collection
    if _collection is None:
        try:
            # Connect to the ChromaDB Docker container
            _chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

            # Create or get the collection for message embeddings
            _collection = _chroma_client.get_or_create_collection(
                name="whatsapp_messages",
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            logger.error(f"ChromaDB Initialization Error: {e}")
            raise
    return _collection

def store_message_embedding(message_id: str, content: str, metadata: dict):
    """Store the message text and metadata in the vector database."""
    try:
        coll = get_collection()

        # ChromaDB metadata values must be str, int, float or bool.
        # Remove any keys where the value is None to prevent insertion errors.
        clean_metadata = {k: v for k, v in metadata.items() if v is not None}

        coll.upsert(
            documents=[content],
            metadatas=[clean_metadata],
            ids=[message_id]
        )
    except Exception as e:
        logger.error(f"ChromaDB Error: {e}")
        raise
