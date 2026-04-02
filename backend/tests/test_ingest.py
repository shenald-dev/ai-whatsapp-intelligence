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
    assert not cache.get("1")
    cache.put("1")
    assert cache.get("1")
    cache.put("2")
    cache.put("3") # Should evict "1"
    assert not cache.get("1")
    assert cache.get("2")
    assert cache.get("3")


@patch("app.main.celery_app.send_task")
def test_ingest_message_caching(mock_send_task):
    client = TestClient(app)

    mock_db = AsyncMock()
    # Mock db.get to return None (so it adds to db)
    mock_db.get.return_value = None
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

    # First request
    response = client.post("/api/v1/ingest", json=payload)
    assert response.status_code == 200

    # Assert DB methods were called
    assert mock_db.get.call_count == 3 # msg idempotency check, group, user
    assert mock_db.add.call_count == 3  # group, user, msg
    assert mock_db.commit.call_count == 1

    # Check cache is updated
    assert entity_cache.get("group_grp1")
    assert entity_cache.get("user_usr1")

    # Reset mocks
    mock_db.reset_mock()

    # Second request (simulate existing message for idempotency check)
    mock_db.get.return_value = MagicMock() # Mock returning an existing message
    response = client.post("/api/v1/ingest", json=payload)
    assert response.status_code == 200
    assert response.json().get("detail") == "Already ingested"

    # Assert DB get and add were NOT called further
    assert mock_db.get.call_count == 1 # Only the idempotency check
    assert mock_db.add.call_count == 0
    assert mock_db.commit.call_count == 0
