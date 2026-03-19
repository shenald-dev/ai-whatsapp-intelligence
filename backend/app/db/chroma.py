import os
import chromadb

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))

# Connect to the ChromaDB Docker container
chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

# Create or get the collection for message embeddings
collection = chroma_client.get_or_create_collection(
    name="whatsapp_messages",
    metadata={"hnsw:space": "cosine"}
)

def search_similar_messages(query: str, n_results: int = 5):
    """Semantic search query over the chat history."""
    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results
    except Exception as e:
        print(f"ChromaDB Query Error: {e}")
        return {"documents": [], "metadatas": []}
