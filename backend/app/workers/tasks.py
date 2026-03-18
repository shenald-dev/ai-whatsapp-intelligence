import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

from ..db.models import Message
from ..ai.engine import ai_engine

load_dotenv()

# Worker uses sync engine for simplicity within Celery
SYNC_DB_URL = os.getenv("SYNC_DATABASE_URL")
if not SYNC_DB_URL:
    raise ValueError("SYNC_DATABASE_URL environment variable is missing")

engine = create_engine(SYNC_DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def process_message(message_id: str):
    """Celery task worker to enrich a message with AI."""
    session = SessionLocal()
    try:
        msg = session.query(Message).filter(Message.id == message_id).first()
        if not msg or msg.is_analyzed or not msg.content:
            return {"status": "skipped", "reason": "Not found, analyzed, or empty"}

        # Run AI analysis (async block within sync celery task)
        loop = asyncio.get_event_loop()
        if loop.is_closed():
             loop = asyncio.new_event_loop()
             asyncio.set_event_loop(loop)
             
        analysis = loop.run_until_complete(ai_engine.analyze_message(msg.content))

        # Update DB
        msg.sentiment = analysis.get("sentiment")
        msg.classification = analysis.get("classification")
        msg.topics = analysis.get("topics", [])
        msg.is_analyzed = True
        
        session.commit()
        return {"status": "success", "message_id": message_id}
        
    except Exception as e:
        session.rollback()
        return {"status": "error", "error": str(e)}
    finally:
        session.close()
