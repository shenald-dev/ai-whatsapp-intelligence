import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import get_db
from app.api.auth import get_api_key
from app.ai.engine import ai_engine
from app.api.stream import event_bus

@pytest.fixture(autouse=True)
def cleanup():
    yield
    app.dependency_overrides.clear()

def test_ai_engine_extract_action_items():
    # 1. Actionable task with assignee
    content1 = "Please review PR #402 and finalize API docs by Friday, critical blocker"
    tasks1 = ai_engine.extract_action_items_sync(content1, sender_name="Alex Rivera")
    assert len(tasks1) == 1
    assert tasks1[0]["urgency"] == "high"
    assert "PR #402" in tasks1[0]["title"]
    assert tasks1[0]["due_date_str"] == "by Friday"

    # 2. Non-actionable conversation
    content2 = "Good morning everyone, nice weather today"
    tasks2 = ai_engine.extract_action_items_sync(content2, sender_name="Maria")
    assert len(tasks2) == 0

def test_ai_engine_detect_incident_alert():
    # 1. Outage emergency
    outage_msg = "CRITICAL ALERT: Production is down, 500 error spike across all endpoints!"
    alert1 = ai_engine.detect_incident_alert_sync(outage_msg, sender_name="Sarah")
    assert alert1 is not None
    assert alert1["severity"] == "critical"
    assert alert1["alert_type"] == "outage"
    assert "Sarah" in alert1["title"]

    # 2. Security leak
    leak_msg = "Warning: API key exposed in public logs repo!"
    alert2 = ai_engine.detect_incident_alert_sync(leak_msg, sender_name="David")
    assert alert2 is not None
    assert alert2["severity"] == "critical"
    assert alert2["alert_type"] == "security_leak"

    # 3. Normal informational chat
    normal_msg = "Lunch is ready in the kitchen guys"
    alert3 = ai_engine.detect_incident_alert_sync(normal_msg, sender_name="Alex")
    assert alert3 is None

def test_get_group_tasks_endpoint():
    client = TestClient(app)
    mock_db = AsyncMock()

    mock_task = MagicMock()
    mock_task.id = "t_1"
    mock_task.group_id = "grp_core"
    mock_task.source_message_id = "msg_1"
    mock_task.title = "Ship v2.0 release"
    mock_task.description = "Production readiness overhaul"
    mock_task.assignee = "Alex"
    mock_task.assignee_id = "u_alex"
    mock_task.urgency = "high"
    mock_task.status = "in_progress"
    mock_task.due_date = datetime(2026, 11, 5, 0, 0, tzinfo=timezone.utc)
    mock_task.created_at = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
    mock_task.completed_at = None

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [mock_task]
    mock_db.execute.return_value = mock_res

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_api_key] = lambda: "valid-key"

    response = client.get("/api/v1/dashboard/groups/grp_core/tasks?status=in_progress")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "t_1"
    assert data[0]["title"] == "Ship v2.0 release"
    assert data[0]["urgency"] == "high"
    assert data[0]["status"] == "in_progress"

def test_create_and_update_task_endpoint():
    client = TestClient(app)
    mock_db = AsyncMock()
    mock_db.add = MagicMock()

    created_task = MagicMock()
    created_task.id = "new_task_uuid"
    created_task.group_id = "grp_core"
    created_task.source_message_id = None
    created_task.title = "Refactor database connection pool"
    created_task.description = None
    created_task.assignee = "Sarah"
    created_task.assignee_id = None
    created_task.urgency = "high"
    created_task.status = "todo"
    created_task.created_at = datetime.now(timezone.utc)
    created_task.due_date = None
    created_task.completed_at = None

    mock_db.refresh = AsyncMock()

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_api_key] = lambda: "valid-key"

    with patch.object(event_bus, "publish", new_callable=AsyncMock) as mock_publish:
        # 1. Create task
        res_create = client.post(
            "/api/v1/dashboard/groups/grp_core/tasks",
            json={
                "group_id": "grp_core",
                "title": "Refactor database connection pool",
                "assignee": "Sarah",
                "urgency": "high",
                "status": "todo"
            }
        )
        assert res_create.status_code == 200
        assert mock_publish.called

        # 2. Update task status to done
        mock_res_select = MagicMock()
        mock_res_select.scalar_one_or_none.return_value = created_task
        mock_db.execute.return_value = mock_res_select

        res_update = client.patch(
            "/api/v1/dashboard/tasks/new_task_uuid",
            json={"status": "done"}
        )
        assert res_update.status_code == 200
        assert created_task.status == "done"
        assert created_task.completed_at is not None

def test_get_and_update_alert_endpoint():
    client = TestClient(app)
    mock_db = AsyncMock()
    mock_db.add = MagicMock()

    mock_alert = MagicMock()
    mock_alert.id = "alt_1"
    mock_alert.group_id = "grp_core"
    mock_alert.source_message_id = "msg_outage"
    mock_alert.severity = "critical"
    mock_alert.alert_type = "outage"
    mock_alert.title = "Service Outage Reported"
    mock_alert.description = "Production 500 error spike"
    mock_alert.status = "active"
    mock_alert.created_at = datetime.now(timezone.utc)
    mock_alert.resolved_at = None

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [mock_alert]
    mock_res.scalar_one_or_none.return_value = mock_alert
    mock_db.execute.return_value = mock_res
    mock_db.refresh = AsyncMock()

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_api_key] = lambda: "valid-key"

    # 1. Fetch alerts
    response = client.get("/api/v1/dashboard/groups/grp_core/alerts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["severity"] == "critical"
    assert data[0]["status"] == "active"

    # 2. Resolve alert
    patch_res = client.patch(
        "/api/v1/dashboard/alerts/alt_1",
        json={"status": "resolved"}
    )
    assert patch_res.status_code == 200
    assert mock_alert.status == "resolved"
    assert mock_alert.resolved_at is not None

@patch("app.main.celery_app.send_task")
def test_immediate_incident_alert_on_ingest(mock_send_task):
    client = TestClient(app)
    mock_db = AsyncMock()
    mock_db.add = MagicMock()

    mock_scalar = MagicMock()
    mock_scalar.scalar.return_value = "msg_outage_123"
    mock_db.execute.return_value = mock_scalar

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_api_key] = lambda: "valid-key"

    with patch.object(event_bus, "publish", new_callable=AsyncMock) as mock_publish:
        payload = {
            "message_id": "msg_outage_123",
            "group_id": "grp_dev",
            "group_name": "Dev Ops",
            "sender_id": "usr_ops",
            "sender_name": "DevOps Lead",
            "content": "CRITICAL: Production is down, database crash detected!",
            "timestamp": 1700000000,
            "is_media": False
        }
        res = client.post("/api/v1/ingest", json=payload)
        assert res.status_code == 200
        assert res.json()["status"] == "success"
        
        # Verify alert event was triggered
        published_event_names = [call[0][0] for call in mock_publish.call_args_list]
        assert "alert.triggered" in published_event_names
