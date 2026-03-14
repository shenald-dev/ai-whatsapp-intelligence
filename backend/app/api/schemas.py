from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List

class MessageIngest(BaseModel):
    message_id: str
    group_id: str
    group_name: str
    sender_id: str
    sender_name: str
    content: str
    timestamp: int
    is_media: bool
    quoted_msg_id: Optional[str] = None

class AnalysisQuery(BaseModel):
    group_id: str
    days: int = 7

class SummaryResponse(BaseModel):
    id: int
    group_id: str
    period: str
    content: str
    key_decisions: List[str]
    tasks: List[str]
    
    model_config = ConfigDict(from_attributes=True)

class MessageResponse(BaseModel):
    id: str
    content: str
    sentiment: Optional[str]
    classification: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)
