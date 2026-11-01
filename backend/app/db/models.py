from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from .database import Base

class Group(Base):
    __tablename__ = "groups"

    id = Column(String, primary_key=True)
    name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

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
    classification = Column(String, nullable=True) # question, task, announcement, discussion, decision
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_messages_group_id_timestamp", "group_id", "timestamp"),
    )

class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(String, primary_key=True)
    group_id = Column(String, ForeignKey("groups.id"), index=True, nullable=False)
    source_message_id = Column(String, ForeignKey("messages.id"), nullable=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    assignee = Column(String, nullable=True)
    assignee_id = Column(String, nullable=True)
    urgency = Column(String, default="medium") # high, medium, low
    status = Column(String, default="todo", index=True) # todo, in_progress, done, dismissed
    due_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_action_items_group_status", "group_id", "status"),
    )

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String, primary_key=True)
    group_id = Column(String, ForeignKey("groups.id"), index=True, nullable=False)
    source_message_id = Column(String, ForeignKey("messages.id"), nullable=True)
    severity = Column(String, default="warning", index=True) # critical, warning, info
    alert_type = Column(String, default="incident") # outage, sentiment_surge, security_leak, escalation, incident
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String, default="active", index=True) # active, acknowledged, resolved
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_alerts_group_status", "group_id", "status"),
    )
