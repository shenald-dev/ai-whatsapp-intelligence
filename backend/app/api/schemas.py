from pydantic import BaseModel, Field
from typing import Optional, List, Dict

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

class GroupResponse(BaseModel):
    id: str
    name: str

class MessageResponse(BaseModel):
    id: str
    content: str
    sentiment: Optional[str]
    classification: Optional[str]

# --- Next-Gen Semantic Search & RAG Schemas ---

class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="Natural language search query")
    group_id: Optional[str] = Field(None, description="Filter results to a specific WhatsApp group")
    limit: int = Field(10, ge=1, le=50, description="Maximum number of semantic results")
    min_similarity: float = Field(0.0, ge=0.0, le=1.0, description="Minimum cosine similarity threshold")
    classification: Optional[str] = Field(None, description="Filter by classification (task, decision, question, etc.)")
    sentiment: Optional[str] = Field(None, description="Filter by sentiment (positive, neutral, negative)")

class SearchResultItem(BaseModel):
    message_id: str
    content: str
    group_id: Optional[str] = None
    group_name: Optional[str] = None
    sender_id: Optional[str] = None
    sender_name: Optional[str] = None
    timestamp: Optional[str] = None
    sentiment: Optional[str] = None
    classification: Optional[str] = None
    similarity: float

class SemanticSearchResponse(BaseModel):
    query: str
    total_found: int
    results: List[SearchResultItem]

class AskAIRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=2000, description="Natural language inquiry over group history")
    group_id: Optional[str] = Field(None, description="Target group ID (optional)")
    time_window_hours: Optional[int] = Field(None, ge=1, le=720, description="Lookback window in hours (up to 30 days)")

class CitationItem(BaseModel):
    message_id: str
    sender_name: str
    timestamp: str
    snippet: str

class AskAIResponse(BaseModel):
    question: str
    answer: str
    confidence: float
    citations: List[CitationItem]
    key_topics: List[str]
    relevant_messages_count: int

# --- Executive Intelligence Briefing Schemas ---

class ActionItem(BaseModel):
    task: str
    assignee: Optional[str] = None
    urgency: str = "medium"
    source_message_id: Optional[str] = None

class DecisionItem(BaseModel):
    decision: str
    decider: Optional[str] = None
    source_message_id: Optional[str] = None

class QuestionItem(BaseModel):
    question: str
    asker: Optional[str] = None
    source_message_id: Optional[str] = None

class ExecutiveBriefingResponse(BaseModel):
    group_id: str
    group_name: str
    time_window_hours: int
    total_messages_analyzed: int
    executive_summary: str
    key_decisions: List[DecisionItem]
    action_items: List[ActionItem]
    open_questions: List[QuestionItem]
    sentiment_breakdown: Dict[str, int]
