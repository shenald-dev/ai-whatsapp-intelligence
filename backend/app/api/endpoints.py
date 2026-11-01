import time
import collections
import logging
import csv
import io
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func

from ..db.database import get_db, sanitize_error_msg
from ..db import models
from ..db.chroma import search_message_embeddings
from ..ai.engine import ai_engine
from .stream import event_bus
from .schemas import (
    MessageResponse,
    GroupResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
    SearchResultItem,
    AskAIRequest,
    AskAIResponse,
    CitationItem,
    ExecutiveBriefingResponse,
    ActionItem,
    DecisionItem,
    QuestionItem,
    TaskItemCreate,
    TaskItemUpdate,
    TaskItemResponse,
    AlertResponse,
    AlertUpdate,
)
from .auth import get_api_key

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"], dependencies=[Depends(get_api_key)])

class BoundedTTLCache:
    """
    A thread-safe Bounded TTL Cache for API responses.
    Leverages atomic operations of OrderedDict in standard async event loop.
    """
    def __init__(self, capacity: int, ttl: int):
        self.capacity = capacity
        self.ttl = ttl
        self.cache = collections.OrderedDict()

    def get(self, key: str):
        if key not in self.cache:
            return None
        value, timestamp = self.cache[key]
        if time.monotonic() - timestamp > self.ttl:
            del self.cache[key]
            return None
        self.cache.move_to_end(key)
        return value

    def put(self, key: str, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = (value, time.monotonic())
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

    def clear(self):
        self.cache.clear()

stats_cache = BoundedTTLCache(capacity=100, ttl=60)
briefing_cache = BoundedTTLCache(capacity=50, ttl=60)

# --- Core Group & Message Endpoints ---

@router.get("/groups", response_model=List[GroupResponse])
async def get_groups(
    limit: int = Query(50, ge=1, le=100, description="Max groups to fetch"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db)
):
    """Fetch all monitored groups."""
    try:
        result = await db.execute(
            select(models.Group.id, models.Group.name)
            .order_by(models.Group.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [GroupResponse.model_construct(id=row.id, name=row.name) for row in result.all()]
    except Exception as e:
        safe_error = sanitize_error_msg(str(e))
        logging.error(f"Database error in get_groups: {safe_error}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/groups/{group_id}/stats")
async def get_group_stats(group_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch high-level stats for the dashboard using optimized SQL aggregations."""
    cache_key = f"stats_{group_id}"
    cached_stats = stats_cache.get(cache_key)
    if cached_stats is not None:
        return cached_stats

    try:
        query = select(
            func.count().label("total"),
            func.count().filter(models.Message.is_analyzed.is_(True)).label("analyzed"),
            func.count().filter(models.Message.sentiment == 'positive').label("positive"),
            func.count().filter(models.Message.sentiment == 'negative').label("negative"),
            func.count().filter(models.Message.sentiment == 'neutral').label("neutral"),
            func.count().filter(models.Message.classification == 'task').label("tasks"),
            func.count().filter(models.Message.classification == 'decision').label("decisions"),
        ).where(models.Message.group_id == group_id)
        
        result = await db.execute(query)
        row = result.first()

        total = (row.total or 0) if row else 0
        analyzed = (row.analyzed or 0) if row else 0
        positive = (row.positive or 0) if row else 0
        negative = (row.negative or 0) if row else 0
        neutral = (row.neutral or 0) if row else 0
        tasks_found = (row.tasks or 0) if row else 0
        decisions_found = (row.decisions or 0) if row else 0

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
            "decisions_detected": decisions_found,
            "tasks_pending": getattr(row, "tasks_pending", tasks_found),
            "tasks_completed": getattr(row, "tasks_completed", 0),
            "active_alerts": getattr(row, "active_alerts", 0)
        }

        stats_cache.put(cache_key, response_data)
        return response_data
    except Exception as e:
        safe_error = sanitize_error_msg(str(e))
        logging.error(f"Database error in get_group_stats: {safe_error}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/groups/{group_id}/messages", response_model=List[MessageResponse])
async def get_recent_messages(
    group_id: str,
    limit: int = Query(50, ge=1, le=100, description="Max messages to fetch"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db)
):
    """Fetch recent messages with their AI analysis attached."""
    try:
        result = await db.execute(
            select(models.Message.id, models.Message.content, models.Message.sentiment, models.Message.classification)
            .where(models.Message.group_id == group_id)
            .order_by(models.Message.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        return [
            MessageResponse.model_construct(
                id=row.id,
                content=row.content,
                sentiment=row.sentiment,
                classification=row.classification
            )
            for row in result.all()
        ]
    except Exception as e:
        safe_error = sanitize_error_msg(str(e))
        logging.error(f"Database error in get_recent_messages: {safe_error}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# --- Next-Gen Semantic Search & RAG Q&A Endpoints ---

@router.post("/search", response_model=SemanticSearchResponse)
async def semantic_search(
    payload: SemanticSearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Performs hybrid semantic vector search over WhatsApp messages.
    Falls back gracefully to indexed full-text/relational search if vector index is warm or empty.
    """
    try:
        where_clause = {}
        if payload.group_id:
            where_clause["group_id"] = payload.group_id
        if payload.classification:
            where_clause["classification"] = payload.classification
        if payload.sentiment:
            where_clause["sentiment"] = payload.sentiment

        vector_hits = search_message_embeddings(
            query_text=payload.query,
            n_results=payload.limit * 2,
            where=where_clause if where_clause else None
        )

        results: List[SearchResultItem] = []

        if vector_hits:
            hit_ids = [h["message_id"] for h in vector_hits]
            stmt = (
                select(models.Message, models.Group.name.label("group_name"), models.User.name.label("user_name"))
                .outerjoin(models.Group, models.Message.group_id == models.Group.id)
                .outerjoin(models.User, models.Message.sender_id == models.User.id)
                .where(models.Message.id.in_(hit_ids))
            )
            db_res = await db.execute(stmt)
            db_map = {row.Message.id: (row.Message, row.group_name, row.user_name) for row in db_res.all()}

            for h in vector_hits:
                sim = h.get("similarity", 0.0)
                if sim < payload.min_similarity:
                    continue

                msg_id = h["message_id"]
                db_record = db_map.get(msg_id)
                if db_record:
                    msg, g_name, u_name = db_record
                    results.append(
                        SearchResultItem(
                            message_id=msg.id,
                            content=msg.content or h.get("content", ""),
                            group_id=msg.group_id,
                            group_name=g_name or "Unknown Group",
                            sender_id=msg.sender_id,
                            sender_name=u_name or "Unknown User",
                            timestamp=msg.timestamp.isoformat() if msg.timestamp else None,
                            sentiment=msg.sentiment,
                            classification=msg.classification,
                            similarity=sim
                        )
                    )
                else:
                    meta = h.get("metadata", {})
                    results.append(
                        SearchResultItem(
                            message_id=msg_id,
                            content=h.get("content", ""),
                            group_id=meta.get("group_id"),
                            group_name="Unknown Group",
                            sender_id=meta.get("sender_id"),
                            sender_name="Unknown User",
                            timestamp=None,
                            sentiment=meta.get("sentiment"),
                            classification=meta.get("classification"),
                            similarity=sim
                        )
                    )

                if len(results) >= payload.limit:
                    break

        # Fallback to database keyword search if semantic search yields no results
        if not results:
            stmt = (
                select(models.Message, models.Group.name.label("group_name"), models.User.name.label("user_name"))
                .outerjoin(models.Group, models.Message.group_id == models.Group.id)
                .outerjoin(models.User, models.Message.sender_id == models.User.id)
                .where(models.Message.content.ilike(f"%{payload.query}%"))
            )
            if payload.group_id:
                stmt = stmt.where(models.Message.group_id == payload.group_id)
            if payload.classification:
                stmt = stmt.where(models.Message.classification == payload.classification)
            if payload.sentiment:
                stmt = stmt.where(models.Message.sentiment == payload.sentiment)

            stmt = stmt.order_by(models.Message.timestamp.desc()).limit(payload.limit)
            db_res = await db.execute(stmt)

            for row in db_res.all():
                msg = row.Message
                results.append(
                    SearchResultItem(
                        message_id=msg.id,
                        content=msg.content or "",
                        group_id=msg.group_id,
                        group_name=row.group_name or "Unknown Group",
                        sender_id=msg.sender_id,
                        sender_name=row.user_name or "Unknown User",
                        timestamp=msg.timestamp.isoformat() if msg.timestamp else None,
                        sentiment=msg.sentiment,
                        classification=msg.classification,
                        similarity=0.75
                    )
                )

        return SemanticSearchResponse(
            query=payload.query,
            total_found=len(results),
            results=results
        )
    except Exception as e:
        safe_error = sanitize_error_msg(str(e))
        logging.error(f"Semantic search error: {safe_error}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/ask", response_model=AskAIResponse)
async def ask_intelligence(
    payload: AskAIRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Answers natural language inquiries over WhatsApp group history using Retrieval-Augmented Generation (RAG).
    Returns synthesized answer with exact message citations.
    """
    try:
        where_clause = {"group_id": payload.group_id} if payload.group_id else None
        vector_hits = search_message_embeddings(
            query_text=payload.question,
            n_results=10,
            where=where_clause
        )

        context_messages = []
        if vector_hits:
            hit_ids = [h["message_id"] for h in vector_hits]
            stmt = (
                select(models.Message, models.User.name.label("user_name"))
                .outerjoin(models.User, models.Message.sender_id == models.User.id)
                .where(models.Message.id.in_(hit_ids))
            )
            db_res = await db.execute(stmt)
            for row in db_res.all():
                context_messages.append({
                    "id": row.Message.id,
                    "sender_name": row.user_name or "Team Member",
                    "content": row.Message.content,
                    "timestamp": row.Message.timestamp.isoformat() if row.Message.timestamp else ""
                })

        # If semantic search has few matches, supplement with recent group messages
        if len(context_messages) < 3 and payload.group_id:
            recent_stmt = (
                select(models.Message, models.User.name.label("user_name"))
                .outerjoin(models.User, models.Message.sender_id == models.User.id)
                .where(models.Message.group_id == payload.group_id)
                .order_by(models.Message.timestamp.desc())
                .limit(10)
            )
            recent_res = await db.execute(recent_stmt)
            existing_ids = {m["id"] for m in context_messages}
            for row in recent_res.all():
                if row.Message.id not in existing_ids:
                    context_messages.append({
                        "id": row.Message.id,
                        "sender_name": row.user_name or "Team Member",
                        "content": row.Message.content,
                        "timestamp": row.Message.timestamp.isoformat() if row.Message.timestamp else ""
                    })

        qa_result = ai_engine.answer_question_sync(payload.question, context_messages)

        citations = [
            CitationItem(
                message_id=c["message_id"],
                sender_name=c["sender_name"],
                timestamp=c["timestamp"],
                snippet=c["snippet"]
            )
            for c in qa_result.get("citations", [])
        ]

        return AskAIResponse(
            question=payload.question,
            answer=qa_result.get("answer", "No response generated."),
            confidence=qa_result.get("confidence", 0.0),
            citations=citations,
            key_topics=qa_result.get("key_topics", []),
            relevant_messages_count=len(context_messages)
        )
    except Exception as e:
        safe_error = sanitize_error_msg(str(e))
        logging.error(f"RAG ask error: {safe_error}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# --- Autonomous Executive Intelligence Briefing Endpoints ---

@router.get("/groups/{group_id}/briefing", response_model=ExecutiveBriefingResponse)
async def get_executive_briefing(
    group_id: str,
    hours: int = Query(24, ge=1, le=720, description="Time window in hours"),
    db: AsyncSession = Depends(get_db)
):
    """
    Generates a structured executive intelligence briefing for a group.
    Surfaces key decisions, prioritized action items, open questions, and sentiment trajectory.
    """
    cache_key = f"briefing_{group_id}_{hours}"
    cached = briefing_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        group_res = await db.execute(select(models.Group).where(models.Group.id == group_id))
        group = group_res.scalar_one_or_none()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        msg_stmt = (
            select(models.Message, models.User.name.label("user_name"))
            .outerjoin(models.User, models.Message.sender_id == models.User.id)
            .where(models.Message.group_id == group_id)
            .where(models.Message.timestamp >= cutoff)
            .order_by(models.Message.timestamp.asc())
        )
        res = await db.execute(msg_stmt)
        messages_data = []
        for row in res.all():
            m = row.Message
            messages_data.append({
                "id": m.id,
                "content": m.content or "",
                "sender_id": m.sender_id,
                "sender_name": row.user_name or "Team Member",
                "sentiment": m.sentiment or "neutral",
                "classification": m.classification or "discussion",
                "timestamp": m.timestamp.isoformat() if m.timestamp else ""
            })

        raw_briefing = ai_engine.generate_briefing_sync(group.name or group.id, messages_data)

        decisions = [
            DecisionItem(
                decision=d["decision"],
                decider=d.get("decider"),
                source_message_id=d.get("source_message_id")
            )
            for d in raw_briefing.get("key_decisions", [])
        ]

        actions = [
            ActionItem(
                task=t["task"],
                assignee=t.get("assignee"),
                urgency=t.get("urgency", "medium"),
                source_message_id=t.get("source_message_id")
            )
            for t in raw_briefing.get("action_items", [])
        ]

        questions = [
            QuestionItem(
                question=q["question"],
                asker=q.get("asker"),
                source_message_id=q.get("source_message_id")
            )
            for q in raw_briefing.get("open_questions", [])
        ]

        response = ExecutiveBriefingResponse(
            group_id=group.id,
            group_name=group.name or group.id,
            time_window_hours=hours,
            total_messages_analyzed=len(messages_data),
            executive_summary=raw_briefing.get("executive_summary", ""),
            key_decisions=decisions,
            action_items=actions,
            open_questions=questions,
            sentiment_breakdown=raw_briefing.get("sentiment_summary", {"positive": 0, "neutral": 0, "negative": 0})
        )

        briefing_cache.put(cache_key, response)
        return response
    except HTTPException:
        raise
    except Exception as e:
        safe_error = sanitize_error_msg(str(e))
        logging.error(f"Briefing generation error: {safe_error}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/groups/{group_id}/export")
async def export_intelligence(
    group_id: str,
    format: Literal["markdown", "json", "csv"] = Query("markdown", description="Export format"),
    hours: int = Query(72, ge=1, le=720, description="Time window in hours"),
    db: AsyncSession = Depends(get_db)
):
    """
    Exports a comprehensive intelligence report for team briefings, Notion, Slack, or archival.
    Supports Markdown, JSON, and CSV.
    """
    briefing = await get_executive_briefing(group_id=group_id, hours=hours, db=db)

    if format == "json":
        return briefing.model_dump()

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Type", "Item", "Owner", "Urgency_or_Classification", "Source_Message_ID"])
        for d in briefing.key_decisions:
            writer.writerow(["Decision", d.decision, d.decider or "", "Finalized", d.source_message_id or ""])
        for a in briefing.action_items:
            writer.writerow(["Action Item", a.task, a.assignee or "", a.urgency, a.source_message_id or ""])
        for q in briefing.open_questions:
            writer.writerow(["Open Question", q.question, q.asker or "", "Pending", q.source_message_id or ""])
        return PlainTextResponse(content=output.getvalue(), media_type="text/csv")

    md_lines = [
        f"# 📊 WhatsApp Group Intelligence Briefing: {briefing.group_name}",
        f"*Window: Last {briefing.time_window_hours} Hours | Total Messages Analyzed: {briefing.total_messages_analyzed}*",
        "",
        "## 📝 Executive Summary",
        briefing.executive_summary,
        "",
        "## 🎯 Key Decisions",
    ]
    if briefing.key_decisions:
        for idx, d in enumerate(briefing.key_decisions, 1):
            decider_tag = f" *(Decided by {d.decider})*" if d.decider else ""
            md_lines.append(f"{idx}. {d.decision}{decider_tag}")
    else:
        md_lines.append("*No formal decisions recorded during this period.*")

    md_lines.extend(["", "## ✅ Action Items & Tasks"])
    if briefing.action_items:
        for idx, a in enumerate(briefing.action_items, 1):
            owner_tag = f" — **@{a.assignee}**" if a.assignee else ""
            urgency_badge = f" `[{a.urgency.upper()}]`" if a.urgency == "high" else ""
            md_lines.append(f"{idx}. {urgency_badge} {a.task}{owner_tag}")
    else:
        md_lines.append("*No open tasks detected during this period.*")

    md_lines.extend(["", "## ❓ Open Questions & Pending Discussions"])
    if briefing.open_questions:
        for idx, q in enumerate(briefing.open_questions, 1):
            asker_tag = f" *(from {q.asker})*" if q.asker else ""
            md_lines.append(f"{idx}. {q.question}{asker_tag}")
    else:
        md_lines.append("*All discussions appear resolved.*")

    md_lines.extend([
        "",
        "## 📈 Sentiment & Team Dynamics",
        f"- **Positive Sentiment:** {briefing.sentiment_breakdown.get('positive', 0)}",
        f"- **Neutral / Informational:** {briefing.sentiment_breakdown.get('neutral', 0)}",
        f"- **Negative / Blockers:** {briefing.sentiment_breakdown.get('negative', 0)}",
        "",
        "---",
        "*Generated autonomously by AI WhatsApp Intelligence Monitor*"
    ])

    return PlainTextResponse(content="\n".join(md_lines), media_type="text/markdown")

# --- Action Items & Kanban Endpoints ---

@router.get("/groups/{group_id}/tasks", response_model=List[TaskItemResponse])
async def get_group_tasks(
    group_id: str,
    status: Optional[str] = Query(None, description="Filter by status: todo, in_progress, done, dismissed"),
    urgency: Optional[str] = Query(None, description="Filter by urgency: high, medium, low"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Fetches action items/tasks for the group's Kanban tracker."""
    try:
        stmt = select(models.ActionItem).where(models.ActionItem.group_id == group_id)
        if status:
            stmt = stmt.where(models.ActionItem.status == status)
        if urgency:
            stmt = stmt.where(models.ActionItem.urgency == urgency)
        stmt = stmt.order_by(models.ActionItem.created_at.desc()).limit(limit).offset(offset)
        res = await db.execute(stmt)
        tasks = res.scalars().all()
        return [
            TaskItemResponse(
                id=t.id,
                group_id=t.group_id,
                source_message_id=t.source_message_id,
                title=t.title,
                description=t.description,
                assignee=t.assignee,
                assignee_id=t.assignee_id,
                urgency=t.urgency,
                status=t.status,
                due_date=t.due_date.isoformat() if t.due_date else None,
                created_at=t.created_at.isoformat() if t.created_at else None,
                completed_at=t.completed_at.isoformat() if t.completed_at else None,
            )
            for t in tasks
        ]
    except Exception as e:
        safe_error = sanitize_error_msg(str(e))
        logging.error(f"Error fetching tasks: {safe_error}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/groups/{group_id}/tasks", response_model=TaskItemResponse)
async def create_group_task(
    group_id: str,
    payload: TaskItemCreate,
    db: AsyncSession = Depends(get_db)
):
    """Creates a new action item manually or via automation."""
    try:
        task_id = str(uuid.uuid4())
        task_item = models.ActionItem(
            id=task_id,
            group_id=group_id,
            title=payload.title,
            description=payload.description,
            assignee=payload.assignee,
            urgency=payload.urgency,
            status=payload.status,
            created_at=datetime.now(timezone.utc)
        )
        db.add(task_item)
        await db.commit()
        await db.refresh(task_item)

        resp = TaskItemResponse(
            id=task_item.id,
            group_id=task_item.group_id,
            source_message_id=task_item.source_message_id,
            title=task_item.title,
            description=task_item.description,
            assignee=task_item.assignee,
            assignee_id=task_item.assignee_id,
            urgency=task_item.urgency,
            status=task_item.status,
            due_date=None,
            created_at=task_item.created_at.isoformat() if task_item.created_at else None,
            completed_at=None,
        )

        await event_bus.publish("task.created", resp.model_dump())
        return resp
    except Exception as e:
        await db.rollback()
        safe_error = sanitize_error_msg(str(e))
        logging.error(f"Error creating task: {safe_error}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.patch("/tasks/{task_id}", response_model=TaskItemResponse)
@router.post("/tasks/{task_id}", response_model=TaskItemResponse)
async def update_task(
    task_id: str,
    payload: TaskItemUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Updates a task's status (todo -> in_progress -> done), urgency, assignee, or title."""
    try:
        stmt = select(models.ActionItem).where(models.ActionItem.id == task_id)
        res = await db.execute(stmt)
        task = res.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        if payload.title is not None:
            task.title = payload.title
        if payload.description is not None:
            task.description = payload.description
        if payload.assignee is not None:
            task.assignee = payload.assignee
        if payload.urgency is not None:
            task.urgency = payload.urgency
        if payload.status is not None:
            task.status = payload.status
            if payload.status == "done":
                task.completed_at = datetime.now(timezone.utc)
            elif payload.status in ["todo", "in_progress"]:
                task.completed_at = None

        await db.commit()
        await db.refresh(task)

        resp = TaskItemResponse(
            id=task.id,
            group_id=task.group_id,
            source_message_id=task.source_message_id,
            title=task.title,
            description=task.description,
            assignee=task.assignee,
            assignee_id=task.assignee_id,
            urgency=task.urgency,
            status=task.status,
            due_date=task.due_date.isoformat() if task.due_date else None,
            created_at=task.created_at.isoformat() if task.created_at else None,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
        )
        await event_bus.publish("task.updated", resp.model_dump())
        return resp
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        safe_error = sanitize_error_msg(str(e))
        logging.error(f"Error updating task: {safe_error}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.delete("/tasks/{task_id}")
@router.post("/tasks/{task_id}/delete")
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """Deletes an action item."""
    try:
        stmt = select(models.ActionItem).where(models.ActionItem.id == task_id)
        res = await db.execute(stmt)
        task = res.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        group_id = task.group_id
        await db.delete(task)
        await db.commit()
        await event_bus.publish("task.deleted", {"task_id": task_id, "group_id": group_id})
        return {"status": "success", "task_id": task_id}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        safe_error = sanitize_error_msg(str(e))
        logging.error(f"Error deleting task: {safe_error}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# --- Incident & Anomaly Alert Endpoints ---

@router.get("/groups/{group_id}/alerts", response_model=List[AlertResponse])
async def get_group_alerts(
    group_id: str,
    status: Optional[str] = Query(None, description="Filter by status: active, acknowledged, resolved"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Fetches real-time incident and anomaly alerts for a group."""
    try:
        stmt = select(models.Alert).where(models.Alert.group_id == group_id)
        if status:
            stmt = stmt.where(models.Alert.status == status)
        stmt = stmt.order_by(models.Alert.created_at.desc()).limit(limit)
        res = await db.execute(stmt)
        alerts = res.scalars().all()
        return [
            AlertResponse(
                id=a.id,
                group_id=a.group_id,
                source_message_id=a.source_message_id,
                severity=a.severity,
                alert_type=a.alert_type,
                title=a.title,
                description=a.description,
                status=a.status,
                created_at=a.created_at.isoformat() if a.created_at else None,
                resolved_at=a.resolved_at.isoformat() if a.resolved_at else None,
            )
            for a in alerts
        ]
    except Exception as e:
        safe_error = sanitize_error_msg(str(e))
        logging.error(f"Error fetching alerts: {safe_error}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.patch("/alerts/{alert_id}", response_model=AlertResponse)
@router.post("/alerts/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: str,
    payload: AlertUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Updates an alert status (acknowledge or resolve)."""
    try:
        stmt = select(models.Alert).where(models.Alert.id == alert_id)
        res = await db.execute(stmt)
        alert = res.scalar_one_or_none()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        alert.status = payload.status
        if payload.status == "resolved":
            alert.resolved_at = datetime.now(timezone.utc)
        elif payload.status in ["active", "acknowledged"]:
            alert.resolved_at = None

        await db.commit()
        await db.refresh(alert)

        resp = AlertResponse(
            id=alert.id,
            group_id=alert.group_id,
            source_message_id=alert.source_message_id,
            severity=alert.severity,
            alert_type=alert.alert_type,
            title=alert.title,
            description=alert.description,
            status=alert.status,
            created_at=alert.created_at.isoformat() if alert.created_at else None,
            resolved_at=alert.resolved_at.isoformat() if alert.resolved_at else None,
        )
        await event_bus.publish("alert.updated", resp.model_dump())
        return resp
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        safe_error = sanitize_error_msg(str(e))
        logging.error(f"Error updating alert: {safe_error}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# --- Real-Time Intelligence Event Stream (SSE) ---

@router.get("/stream")
async def intelligence_stream():
    """
    Subscribes to live Server-Sent Events (SSE) broadcasting real-time message ingestions,
    AI enrichments, and intelligence alerts.
    """
    queue = event_bus.subscribe()
    return StreamingResponse(
        event_bus.event_generator(queue),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
