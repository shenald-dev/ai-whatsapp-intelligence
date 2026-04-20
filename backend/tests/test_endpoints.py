import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import get_db

@pytest.fixture(autouse=True)
def cleanup():
    # Clear dependency overrides after each test
    yield
    app.dependency_overrides.clear()

def test_get_groups():
    client = TestClient(app)

    mock_db = AsyncMock()
    mock_result = MagicMock()

    # Mock groups
    mock_group_1 = MagicMock()
    mock_group_1.id = "group_1"
    mock_group_1.name = "Test Group 1"

    mock_group_2 = MagicMock()
    mock_group_2.id = "group_2"
    mock_group_2.name = "Test Group 2"

    mock_result.scalars.return_value.all.return_value = [mock_group_1, mock_group_2]
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/api/v1/dashboard/groups")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0] == {"id": "group_1", "name": "Test Group 1"}
    assert data[1] == {"id": "group_2", "name": "Test Group 2"}
    assert mock_db.execute.call_count == 1

def test_get_group_stats():
    client = TestClient(app)

    mock_db = AsyncMock()
    mock_result = MagicMock()

    # Mock row
    mock_row = MagicMock()
    mock_row.total = 100
    mock_row.analyzed = 80
    mock_row.positive = 30
    mock_row.negative = 10
    mock_row.neutral = 40
    mock_row.tasks = 5
    mock_row.decisions = 2

    mock_result.first.return_value = mock_row
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/api/v1/dashboard/groups/group_1/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["group_id"] == "group_1"
    assert data["total_messages"] == 100
    assert data["ai_analyzed"] == 80
    assert data["sentiment_distribution"]["positive"] == 30
    assert data["sentiment_distribution"]["negative"] == 10
    assert data["sentiment_distribution"]["neutral"] == 40
    assert data["tasks_detected"] == 5
    assert data["decisions_detected"] == 2
    assert mock_db.execute.call_count == 1

def test_get_group_stats_empty():
    client = TestClient(app)

    mock_db = AsyncMock()
    mock_result = MagicMock()

    # Mock empty row
    mock_result.first.return_value = None
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/api/v1/dashboard/groups/group_1/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_messages"] == 0
    assert data["ai_analyzed"] == 0
    assert data["tasks_detected"] == 0
    assert data["decisions_detected"] == 0
    assert mock_db.execute.call_count == 1

def test_get_recent_messages():
    client = TestClient(app)

    mock_db = AsyncMock()
    mock_result = MagicMock()

    # Mock message
    mock_msg = MagicMock()
    mock_msg.id = "msg_1"
    mock_msg.content = "Test content"
    mock_msg.sentiment = "positive"
    mock_msg.classification = "task"

    mock_result.scalars.return_value.all.return_value = [mock_msg]
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/api/v1/dashboard/groups/group_1/messages?limit=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "msg_1"
    assert data[0]["content"] == "Test content"
    assert data[0]["sentiment"] == "positive"
    assert data[0]["classification"] == "task"
    assert mock_db.execute.call_count == 1
