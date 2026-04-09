from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import os
from datetime import datetime
from collections import OrderedDict

from .db.database import engine, Base, get_db
from .db import models
from .api.schemas import MessageIngest
from .api.endpoints import router as dashboard_router

app = FastAPI(
    title="AI WhatsApp Intelligence API",
    description="Backend API for ingesting, analyzing, and retrieving WhatsApp group intelligence.",
    version="1.0.0"
)

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard_router)

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY environment variable is not set")

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(status_code=403, detail="Could not validate credentials")

@app.on_event("startup")
async def startup():
    # Only for development: create tables sync (in production use alembic)
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

@app.get("/")
async def root():
    return {"status": "online", "service": "awi_backend"}

# Global in-memory caches to track existing users and groups
# This avoids unnecessary DB queries for every message in high-volume environments
# Using a simple LRU-style eviction with OrderedDict to prevent unbounded memory growth
class SimpleLRUCache:
    def __init__(self, capacity: int = 10000):
        self.cache = OrderedDict()
        self.capacity = capacity

    def __contains__(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)
            return True
        return False

    def add(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.capacity:
                self.cache.popitem(last=False)
            self.cache[key] = True

_GROUP_CACHE = SimpleLRUCache(capacity=5000)
_USER_CACHE = SimpleLRUCache(capacity=10000)

# Ingestion Webhook used by the Node.js Collector
@app.post("/api/v1/ingest")
async def ingest_message(
    payload: MessageIngest, 
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    # 1. Ensure Group exists
    if payload.group_id not in _GROUP_CACHE:
        group = await db.get(models.Group, payload.group_id)
        if not group:
            group = models.Group(id=payload.group_id, name=payload.group_name)
            db.add(group)
        else:
            _GROUP_CACHE.add(payload.group_id)

    # 2. Ensure User exists
    if payload.sender_id not in _USER_CACHE:
        user = await db.get(models.User, payload.sender_id)
        if not user:
            user = models.User(id=payload.sender_id, name=payload.sender_name)
            db.add(user)
        else:
            _USER_CACHE.add(payload.sender_id)

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
        # Update caches after successful commit
        _GROUP_CACHE.add(payload.group_id)
        _USER_CACHE.add(payload.sender_id)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
    # NOTE: Here we would trigger a Celery task to run AI enrichment asynchronously
    # e.g., celery_app.send_task("enrich_message", args=[msg.id])
    
    return {"status": "success", "message_id": msg.id}
