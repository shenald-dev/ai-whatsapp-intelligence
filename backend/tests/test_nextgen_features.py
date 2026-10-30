import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import get_db
from app.api.auth import get_api_key
from app.api.endpoints import stats_cache, briefing_cache
from app.api.stream import EventBus

@pytest.fixture(autouse=True)
def cleanup():
    yield
    app.dependency_overrides.clear()
    stats_cache.clear()
    briefing_cache.clear()

def test_health_check_endpoint():
    client = TestClient(app)
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch('app.main.get_collection_stats', return_value={"status": "online", "total_embeddings": 10}):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert data["chromadb"]["status"] == "online"

def test_dashboard_ui_html_endpoint():
    client = TestClient(app)
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "AI WhatsApp Intelligence" in response.text
    assert "<!DOCTYPE html>" in response.text

@patch('app.api.endpoints.search_message_embeddings')
def test_semantic_search_with_vector_hits(mock_vector_search):
    client = TestClient(app)
    mock_db = AsyncMock()

    mock_vector_search.return_value = [
        {
            "message_id": "msg_1",
            "content": "We decided to ship feature X",
            "similarity": 0.88,
            "metadata": {"group_id": "g1", "sender_id": "u1"}
        }
    ]

    mock_msg = MagicMock()
    mock_msg.id = "msg_1"
    mock_msg.content = "We decided to ship feature X"
    mock_msg.group_id = "g1"
    mock_msg.sender_id = "u1"
    mock_msg.timestamp = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)
    mock_msg.sentiment = "positive"
    mock_msg.classification = "decision"

    mock_row = MagicMock()
    mock_row.Message = mock_msg
    mock_row.group_name = "Core Team"
    mock_row.user_name = "Alex"

    mock_exec = MagicMock()
    mock_exec.all.return_value = [mock_row]
    mock_db.execute.return_value = mock_exec

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_api_key] = lambda: "valid-key"

    response = client.post("/api/v1/dashboard/search", json={"query": "feature X shipment", "limit": 5})
    assert response.status_code == 200
    data = response.json()
    assert data["total_found"] == 1
    assert data["results"][0]["message_id"] == "msg_1"
    assert data["results"][0]["group_name"] == "Core Team"
    assert data["results"][0]["sender_name"] == "Alex"
    assert data["results"][0]["similarity"] == 0.88

@patch('app.api.endpoints.search_message_embeddings', return_value=[])
def test_semantic_search_fallback_to_db(mock_vector_search):
    client = TestClient(app)
    mock_db = AsyncMock()

    mock_msg = MagicMock()
    mock_msg.id = "fallback_msg"
    mock_msg.content = "Keyword match for deployment"
    mock_msg.group_id = "g2"
    mock_msg.sender_id = "u2"
    mock_msg.timestamp = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)
    mock_msg.sentiment = "neutral"
    mock_msg.classification = "announcement"

    mock_row = MagicMock()
    mock_row.Message = mock_msg
    mock_row.group_name = "DevOps"
    mock_row.user_name = "Sarah"

    mock_exec = MagicMock()
    mock_exec.all.return_value = [mock_row]
    mock_db.execute.return_value = mock_exec

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_api_key] = lambda: "valid-key"

    response = client.post("/api/v1/dashboard/search", json={"query": "deployment", "limit": 5})
    assert response.status_code == 200
    data = response.json()
    assert data["total_found"] == 1
    assert data["results"][0]["message_id"] == "fallback_msg"
    assert data["results"][0]["sender_name"] == "Sarah"

@patch('app.api.endpoints.search_message_embeddings')
def test_ask_ai_conversational_rag(mock_vector_search):
    client = TestClient(app)
    mock_db = AsyncMock()

    mock_vector_search.return_value = [
        {
            "message_id": "msg_target",
            "content": "Alex confirmed the migration runs at 3 AM",
            "similarity": 0.92,
            "metadata": {"group_id": "g1"}
        }
    ]

    mock_msg = MagicMock()
    mock_msg.id = "msg_target"
    mock_msg.content = "Alex confirmed the migration runs at 3 AM"
    mock_msg.timestamp = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)

    mock_row = MagicMock()
    mock_row.Message = mock_msg
    mock_row.user_name = "Alex"

    mock_exec = MagicMock()
    mock_exec.all.return_value = [mock_row]
    mock_db.execute.return_value = mock_exec

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_api_key] = lambda: "valid-key"

    response = client.post("/api/v1/dashboard/ask", json={"question": "When is the migration happening?", "group_id": "g1"})
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert len(data["citations"]) >= 1
    assert data["citations"][0]["message_id"] == "msg_target"
    assert data["citations"][0]["sender_name"] == "Alex"

def test_executive_briefing_generation():
    client = TestClient(app)
    mock_db = AsyncMock()

    # 1. Mock Group
    mock_group = MagicMock()
    mock_group.id = "g_eng"
    mock_group.name = "Engineering Lead Sync"

    # 2. Mock Messages
    mock_msg1 = MagicMock()
    mock_msg1.id = "m1"
    mock_msg1.content = "We decided to adopt PostgreSQL 16"
    mock_msg1.sentiment = "positive"
    mock_msg1.classification = "decision"
    mock_msg1.timestamp = datetime.now(timezone.utc)

    mock_msg2 = MagicMock()
    mock_msg2.id = "m2"
    mock_msg2.content = "Need to update docker images ASAP"
    mock_msg2.sentiment = "neutral"
    mock_msg2.classification = "task"
    mock_msg2.timestamp = datetime.now(timezone.utc)

    row1 = MagicMock()
    row1.Message = mock_msg1
    row1.user_name = "Alex"

    row2 = MagicMock()
    row2.Message = mock_msg2
    row2.user_name = "Sarah"

    mock_group_exec = MagicMock()
    mock_group_exec.scalar_one_or_none.return_value = mock_group

    mock_msg_exec = MagicMock()
    mock_msg_exec.all.return_value = [row1, row2]

    mock_db.execute.side_effect = [mock_group_exec, mock_msg_exec]

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_api_key] = lambda: "valid-key"

    response = client.get("/api/v1/dashboard/groups/g_eng/briefing?hours=48")
    assert response.status_code == 200
    data = response.json()
    assert data["group_name"] == "Engineering Lead Sync"
    assert data["total_messages_analyzed"] == 2
    assert len(data["key_decisions"]) >= 1
    assert len(data["action_items"]) >= 1
    assert "executive_summary" in data

def test_export_intelligence_markdown_and_csv():
    client = TestClient(app)
    mock_db = AsyncMock()

    mock_group = MagicMock()
    mock_group.id = "g_export"
    mock_group.name = "Strategy Room"

    mock_msg = MagicMock()
    mock_msg.id = "m_exp"
    mock_msg.content = "Action item: Deploy security patch"
    mock_msg.sentiment = "positive"
    mock_msg.classification = "task"
    mock_msg.timestamp = datetime.now(timezone.utc)

    row = MagicMock()
    row.Message = mock_msg
    row.user_name = "Elena"

    mock_group_exec = MagicMock()
    mock_group_exec.scalar_one_or_none.return_value = mock_group

    mock_msg_exec = MagicMock()
    mock_msg_exec.all.return_value = [row]

    mock_db.execute.side_effect = [
        mock_group_exec, mock_msg_exec, # First call (markdown)
        mock_group_exec, mock_msg_exec  # Second call (csv)
    ]

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_api_key] = lambda: "valid-key"

    # 1. Test Markdown Export
    res_md = client.get("/api/v1/dashboard/groups/g_export/export?format=markdown")
    assert res_md.status_code == 200
    assert "Strategy Room" in res_md.text
    assert "## Executive Summary" in res_md.text or "## 📝 Executive Summary" in res_md.text

    briefing_cache.clear()

    # 2. Test CSV Export
    res_csv = client.get("/api/v1/dashboard/groups/g_export/export?format=csv")
    assert res_csv.status_code == 200
    assert "Type,Item,Owner,Urgency_or_Classification,Source_Message_ID" in res_csv.text

@pytest.mark.anyio
async def test_event_bus_publish_and_receive():
    bus = EventBus()
    queue = bus.subscribe()
    await bus.publish("test.event", {"hello": "world"})
    gen = bus.event_generator(queue)

    # First event: connected
    chunk1 = await anext(gen)
    assert "event: connected" in chunk1

    # Second event: test.event
    chunk2 = await anext(gen)
    assert "event: test.event" in chunk2
    assert "hello" in chunk2
    bus.unsubscribe(queue)

def test_stream_sse_endpoint():
    client = TestClient(app)
    app.dependency_overrides[get_api_key] = lambda: "valid-key"
    async def mock_generator(_q):
        yield "event: connected\ndata: {\"status\": \"connected\"}\n\n"

    with patch("app.api.endpoints.event_bus.event_generator", side_effect=mock_generator):
        response = client.get("/api/v1/dashboard/stream")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        assert "event: connected" in response.text
