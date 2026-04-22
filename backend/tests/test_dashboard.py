import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import get_db
from app.api.auth import get_api_key

@pytest.fixture(autouse=True)
def cleanup():
    yield
    app.dependency_overrides.clear()

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
