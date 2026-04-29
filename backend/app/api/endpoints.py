import time
import collections
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func
from typing import List

from ..db.database import get_db
from ..db import models
from .schemas import MessageResponse
from .auth import get_api_key

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"], dependencies=[Depends(get_api_key)])

class BoundedTTLCache:
    def __init__(self, capacity: int, ttl: int):
        self.capacity = capacity
        self.ttl = ttl
        self.cache = collections.OrderedDict()

    def get(self, key: str):
        if key not in self.cache:
            return None
        value, timestamp = self.cache[key]
        if time.time() - timestamp > self.ttl:
            del self.cache[key]
            return None
        self.cache.move_to_end(key)
        return value

    def put(self, key: str, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = (value, time.time())
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

    def clear(self):
        self.cache.clear()

stats_cache = BoundedTTLCache(capacity=100, ttl=60)

@router.get("/groups", response_model=List[dict])
async def get_groups(
    limit: int = Query(50, ge=1, le=100, description="Max groups to fetch"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db)
):
    """Fetch all monitored groups."""
    result = await db.execute(
        select(models.Group)
        .order_by(models.Group.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    groups = result.scalars().all()
    return [{"id": g.id, "name": g.name} for g in groups]

@router.get("/groups/{group_id}/stats")
async def get_group_stats(group_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch high-level stats for the dashboard using optimized SQL aggregations."""
    
    cache_key = f"stats_{group_id}"
    cached_stats = stats_cache.get(cache_key)
    if cached_stats is not None:
        return cached_stats

    query = select(
        func.count(models.Message.id).label("total"),
        func.count(models.Message.id).filter(models.Message.is_analyzed.is_(True)).label("analyzed"),
        func.count(models.Message.id).filter(models.Message.sentiment == 'positive').label("positive"),
        func.count(models.Message.id).filter(models.Message.sentiment == 'negative').label("negative"),
        func.count(models.Message.id).filter(models.Message.sentiment == 'neutral').label("neutral"),
        func.count(models.Message.id).filter(models.Message.classification == 'task').label("tasks"),
        func.count(models.Message.id).filter(models.Message.classification == 'decision').label("decisions"),
    ).where(models.Message.group_id == group_id)
    
    result = await db.execute(query)
    row = result.first()

    total = row.total if row else 0
    analyzed = row.analyzed if row else 0
    positive = row.positive if row else 0
    negative = row.negative if row else 0
    neutral = row.neutral if row else 0
    tasks_found = row.tasks if row else 0
    decisions_found = row.decisions if row else 0

    response_data = {
        "group_id": group_id,
        "total_messages": total,
        "ai_analyzed": analyzed,
        "sentiment_distribution": {
            "positive": positive,
            "negative": negative,
            "neutral": neutral
        },
        "tasks_detected": tasks_found,
        "decisions_detected": decisions_found
    }

    stats_cache.put(cache_key, response_data)
    return response_data

@router.get("/groups/{group_id}/messages", response_model=List[MessageResponse])
async def get_recent_messages(
    group_id: str,
    limit: int = Query(50, ge=1, le=100, description="Max messages to fetch"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db)
):
    """Fetch recent messages with their AI analysis attached."""
    result = await db.execute(
        select(models.Message)
        .where(models.Message.group_id == group_id)
        .order_by(models.Message.timestamp.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()
