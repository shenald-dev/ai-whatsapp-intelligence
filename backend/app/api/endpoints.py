from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func
from sqlalchemy import case
from typing import List

from ..db.database import get_db
from ..db import models
from .schemas import MessageResponse

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])

@router.get("/groups", response_model=List[dict])
async def get_groups(db: AsyncSession = Depends(get_db)):
    """Fetch all monitored groups."""
    result = await db.execute(select(models.Group))
    groups = result.scalars().all()
    return [{"id": g.id, "name": g.name} for g in groups]

@router.get("/groups/{group_id}/stats")
async def get_group_stats(group_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch high-level stats for the dashboard using optimized SQL aggregations."""
    
    query = select(
        func.count(models.Message.id).label("total"),
        func.coalesce(func.sum(case((models.Message.is_analyzed == True, 1), else_=0)), 0).label("analyzed"),
        func.coalesce(func.sum(case((models.Message.sentiment == 'positive', 1), else_=0)), 0).label("positive"),
        func.coalesce(func.sum(case((models.Message.sentiment == 'negative', 1), else_=0)), 0).label("negative"),
        func.coalesce(func.sum(case((models.Message.sentiment == 'neutral', 1), else_=0)), 0).label("neutral"),
        func.coalesce(func.sum(case((models.Message.classification == 'task', 1), else_=0)), 0).label("tasks"),
        func.coalesce(func.sum(case((models.Message.classification == 'decision', 1), else_=0)), 0).label("decisions"),
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

    return {
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

@router.get("/groups/{group_id}/messages", response_model=List[MessageResponse])
async def get_recent_messages(group_id: str, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Fetch recent messages with their AI analysis attached."""
    result = await db.execute(
        select(models.Message)
        .where(models.Message.group_id == group_id)
        .order_by(models.Message.timestamp.desc())
        .limit(limit)
    )
    return result.scalars().all()
