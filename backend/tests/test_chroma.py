from unittest.mock import MagicMock, patch
import pytest

from app.db.chroma import store_message_embedding

@patch("app.db.chroma.get_collection")
def test_store_message_embedding_idempotent_upsert(mock_get_collection):
    """
    Test that store_message_embedding uses upsert for idempotency
    to prevent duplicate ID exceptions during Celery retries.
    """
    mock_coll = MagicMock()
    mock_get_collection.return_value = mock_coll

    # Store message with no null values
    store_message_embedding(
        message_id="msg-123",
        content="Hello world",
        metadata={"group_id": "grp-1", "sentiment": "positive", "classification": None}
    )

    # Ensure upsert is called instead of add
    mock_coll.upsert.assert_called_once_with(
        documents=["Hello world"],
        metadatas=[{"group_id": "grp-1", "sentiment": "positive"}],
        ids=["msg-123"]
    )

    # Ensure add was not called
    mock_coll.add.assert_not_called()
