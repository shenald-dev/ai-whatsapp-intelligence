import asyncio
import os
import uuid
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db import models
from app.ai.engine import ai_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is missing.")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

GROUPS = [
    {"id": "dev_core", "name": "Engineering Core"},
    {"id": "product_sync", "name": "Product Sync"},
    {"id": "marketing", "name": "Marketing Strategy Q3"}
]

USERS = [
    {"id": "u1", "name": "Sarah Jenkins"},
    {"id": "u2", "name": "Alex Rivera"},
    {"id": "u3", "name": "John Doe"},
    {"id": "u4", "name": "Maria Garcia"}
]

MESSAGES = [
    "We need to finalize the API docs by Friday.",
    "Did anyone check the recent downtime alert?",
    "Great work on the new dashboard guys, looks amazing!",
    "Are we still on track for the Q3 feature freeze?",
    "Can someone review PR #402?",
    "I'll handle the database migration tomorrow morning.",
    "User engagement is up 15% since the new update.",
    "Wait, is the staging environment down again?",
    "Let's schedule a 15-min sync to discuss the authentication flow.",
    "The new marketing assets are ready for review."
]

async def seed_db():
    async with engine.begin() as conn:
        print("Creating tables...")
        await conn.run_sync(models.Base.metadata.drop_all)
        await conn.run_sync(models.Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        print("Seeding Groups & Users...")
        for g in GROUPS:
            session.add(models.Group(id=g["id"], name=g["name"]))
        for u in USERS:
            session.add(models.User(id=u["id"], name=u["name"]))
            
        await session.commit()

        print("Seeding Messages & running AI pipeline...")
        now = datetime.now()
        
        # Prepare all messages and analysis tasks
        messages = []
        analysis_tasks = []

        for i in range(20):
            group = random.choice(GROUPS)
            user = random.choice(USERS)
            content = random.choice(MESSAGES)
            
            # Stagger timestamps
            ts = now - timedelta(hours=random.randint(1, 48), minutes=random.randint(0, 60))
            
            msg = models.Message(
                id=str(uuid.uuid4()),
                group_id=group["id"],
                sender_id=user["id"],
                content=content,
                timestamp=ts,
                is_media=False,
                is_analyzed=True
            )
            
            messages.append(msg)
            analysis_tasks.append(ai_engine.analyze_message(content))

        # Execute all AI analysis concurrently
        analyses = await asyncio.gather(*analysis_tasks)

        # Update messages with analysis results and add to session
        for msg, analysis in zip(messages, analyses):
            msg.sentiment = analysis.get("sentiment", "neutral")
            msg.classification = analysis.get("classification", "discussion")
            msg.topics = analysis.get("topics", [])
            session.add(msg)
            
        await session.commit()
        print("✅ Database successfully seeded with AI intelligence!")

if __name__ == "__main__":
    asyncio.run(seed_db())
