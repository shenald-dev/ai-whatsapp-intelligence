import pytest
from unittest.mock import patch, MagicMock
import app.db.chroma as chroma

@pytest.fixture(autouse=True)
def reset_chroma():
    chroma._chroma_client = None
    chroma._collection = None
    yield
    chroma._chroma_client = None
    chroma._collection = None

@patch('app.db.chroma.chromadb.HttpClient')
def test_store_message_embedding_uses_upsert(mock_client):
    mock_coll = MagicMock()
    mock_client.return_value.get_or_create_collection.return_value = mock_coll

    chroma.store_message_embedding("msg-1", "Hello World", {"user": "Alice", "invalid": None})

    # Assert upsert was called instead of add
    mock_coll.upsert.assert_called_once_with(
        documents=["Hello World"],
        metadatas=[{"user": "Alice"}],
        ids=["msg-1"]
    )
    mock_coll.add.assert_not_called()

@patch('app.db.chroma.chromadb.HttpClient')
def test_search_message_embeddings(mock_client):
    mock_coll = MagicMock()
    mock_coll.count.return_value = 5
    mock_coll.query.return_value = {
        "ids": [["msg-1", "msg-2"]],
        "documents": [["Test doc 1", "Test doc 2"]],
        "metadatas": [[{"group_id": "grp1"}, {"group_id": "grp1"}]],
        "distances": [[0.1, 0.4]]
    }
    mock_client.return_value.get_or_create_collection.return_value = mock_coll

    results = chroma.search_message_embeddings("query text", n_results=2, where={"group_id": "grp1"})
    assert len(results) == 2
    assert results[0]["message_id"] == "msg-1"
    assert results[0]["similarity"] == 0.9 # 1.0 - 0.1
    assert results[1]["message_id"] == "msg-2"
    assert results[1]["similarity"] == 0.6 # 1.0 - 0.4

@patch('app.db.chroma.chromadb.HttpClient')
def test_search_empty_query(mock_client):
    assert chroma.search_message_embeddings("") == []
    assert chroma.search_message_embeddings("   ") == []

@patch('app.db.chroma.chromadb.HttpClient')
def test_get_collection_stats(mock_client):
    mock_coll = MagicMock()
    mock_coll.name = "whatsapp_messages"
    mock_coll.count.return_value = 42
    mock_client.return_value.get_or_create_collection.return_value = mock_coll

    stats = chroma.get_collection_stats()
    assert stats["total_embeddings"] == 42
    assert stats["status"] == "online"
