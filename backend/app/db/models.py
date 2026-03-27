from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from .database import Base

class Group(Base):
    __tablename__ = "groups"

    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    is_bot = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, index=True)
    group_id = Column(String, ForeignKey("groups.id"), index=True)
    sender_id = Column(String, ForeignKey("users.id"), index=True)
    content = Column(Text)
    timestamp = Column(DateTime(timezone=True), index=True)
    is_media = Column(Boolean, default=False)
    quoted_msg_id = Column(String, nullable=True)
    
    # AI Enrichment fields
    is_analyzed = Column(Boolean, default=False)
    sentiment = Column(String, nullable=True) # positive, negative, neutral
    classification = Column(String, nullable=True) # question, task, announcement, discussion
    topics = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
