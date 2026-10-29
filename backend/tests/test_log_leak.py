import logging
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import get_db
from app.api.auth import get_api_key

def test_ingest_message_500_error_hides_secret_in_logs(caplog):
    client = TestClient(app)
    mock_db = AsyncMock()
    # Simulate a database exception that contains a secret
    mock_db.execute.side_effect = Exception("Connection refused: postgresql://user:MY_SUPER_SECRET_PASSWORD@localhost:5432/db")

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

    with caplog.at_level(logging.ERROR):
        response = client.post("/api/v1/ingest", json=payload)

    assert response.status_code == 500

    # The secret should NOT be in the logs
    assert "MY_SUPER_SECRET_PASSWORD" not in caplog.text
    # But the URL format should be masked
    assert "postgresql://user:***@localhost:5432/db" in caplog.text
