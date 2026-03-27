from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import os
from datetime import datetime
from contextlib import asynccontextmanager
import collections

from .db.database import engine, Base, get_db
from .db import models
from .api.schemas import MessageIngest
from .api.endpoints import router as dashboard_router
from .workers.celery_config import celery_app

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Only for development: create tables sync (in production use alembic)
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield

app = FastAPI(
    title="AI WhatsApp Intelligence API",
    description="Backend API for ingesting, analyzing, and retrieving WhatsApp group intelligence.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Setup
allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_raw.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY environment variable is not set")

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(status_code=403, detail="Could not validate credentials")

@app.get("/")
async def root():
    return {"status": "online", "service": "awi_backend"}

# Ingestion Webhook used by the Node.js Collector
@app.post("/api/v1/ingest")
async def ingest_message(
    payload: MessageIngest, 
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    # Tracking if we need to cache these after commit
    cache_updates = []

    # 1. Ensure Group exists
    group_cache_key = f"group_{payload.group_id}"
    if not entity_cache.get(group_cache_key):
        group = await db.get(models.Group, payload.group_id)
        if not group:
            group = models.Group(id=payload.group_id, name=payload.group_name)
            db.add(group)
        cache_updates.append(group_cache_key)

    # 2. Ensure User exists
    user_cache_key = f"user_{payload.sender_id}"
    if not entity_cache.get(user_cache_key):
        user = await db.get(models.User, payload.sender_id)
        if not user:
            user = models.User(id=payload.sender_id, name=payload.sender_name)
            db.add(user)
        cache_updates.append(user_cache_key)

    # Convert JS timestamp (unix seconds) to Datetime
    dt = datetime.fromtimestamp(payload.timestamp)

    # 3. Save Message
    msg = models.Message(
        id=payload.message_id,
        group_id=payload.group_id,
        sender_id=payload.sender_id,
        content=payload.content,
        timestamp=dt,
        is_media=payload.is_media,
        quoted_msg_id=payload.quoted_msg_id
    )
    db.add(msg)
    
    try:
        await db.commit()

        # 4. Update Cache only after successful commit
        for key in cache_updates:
            entity_cache.put(key)

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
    # Trigger a Celery task to run AI enrichment asynchronously
    celery_app.send_task("enrich_message", args=[msg.id])
    
    return {"status": "success", "message_id": msg.id}
