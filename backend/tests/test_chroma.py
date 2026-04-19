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
