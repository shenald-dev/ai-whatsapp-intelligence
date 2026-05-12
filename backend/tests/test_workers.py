import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.workers.tasks import process_message
from app.db.models import Message, Base

engine = create_engine("sqlite:///:memory:")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

@patch("app.workers.tasks.SessionLocal")
@patch("app.workers.tasks.ai_engine.analyze_message_sync")
@patch("app.workers.tasks.store_message_embedding")
def test_process_message_direct_update(mock_store_embedding, mock_analyze, mock_session_local):
    # Setup test DB
    session = SessionLocal()
    mock_session_local.return_value = session

    msg_id = "test-msg-1"
    msg = Message(id=msg_id, content="test content", group_id="g1", sender_id="s1")
    session.add(msg)
    session.commit()

    mock_analyze.return_value = {"sentiment": "positive", "classification": "task"}

    # Process
    result = process_message(msg_id)

    assert result == {"status": "success", "message_id": msg_id}

    # Verify DB state
    updated_msg = session.get(Message, msg_id)
    assert updated_msg.sentiment == "positive"
    assert updated_msg.classification == "task"
    assert updated_msg.is_analyzed is True

@patch("app.workers.tasks.SessionLocal")
@patch("app.workers.tasks.ai_engine.analyze_message_sync")
@patch("app.workers.tasks.store_message_embedding")
def test_process_message_direct_update_rollback_on_error(mock_store_embedding, mock_analyze, mock_session_local):
    # Setup test DB
    session = SessionLocal()
    mock_session_local.return_value = session

    msg_id = "test-msg-2"
    msg = Message(id=msg_id, content="test content", group_id="g1", sender_id="s1")
    session.add(msg)
    session.commit()

    mock_analyze.return_value = {"sentiment": "positive", "classification": "task"}
    mock_store_embedding.side_effect = Exception("ChromaDB failed")

    # Process
    with pytest.raises(Exception):
        process_message(msg_id)

    # Verify DB state reverted
    updated_msg = session.get(Message, msg_id)
    assert updated_msg.sentiment is None
    assert updated_msg.classification is None
    assert updated_msg.is_analyzed is False
