from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

class MessageIngest(BaseModel):
    message_id: str = Field(..., max_length=255)
    group_id: str = Field(..., max_length=255)
    group_name: str = Field(..., max_length=255)
    sender_id: str = Field(..., max_length=255)
    sender_name: str = Field(..., max_length=255)
    content: str = Field(..., max_length=65536)
    timestamp: int = Field(..., ge=0, le=4102444800)
    is_media: bool
    quoted_msg_id: Optional[str] = Field(None, max_length=255)

class MessageResponse(BaseModel):
    id: str
    content: str
    sentiment: Optional[str]
    classification: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)
