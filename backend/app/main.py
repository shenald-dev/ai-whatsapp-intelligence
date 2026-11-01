from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
import os
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import collections
from sqlalchemy.dialects.postgresql import insert
import logging

from .db.database import engine, get_db, sanitize_error_msg
from .db import models
from .db.chroma import get_collection_stats
from .api.schemas import MessageIngest
from .api.endpoints import router as dashboard_router
from .api.stream import event_bus
from .workers.celery_config import celery_app
from .api.auth import get_api_key
from .ai.engine import ai_engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables sync for dev/testing (in production use alembic)
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield

app = FastAPI(
    title="AI WhatsApp Intelligence API",
    description="Autonomous Group Operations, Kanban Tasks & Real-Time Intelligence Engine for WhatsApp.",
    version="2.0.0",
    lifespan=lifespan,
    default_response_class=ORJSONResponse
)

# CORS Setup
allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000")
allowed_origins = [origin.strip() for origin in allowed_origins_raw.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(dashboard_router)

class SimpleLRUCache:
    def __init__(self, capacity: int):
        self.cache = collections.OrderedDict()
        self.capacity = capacity

    def get(self, key: str) -> bool:
        if key not in self.cache:
            return False
        self.cache.move_to_end(key)
        return True

    def put(self, key: str) -> None:
        self.cache[key] = True
        self.cache.move_to_end(key)
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

# Cache for entity existence checks
entity_cache = SimpleLRUCache(1000)

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "awi_backend",
        "version": "2.0.0",
        "dashboard_ui": "/dashboard",
        "docs_url": "/docs",
        "health_check": "/health"
    }

@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """System health check verifying database and vector store connectivity."""
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {sanitize_error_msg(str(e))}"

    vector_stats = get_collection_stats()

    is_healthy = db_status == "connected" and vector_stats.get("status") == "online"
    return {
        "status": "healthy" if is_healthy else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_status,
        "chromadb": vector_stats,
        "version": "2.0.0"
    }

# Ingestion Webhook used by the Node.js Collector & CLI Simulator
@app.post("/api/v1/ingest")
async def ingest_message(
    payload: MessageIngest, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(get_api_key)
):
    try:
        cache_updates = []

        # 1. Ensure Group exists
        group_cache_key = f"group_{payload.group_id}"
        if not entity_cache.get(group_cache_key):
            stmt = insert(models.Group).values(
                id=payload.group_id,
                name=payload.group_name
            ).on_conflict_do_nothing(index_elements=['id'])
            await db.execute(stmt)
            cache_updates.append(group_cache_key)

        # 2. Ensure User exists
        user_cache_key = f"user_{payload.sender_id}"
        if not entity_cache.get(user_cache_key):
            stmt = insert(models.User).values(
                id=payload.sender_id,
                name=payload.sender_name
            ).on_conflict_do_nothing(index_elements=['id'])
            await db.execute(stmt)
            cache_updates.append(user_cache_key)

        # Convert JS timestamp (unix seconds) to Datetime
        dt = datetime.fromtimestamp(payload.timestamp, tz=timezone.utc)

        # 3. Save Message with native UPSERT to avoid race conditions
        stmt = insert(models.Message).values(
            id=payload.message_id,
            group_id=payload.group_id,
            sender_id=payload.sender_id,
            content=payload.content,
            timestamp=dt,
            is_media=payload.is_media,
            quoted_msg_id=payload.quoted_msg_id
        ).on_conflict_do_nothing(index_elements=['id']).returning(models.Message.id)

        result = await db.execute(stmt)
        inserted_id = result.scalar()

        await db.commit()

        # 4. Update Cache only after successful commit
        for key in cache_updates:
            entity_cache.put(key)

    except Exception as e:
        await db.rollback()
        safe_error = sanitize_error_msg(str(e))
        logging.error(f"Database error during ingest: {safe_error}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    # If inserted_id is None, it means the message was already inserted by a concurrent request
    if not inserted_id:
        return {"status": "success", "message_id": payload.message_id, "detail": "Already ingested"}

    # Immediate incident detection for instant real-time alerting
    if hasattr(ai_engine, "detect_incident_alert_sync"):
        incident = ai_engine.detect_incident_alert_sync(payload.content, sender_name=payload.sender_name)
        if incident:
            try:
                alert_id = str(uuid.uuid4())
                alert_stmt = insert(models.Alert).values(
                    id=alert_id,
                    group_id=payload.group_id,
                    source_message_id=inserted_id,
                    severity=incident["severity"],
                    alert_type=incident["alert_type"],
                    title=incident["title"],
                    description=incident["description"],
                    status="active"
                )
                await db.execute(alert_stmt)
                await db.commit()

                background_tasks.add_task(
                    event_bus.publish,
                    "alert.triggered",
                    {
                        "alert_id": alert_id,
                        "group_id": payload.group_id,
                        "group_name": payload.group_name,
                        "severity": incident["severity"],
                        "alert_type": incident["alert_type"],
                        "title": incident["title"],
                        "description": incident["description"]
                    }
                )
            except Exception as alert_err:
                logging.warning(f"Non-critical error logging alert: {alert_err}")
        
    # Trigger a Celery task to run AI enrichment asynchronously
    background_tasks.add_task(celery_app.send_task, "enrich_message", args=[inserted_id])

    # Broadcast real-time message.ingested event over SSE stream
    background_tasks.add_task(
        event_bus.publish,
        "message.ingested",
        {
            "message_id": inserted_id,
            "group_id": payload.group_id,
            "group_name": payload.group_name,
            "sender_name": payload.sender_name,
            "content": payload.content,
            "timestamp": payload.timestamp
        }
    )
    
    return {"status": "success", "message_id": inserted_id}

FRONTEND_INDEX_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "frontend", "index.html")
)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_ui():
    """Interactive glassmorphic web dashboard for AI WhatsApp Intelligence."""
    if os.path.exists(FRONTEND_INDEX_PATH):
        try:
            with open(FRONTEND_INDEX_PATH, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        except Exception as e:
            logging.error(f"Error reading frontend template: {e}")

    # Resilient fallback
    return HTMLResponse(
        content="""<!DOCTYPE html><html><head><title>AI WhatsApp Intelligence</title></head>
        <body style="background:#080C14;color:#FFF;font-family:sans-serif;padding:40px;">
        <h1>AI WhatsApp Intelligence Hub v2.0</h1>
        <p>Operational. Access REST endpoints at <a href="/docs" style="color:#25D366">/docs</a>.</p>
        </body></html>"""
    )
