import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import get_db
from app.api.auth import get_api_key
from app.api.endpoints import stats_cache

@pytest.fixture(autouse=True)
def cleanup():
    yield
    app.dependency_overrides.clear()
    stats_cache.clear()

def test_get_group_stats():
    client = TestClient(app)
    mock_db = AsyncMock()

    # Create a mock row object to simulate db.execute(...).first()
    mock_row = MagicMock()
    mock_row.total = 10
    mock_row.analyzed = 8
    mock_row.positive = 5
    mock_row.negative = 2
    mock_row.neutral = 1
    mock_row.tasks = 3
    mock_row.decisions = 1

    mock_execute_result = MagicMock()
    mock_execute_result.first.return_value = mock_row
    mock_db.execute.return_value = mock_execute_result

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_api_key] = lambda: "valid-key"

    response = client.get("/api/v1/dashboard/groups/grp1/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["group_id"] == "grp1"
    assert data["total_messages"] == 10
    assert data["ai_analyzed"] == 8
    assert data["sentiment_distribution"]["positive"] == 5
    assert data["sentiment_distribution"]["negative"] == 2
    assert data["sentiment_distribution"]["neutral"] == 1
    assert data["tasks_detected"] == 3
    assert data["decisions_detected"] == 1

def test_get_group_stats_empty():
    client = TestClient(app)
    mock_db = AsyncMock()

    # Simulate empty group returning a row of zeros natively handled by the DB count filter,
    # but SQLAlchemy will still return a row with counts=0 or None
    mock_row = MagicMock()
    mock_row.total = 0
    mock_row.analyzed = 0
    mock_row.positive = 0
    mock_row.negative = 0
    mock_row.neutral = 0
    mock_row.tasks = 0
    mock_row.decisions = 0

    mock_execute_result = MagicMock()
    mock_execute_result.first.return_value = mock_row
    mock_db.execute.return_value = mock_execute_result

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_api_key] = lambda: "valid-key"

    response = client.get("/api/v1/dashboard/groups/grp2/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_messages"] == 0
    assert data["ai_analyzed"] == 0
    assert data["tasks_detected"] == 0

def test_get_group_stats_caching():
    client = TestClient(app)
    mock_db = AsyncMock()

    # Create a mock row object
    mock_row = MagicMock()
    mock_row.total = 5
    mock_row.analyzed = 5
    mock_row.positive = 5
    mock_row.negative = 0
    mock_row.neutral = 0
    mock_row.tasks = 1
    mock_row.decisions = 0

    mock_execute_result = MagicMock()
    mock_execute_result.first.return_value = mock_row
    mock_db.execute.return_value = mock_execute_result

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_api_key] = lambda: "valid-key"

    # First call should hit the database
    response1 = client.get("/api/v1/dashboard/groups/grp_cache/stats")
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["total_messages"] == 5

    # Check that execute was called
    assert mock_db.execute.call_count == 1

    # Second call should return cached response and not hit the database
    response2 = client.get("/api/v1/dashboard/groups/grp_cache/stats")
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["total_messages"] == 5

    # Check that execute call count is still 1
    assert mock_db.execute.call_count == 1

def test_get_recent_messages_pagination():
    client = TestClient(app)
    mock_db = AsyncMock()

    mock_execute_result = MagicMock()

    mock_row = MagicMock()
    mock_row.id = "msg1"
    mock_row.content = "Hello"
    mock_row.sentiment = "neutral"
    mock_row.classification = "discussion"

    mock_execute_result.all.return_value = [mock_row]
    mock_db.execute.return_value = mock_execute_result

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_api_key] = lambda: "valid-key"

    response = client.get("/api/v1/dashboard/groups/grp1/messages?limit=10&offset=20")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "msg1"

def test_get_recent_messages_limit_validation():
    client = TestClient(app)
    app.dependency_overrides[get_api_key] = lambda: "valid-key"

    # limit > 100 should be rejected by validation
    response = client.get("/api/v1/dashboard/groups/grp1/messages?limit=200")
    assert response.status_code == 422

def test_get_groups_pagination():
    client = TestClient(app)
    mock_db = AsyncMock()

    mock_execute_result = MagicMock()

    mock_row1 = MagicMock()
    mock_row1.id = "grp1"
    mock_row1.name = "Group 1"

    mock_row2 = MagicMock()
    mock_row2.id = "grp2"
    mock_row2.name = "Group 2"

    mock_execute_result.all.return_value = [mock_row1, mock_row2]
    mock_db.execute.return_value = mock_execute_result

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_api_key] = lambda: "valid-key"

    response = client.get("/api/v1/dashboard/groups?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == "grp1"

def test_get_groups_limit_validation():
    client = TestClient(app)
    app.dependency_overrides[get_api_key] = lambda: "valid-key"

    # limit > 100 should be rejected by validation
    response = client.get("/api/v1/dashboard/groups?limit=150")
    assert response.status_code == 422

def test_cache_ttl_uses_monotonic_time():
    import time
    from app.api.endpoints import BoundedTTLCache

    # Create cache with 0.1s TTL
    cache = BoundedTTLCache(capacity=10, ttl=0.1)

    # Put item
    cache.put("key1", "value1")
    assert cache.get("key1") == "value1"

    # Sleep past TTL
    time.sleep(0.15)

    # Item should be expired based on monotonic time
    assert cache.get("key1") is None
