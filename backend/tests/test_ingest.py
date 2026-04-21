import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app, entity_cache, SimpleLRUCache, get_api_key
from app.db.database import get_db

@pytest.fixture(autouse=True)
def cleanup():
    # Clear dependency overrides after each test
    yield
    app.dependency_overrides.clear()
    entity_cache.cache.clear()

def test_lru_cache():
    cache = SimpleLRUCache(2)
    assert cache.get("1") is False
    cache.put("1")
    assert cache.get("1") is True
    cache.put("2")
    cache.put("3") # Should evict "1"
    assert cache.get("1") is False
    assert cache.get("2") is True
    assert cache.get("3") is True


@patch("app.main.celery_app.send_task")
def test_ingest_message_caching(mock_send_task):
    client = TestClient(app)

    mock_db = AsyncMock()
    mock_db.add = MagicMock()

    # Override dependencies
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_api_key] = lambda: "valid-key"

    payload = {
        "message_id": "msg1",
        "group_id": "grp1",
        "group_name": "Group 1",
        "sender_id": "usr1",
        "sender_name": "User 1",
        "content": "Hello",
        "timestamp": 1700000000,
        "is_media": False
    }

    # Mock execute result for message UPSERT
    mock_execute_result = MagicMock()
    mock_execute_result.scalar.return_value = "msg1"
    mock_db.execute.return_value = mock_execute_result

    # First request
    response = client.post("/api/v1/ingest", json=payload)
    assert response.status_code == 200

    # Assert DB methods were called
    assert mock_db.execute.call_count == 3 # group upsert, user upsert, message upsert
    assert mock_db.add.call_count == 0  # no longer using add
    assert mock_db.commit.call_count == 1
    mock_send_task.assert_called_once_with("enrich_message", args=["msg1"])

    # Check cache is updated
    assert entity_cache.get("group_grp1") is True
    assert entity_cache.get("user_usr1") is True

    # Reset mocks
    mock_db.reset_mock()
    mock_send_task.reset_mock()

    # Second request (simulate existing message for idempotency check via UPSERT)
    mock_execute_result.scalar.return_value = None
    mock_db.execute.return_value = mock_execute_result

    response = client.post("/api/v1/ingest", json=payload)
    assert response.status_code == 200
    assert response.json().get("detail") == "Already ingested"

    # Assert DB execute was called for UPSERT but celery wasn't called
    # NOTE: Since the first request already inserted group and user into the cache,
    # entity_cache.get() will return True for them on the second request.
    # Therefore, ONLY the message UPSERT will be executed! Thus call_count == 1.
    assert mock_db.execute.call_count == 1
    assert mock_db.commit.call_count == 1
    mock_send_task.assert_not_called()

@patch("app.main.celery_app.send_task")
def test_ingest_message_concurrent_insert(mock_send_task):
    client = TestClient(app)

    mock_db = AsyncMock()

    # Override dependencies
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_api_key] = lambda: "valid-key"

    payload = {
        "message_id": "msg2",
        "group_id": "grp2",
        "group_name": "Group 2",
        "sender_id": "usr2",
        "sender_name": "User 2",
        "content": "Concurrent Hello",
        "timestamp": 1700000000,
        "is_media": False
    }

    # Mock execute result for message UPSERT
    mock_execute_result = MagicMock()
    # Return None for UPSERT simulating a concurrent insert winning the race
    mock_execute_result.scalar.return_value = None
    mock_db.execute.return_value = mock_execute_result

    response = client.post("/api/v1/ingest", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message_id": "msg2", "detail": "Already ingested"}

    # DB commits and cache gets updated even when UPSERT returns None
    assert mock_db.commit.call_count == 1
    assert entity_cache.get("group_grp2") is True
    assert entity_cache.get("user_usr2") is True
    mock_send_task.assert_not_called()
