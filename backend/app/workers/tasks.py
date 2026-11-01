from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker, load_only
import os
import uuid
from dotenv import load_dotenv
import logging

from ..db.models import Message, ActionItem, Alert, User
from ..ai.engine import ai_engine
from ..db.chroma import store_message_embedding

load_dotenv()

# Worker uses sync engine for simplicity within Celery
SYNC_DB_URL = os.getenv("SYNC_DATABASE_URL")
if not SYNC_DB_URL:
    raise ValueError("SYNC_DATABASE_URL environment variable is not set")

engine = create_engine(
    SYNC_DB_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def process_message(message_id: str):
    """Celery task worker to enrich a message with AI, extract action items, and detect incidents."""
    session = SessionLocal()
    try:
        msg = session.get(Message, message_id, options=[load_only(Message.content, Message.group_id, Message.sender_id, Message.is_analyzed)])
        if not msg or msg.is_analyzed or not msg.content:
            return {"status": "skipped", "reason": "Not found, analyzed, or empty"}

        # Extract needed fields before committing to prevent lazy loading
        content = msg.content
        group_id = msg.group_id
        sender_id = msg.sender_id
        user = session.get(User, sender_id) if sender_id else None
        sender_name = user.name if user else "Team Member"

        # Release the database connection back to the pool before blocking on the network call
        session.commit()

        # Run AI analysis (async block within sync celery task)
        analysis = ai_engine.analyze_message_sync(content)
        sentiment = analysis.get("sentiment")
        classification = analysis.get("classification")

        # Update DB directly without fetching the entire object over the network.
        stmt = update(Message).where(Message.id == message_id).values(
            sentiment=sentiment,
            classification=classification,
            is_analyzed=True
        )
        result = session.execute(stmt)

        if result.rowcount == 0:
            return {"status": "error", "reason": "Message deleted during analysis"}

        # Extract structured action items if engine supports it
        if hasattr(ai_engine, "extract_action_items_sync"):
            tasks_data = ai_engine.extract_action_items_sync(content, sender_name=sender_name)
            for t in tasks_data:
                task_item = ActionItem(
                    id=str(uuid.uuid4()),
                    group_id=group_id,
                    source_message_id=message_id,
                    title=t["title"],
                    description=None,
                    assignee=t.get("assignee"),
                    assignee_id=sender_id if t.get("assignee") == sender_name else None,
                    urgency=t.get("urgency", "medium"),
                    status="todo"
                )
                session.add(task_item)

        # Detect critical incident alerts if engine supports it
        if hasattr(ai_engine, "detect_incident_alert_sync"):
            incident = ai_engine.detect_incident_alert_sync(content, sender_name=sender_name)
            if incident:
                alert_item = Alert(
                    id=str(uuid.uuid4()),
                    group_id=group_id,
                    source_message_id=message_id,
                    severity=incident["severity"],
                    alert_type=incident["alert_type"],
                    title=incident["title"],
                    description=incident["description"],
                    status="active"
                )
                session.add(alert_item)
        
        # Store message in ChromaDB for semantic search BEFORE committing DB.
        metadata = {
            "group_id": group_id,
            "sender_id": sender_id,
            "sentiment": sentiment,
            "classification": classification
        }

        try:
            store_message_embedding(message_id, content, metadata)
        except Exception as e:
            session.rollback()
            logging.error(f"Failed to store embedding for {message_id}: {e}")
            raise e

        session.commit()

        return {"status": "success", "message_id": message_id}
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
