import os
import pytest
from unittest.mock import MagicMock

# Mock the environment variable BEFORE importing tasks
# Note SQLite doesn't support max_overflow, so we must patch create_engine
import sqlalchemy
original_create_engine = sqlalchemy.create_engine
def mock_create_engine(*args, **kwargs):
    kwargs.pop('max_overflow', None)
    kwargs.pop('pool_size', None)
    kwargs.pop('pool_pre_ping', None)
    return original_create_engine(*args, **kwargs)

sqlalchemy.create_engine = mock_create_engine

os.environ["SYNC_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

from app.workers.tasks import process_message, engine, SessionLocal
import app.db.models as models

@pytest.fixture
def db_session():
    models.Base.metadata.create_all(engine)
    session = SessionLocal()

    group = models.Group(id="test_group_1", name="Test Group")
    user = models.User(id="test_user_1", name="Test User")

    session.add(group)
    session.add(user)
    session.commit()

    msg = models.Message(
        id="test_msg_1",
        group_id="test_group_1",
        sender_id="test_user_1",
        content="Hello world",
        is_analyzed=False
    )
    session.add(msg)
    session.commit()

    yield session

    session.query(models.Message).delete()
    session.query(models.User).delete()
    session.query(models.Group).delete()
    session.commit()
    session.close()

def test_process_message_update_orm_sync(db_session, monkeypatch):
    class MockAIEngine:
        def analyze_message_sync(self, content):
            return {"sentiment": "positive", "classification": "discussion"}

    monkeypatch.setattr("app.workers.tasks.ai_engine", MockAIEngine())

    def mock_store(*args, **kwargs):
        pass

    monkeypatch.setattr("app.workers.tasks.store_message_embedding", mock_store)

    # Load the message into the session first to ensure it's in the identity map
    msg_before = db_session.get(models.Message, "test_msg_1")
    assert msg_before.is_analyzed is False

    res = process_message("test_msg_1")
    assert res["status"] == "success"

    # Refresh the object from the DB because the task used a different session
    db_session.refresh(msg_before)

    assert msg_before.is_analyzed is True
    assert msg_before.sentiment == "positive"
    assert msg_before.classification == "discussion"
