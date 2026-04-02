import os
import logging
import chromadb
import logging

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

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

        coll.add(
            documents=[content],
            metadatas=[clean_metadata],
            ids=[message_id]
        )
    except Exception as e:
        logger.error(f"ChromaDB Error: {e}")
