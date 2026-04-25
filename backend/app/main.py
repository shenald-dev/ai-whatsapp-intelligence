from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
import os
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import collections
from sqlalchemy.dialects.postgresql import insert

from .db.database import engine, get_db
from .db import models
from .api.schemas import MessageIngest
from .api.endpoints import router as dashboard_router
from .workers.celery_config import celery_app
from .api.auth import get_api_key

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Only for development: create tables sync (in production use alembic)
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield

app = FastAPI(
    title="AI WhatsApp Intelligence API",
    description="Backend API for ingesting, analyzing, and retrieving WhatsApp group intelligence.",
    version="1.0.16",
    lifespan=lifespan
)

# CORS Setup
allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_raw.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)

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
    return {"status": "online", "service": "awi_backend"}

# Ingestion Webhook used by the Node.js Collector
@app.post("/api/v1/ingest")
async def ingest_message(
    payload: MessageIngest, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(get_api_key)
):
    try:
        # Tracking if we need to cache these after commit
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
        raise HTTPException(status_code=500, detail=str(e))

    # If inserted_id is None, it means the message was already inserted by a concurrent request
    if not inserted_id:
        return {"status": "success", "message_id": payload.message_id, "detail": "Already ingested"}
        
    # Trigger a Celery task to run AI enrichment asynchronously
    background_tasks.add_task(celery_app.send_task, "enrich_message", args=[inserted_id])
    
    return {"status": "success", "message_id": inserted_id}
