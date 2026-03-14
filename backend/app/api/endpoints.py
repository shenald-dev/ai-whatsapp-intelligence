from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
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
    """Fetch high-level stats for the dashboard."""
    # This would normally be complex aggregations, simplified for this template
    messages = await db.execute(select(models.Message).where(models.Message.group_id == group_id))
    all_msgs = messages.scalars().all()
    
    total = len(all_msgs)
    analyzed = sum(1 for m in all_msgs if m.is_analyzed)
    
    # Sentiment distribution
    sentiments = {"positive": 0, "negative": 0, "neutral": 0}
    for m in all_msgs:
        if m.sentiment in sentiments:
            sentiments[m.sentiment] += 1
            
    # Classifications
    tasks_found = sum(1 for m in all_msgs if m.classification == "task")
    decisions_found = sum(1 for m in all_msgs if m.classification == "decision")
            
    return {
        "group_id": group_id,
        "total_messages": total,
        "ai_analyzed": analyzed,
        "sentiment_distribution": sentiments,
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
