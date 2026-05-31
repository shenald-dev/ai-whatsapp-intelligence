from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker, load_only
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
        msg = session.get(Message, message_id, options=[load_only(Message.content, Message.group_id, Message.sender_id, Message.is_analyzed)])
        if not msg or msg.is_analyzed or not msg.content:            return {"status": "skipped", "reason": "Not found, analyzed, or empty"}

        # Extract needed fields before committing
        content = row.content
        group_id = row.group_id
        sender_id = row.sender_id
        # Release the database connection back to the pool before blocking on the network call
        session.commit()

        # Run AI analysis (async block within sync celery task)
        analysis = ai_engine.analyze_message_sync(content)

        # Update DB using a direct SQL UPDATE statement
        # Use execution_options(synchronize_session='fetch') to ensure ORM events and identity map are updated
        stmt = (
            update(Message)
            .where(Message.id == message_id)
            .values(
                sentiment=analysis.get("sentiment"),
                classification=analysis.get("classification"),
                is_analyzed=True
            ).execution_options(synchronize_session="fetch")
        )
        res = session.execute(stmt)
        if res.rowcount == 0:
            return {"status": "error", "reason": "Message deleted during analysis"}

        # Explicitly expire the session to ensure subsequent accesses fetch the updated state
        session.expire_all()        
        # Store message in ChromaDB for semantic search
        metadata = {
            "group_id": group_id,
            "sender_id": sender_id,
            "sentiment": analysis.get("sentiment"),
            "classification": analysis.get("classification")        }

        # Commit early to release DB lock before network I/O
        session.commit()

        try:
            store_message_embedding(message_id, content, metadata)
        except Exception as e:
            # Revert analysis state so the task can be safely retried
            logging.error(f"Failed to store embedding for {message_id}: {e}")
            stmt_revert = (
                update(Message)
                .where(Message.id == message_id)
                .values(
                    is_analyzed=False,
                    sentiment=None,
                    classification=None
                ).execution_options(synchronize_session="fetch")
            )
            session.execute(stmt_revert)
            session.expire_all()            session.commit()
            raise e

        return {"status": "success", "message_id": message_id}
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
