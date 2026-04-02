from pydantic import BaseModel, ConfigDict
from typing import Optional

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

class MessageResponse(BaseModel):
    id: str
    content: str
    sentiment: Optional[str]
    classification: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)
