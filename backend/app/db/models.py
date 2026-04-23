from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from .database import Base

class Group(Base):
    __tablename__ = "groups"

    id = Column(String, primary_key=True)
    name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True)
    group_id = Column(String, ForeignKey("groups.id"))
    sender_id = Column(String, ForeignKey("users.id"), index=True)
    content = Column(Text)
    timestamp = Column(DateTime(timezone=True))
    is_media = Column(Boolean, default=False)
    quoted_msg_id = Column(String, nullable=True)
    
    # AI Enrichment fields
    is_analyzed = Column(Boolean, default=False)
    sentiment = Column(String, nullable=True) # positive, negative, neutral
    classification = Column(String, nullable=True) # question, task, announcement, discussion
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_messages_group_id_timestamp", "group_id", "timestamp"),
    )
