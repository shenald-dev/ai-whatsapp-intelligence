from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import logging

from ..db.models import Message
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
    """Celery task worker to enrich a message with AI."""
    session = SessionLocal()
    try:
        msg = session.get(Message, message_id)
        if not msg or msg.is_analyzed or not msg.content:
            return {"status": "skipped", "reason": "Not found, analyzed, or empty"}

        # Extract needed fields before committing to prevent lazy loading
        content = msg.content
        group_id = msg.group_id
        sender_id = msg.sender_id

        # Release the database connection back to the pool before blocking on the network call
        session.commit()

        # Run AI analysis (async block within sync celery task)
        analysis = ai_engine.analyze_message_sync(content)
        sentiment = analysis.get("sentiment")
        classification = analysis.get("classification")

        # Update DB directly without fetching the potentially large Message payload
        stmt = (
            update(Message)
            .where(Message.id == message_id)
            .values(
                sentiment=sentiment,
                classification=classification,
                is_analyzed=True
            )
        )
        result = session.execute(stmt)
        if result.rowcount == 0:
            return {"status": "error", "reason": "Message deleted during analysis"}

        # Store message in ChromaDB for semantic search
        metadata = {
            "group_id": group_id,
            "sender_id": sender_id,
            "sentiment": sentiment,
            "classification": classification
        }

        # Commit early to release DB lock before network I/O
        session.commit()

        # Store the embedding
        store_message_embedding(message_id, content, metadata)

        return {"status": "success", "message_id": message_id}
        
    except Exception as e:
        # Revert analysis state so the task can be safely retried
        logging.error(f"Failed to store embedding for {message_id}: {e}")
        # Revert the analysis using an UPDATE statement without fetching the object
        stmt = (
            update(Message)
            .where(Message.id == message_id)
            .values(
                sentiment=None,
                classification=None,
                is_analyzed=False
            )
        )
        result = session.execute(stmt)
        if result.rowcount == 0:
            # Log if the message was deleted during the task execution
            logging.warning(f"Message {message_id} not found during rollback")
        session.commit()
        raise e
    finally:
        session.close()