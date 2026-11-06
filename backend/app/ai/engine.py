import os
import logging
from typing import Literal, List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

class MessageAnalysis(BaseModel):
    sentiment: Literal["positive", "negative", "neutral"] = Field(
        description="The sentiment of the message"
    )
    classification: Literal["question", "task", "decision", "announcement", "discussion", "other"] = Field(
        description="The classification of the message"
    )

    @field_validator("sentiment", "classification", mode="before")
    @classmethod
    def lowercase_values(_cls, v: str) -> str:
        if isinstance(v, str):
            return v.lower().strip()
        return v

class QAResponseSchema(BaseModel):
    answer: str = Field(description="Direct, comprehensive answer grounded in the conversation history")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    key_topics: List[str] = Field(default_factory=list, description="Key topics identified in context")

class BriefingSchema(BaseModel):
    executive_summary: str = Field(description="High-level narrative summary of group activities and discussions")
    key_decisions: List[str] = Field(default_factory=list, description="List of notable decisions made")
    action_items: List[str] = Field(default_factory=list, description="List of tasks and action items identified")
    open_questions: List[str] = Field(default_factory=list, description="Unanswered or pending questions")

class AIEngine:
    def __init__(self):
        # Support OpenRouter, standard OpenAI, or local Ollama instances
        api_key = OPENROUTER_API_KEY or OPENAI_API_KEY
        if api_key:
            model_name = "anthropic/claude-3-haiku:beta" if OPENROUTER_API_KEY else "gpt-4o-mini"
            base_url = BASE_URL if OPENROUTER_API_KEY else None
            kwargs = {
                "openai_api_key": api_key,
                "model_name": model_name,
                "temperature": 0.1,
                "timeout": 15.0,
                "max_retries": 3
            }
            if base_url:
                kwargs["openai_api_base"] = base_url
            self.llm = ChatOpenAI(**kwargs)
            self.provider = "OpenRouter" if OPENROUTER_API_KEY else "OpenAI"
        elif OLLAMA_BASE_URL:
            self.llm = ChatOpenAI(
                openai_api_base=OLLAMA_BASE_URL,
                openai_api_key="ollama",
                model_name=OLLAMA_MODEL,
                temperature=0.1,
                timeout=20.0,
                max_retries=3
            )
            self.provider = f"Ollama ({OLLAMA_MODEL})"
        else:
            self.llm = None
            self.provider = "Local Heuristic Synthesis Engine"

        # Message Classifier Chain
        self.parser = PydanticOutputParser(pydantic_object=MessageAnalysis)
        self.prompt = PromptTemplate(
            template="Analyze the following WhatsApp group message.\n{format_instructions}\n\nMessage: '{message}'\n",
            input_variables=["message"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )
        self.chain = self.prompt | self.llm | self.parser if self.llm else None

        # Q&A Synthesizer Chain
        self.qa_parser = PydanticOutputParser(pydantic_object=QAResponseSchema)
        self.qa_prompt = PromptTemplate(
            template=(
                "You are an AI intelligence assistant analyzing WhatsApp group chats.\n"
                "Answer the user's question based strictly on the provided conversation messages.\n"
                "{format_instructions}\n\n"
                "Conversation Context:\n{context}\n\n"
                "User Question: {question}\n"
            ),
            input_variables=["context", "question"],
            partial_variables={"format_instructions": self.qa_parser.get_format_instructions()},
        )
        self.qa_chain = self.qa_prompt | self.llm | self.qa_parser if self.llm else None

        # Briefing Generator Chain
        self.briefing_parser = PydanticOutputParser(pydantic_object=BriefingSchema)
        self.briefing_prompt = PromptTemplate(
            template=(
                "You are an AI intelligence assistant summarizing team communication.\n"
                "Generate an executive briefing from the following group messages.\n"
                "{format_instructions}\n\n"
                "Group: {group_name}\n"
                "Messages:\n{messages_text}\n"
            ),
            input_variables=["group_name", "messages_text"],
            partial_variables={"format_instructions": self.briefing_parser.get_format_instructions()},
        )
        self.briefing_chain = self.briefing_prompt | self.llm | self.briefing_parser if self.llm else None

    def analyze_message_sync(self, content: str) -> dict:
        """Runs the message through the LLM to extract metadata (synchronous)."""
        if not content.strip() or len(content) < 5:
            return {"sentiment": "neutral", "classification": "other"}

        if not self.llm:
            # Contextual heuristic when offline or without external API keys
            content_lower = content.lower()
            sentiment = "neutral"
            if any(w in content_lower for w in ["great", "amazing", "awesome", "perfect", "good", "thanks", "done", "fixed"]):
                sentiment = "positive"
            elif any(w in content_lower for w in ["downtime", "broken", "failed", "error", "down", "bug", "issue", "blocked", "crash", "outage"]):
                sentiment = "negative"

            classification = "discussion"
            if "?" in content or any(w in content_lower for w in ["why", "how", "when", "who", "what", "is anyone", "can someone"]):
                classification = "question"
            elif any(w in content_lower for w in ["todo", "i'll handle", "will do", "need to", "must", "action item", "please review", "assign", "finalize"]):
                classification = "task"
            elif any(w in content_lower for w in ["we decided", "decision:", "agreed", "finalized", "let's go with", "approved"]):
                classification = "decision"
            elif any(w in content_lower for w in ["announcement", "fyi", "heads up", "all-hands", "reminder", "psa"]):
                classification = "announcement"

            return {
                "sentiment": sentiment,
                "classification": classification
            }

        try:
            result: MessageAnalysis = self.chain.invoke({"message": content})
            return result.model_dump()
        except Exception as e:
            logger.error(f"AI Analysis Error: {e}")
            raise

    def extract_action_items_sync(self, content: str, sender_name: str = "Team Member") -> List[Dict[str, Any]]:
        """
        Extracts structured action items from a message.
        Returns a list of dicts: {'title': str, 'assignee': str, 'urgency': str, 'due_date_str': Optional[str]}
        """
        if not content.strip() or len(content) < 8:
            return []

        content_lower = content.lower()
        is_actionable = any(kw in content_lower for kw in [
            "todo", "i'll handle", "will handle", "will do", "need to", "must", "action item",
            "please review", "assign", "finalize", "let's fix", "working on", "scheduled"
        ])
        if not is_actionable:
            return []

        # Determine urgency
        urgency = "medium"
        if any(w in content_lower for w in ["urgent", "asap", "critical", "p0", "immediately", "blocker", "today"]):
            urgency = "high"
        elif any(w in content_lower for w in ["low priority", "backlog", "eventually", "whenever", "nice to have"]):
            urgency = "low"

        # Determine assignee
        assignee = sender_name
        if "assign to @" in content_lower:
            parts = content.split("assign to @")
            if len(parts) > 1:
                assignee = parts[1].split()[0].strip()
        elif "please review" in content_lower and sender_name:
            assignee = None  # open review request for team

        # Clean title
        title = content.strip()
        if len(title) > 140:
            title = title[:137] + "..."

        return [{
            "title": title,
            "assignee": assignee,
            "urgency": urgency,
            "due_date_str": "by Friday" if "by friday" in content_lower else ("tomorrow" if "tomorrow" in content_lower else None)
        }]

    def detect_incident_alert_sync(self, content: str, sender_name: str = "Team Member") -> Optional[Dict[str, Any]]:
        """
        Detects outages, severe security issues, or critical production emergencies.
        Returns None if normal message, or a dict with alert fields.
        """
        if not content.strip():
            return None

        content_lower = content.lower()

        # 1. Outage / Service Disruption Check
        outage_keywords = [
            "production is down", "production down", "prod is down", "staging is down",
            "downtime alert", "server crash", "database crash", "500 error spike",
            "database down", "server down", "outage"
        ]
        if any(kw in content_lower for kw in outage_keywords):
            return {
                "severity": "critical",
                "alert_type": "outage",
                "title": f"Service Outage Flagged by {sender_name}",
                "description": content.strip()
            }

        # 2. Security / Data Exposure Check
        security_keywords = ["api key exposed", "credentials leak", "security breach", "unauthorized access", "token leaked", "data exposure"]
        if any(kw in content_lower for kw in security_keywords):
            return {
                "severity": "critical",
                "alert_type": "security_leak",
                "title": f"Security Exposure Warning from {sender_name}",
                "description": content.strip()
            }

        # 3. Critical Blockers / Urgent Escalation
        escalation_keywords = ["critical blocker", "emergency escalation", "p0 incident", "urgent escalation"]
        if any(kw in content_lower for kw in escalation_keywords):
            return {
                "severity": "warning",
                "alert_type": "escalation",
                "title": f"Critical Escalation by {sender_name}",
                "description": content.strip()
            }

        return None

    def answer_question_sync(self, question: str, context_messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Synthesizes an answer to a question given retrieved message contexts."""
        if not context_messages:
            return {
                "answer": "No relevant messages were found in the chat history matching your inquiry.",
                "confidence": 0.0,
                "citations": [],
                "key_topics": []
            }

        # Build citations
        citations = []
        context_lines = []
        for idx, m in enumerate(context_messages):
            sender = m.get("sender_name") or m.get("sender_id") or "Unknown"
            ts = m.get("timestamp") or ""
            content = m.get("content", "")
            msg_id = m.get("message_id") or m.get("id") or f"ref_{idx}"
            citations.append({
                "message_id": msg_id,
                "sender_name": sender,
                "timestamp": str(ts),
                "snippet": content[:160]
            })
            context_lines.append(f"[{sender} at {ts}]: {content}")

        context_text = "\n".join(context_lines)

        if not self.llm:
            # Deterministic synthesis fallback
            matched_snippets = [f"\"{c['snippet']}\" (by {c['sender_name']})" for c in citations[:3]]
            summary = (
                "Based on the conversation history, the following discussions directly address this: "
                + "; ".join(matched_snippets) + "."
            )
            return {
                "answer": summary,
                "confidence": 0.85,
                "citations": citations,
                "key_topics": ["team sync", "chat context"]
            }

        try:
            res: QAResponseSchema = self.qa_chain.invoke({
                "context": context_text,
                "question": question
            })
            return {
                "answer": res.answer,
                "confidence": round(float(res.confidence), 2),
                "citations": citations,
                "key_topics": res.key_topics
            }
        except Exception as e:
            logger.error(f"RAG Q&A Synthesis Error: {e}")
            return {
                "answer": f"Identified {len(citations)} relevant discussions regarding '{question}'. Most relevant note from {citations[0]['sender_name']}: '{citations[0]['snippet']}'",
                "confidence": 0.70,
                "citations": citations,
                "key_topics": []
            }

    def generate_briefing_sync(self, group_name: str, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generates a structured executive intelligence briefing for a group."""
        if not messages:
            return {
                "executive_summary": f"No messages were recorded for '{group_name}' during this period.",
                "key_decisions": [],
                "action_items": [],
                "open_questions": [],
                "sentiment_summary": {"positive": 0, "neutral": 0, "negative": 0}
            }

        # Sentiment counting
        sentiments = {"positive": 0, "neutral": 0, "negative": 0}
        decisions = []
        tasks = []
        questions = []

        for m in messages:
            sent = m.get("sentiment", "neutral")
            sentiments[sent] = sentiments.get(sent, 0) + 1
            cls_type = m.get("classification")
            sender = m.get("sender_name") or m.get("sender_id") or "Unknown"
            content = m.get("content", "")
            msg_id = m.get("id") or m.get("message_id")

            if cls_type == "decision" or any(w in content.lower() for w in ["decided", "agreed", "finalized", "approved"]):
                decisions.append({
                    "decision": content,
                    "decider": sender,
                    "source_message_id": msg_id
                })
            elif cls_type == "task" or any(w in content.lower() for w in ["todo", "i'll handle", "need to", "will do", "assign"]):
                urgency = "high" if any(w in content.lower() for w in ["urgent", "asap", "critical", "freeze", "blocker", "today"]) else "medium"
                tasks.append({
                    "task": content,
                    "assignee": sender,
                    "urgency": urgency,
                    "source_message_id": msg_id
                })
            elif cls_type == "question" or "?" in content:
                questions.append({
                    "question": content,
                    "asker": sender,
                    "source_message_id": msg_id
                })

        # Format summary text
        if not self.llm:
            dominant_sentiment = max(sentiments, key=sentiments.get)
            exec_summary = (
                f"During this period, '{group_name}' recorded {len(messages)} messages with overall {dominant_sentiment} tone. "
                f"The team surfaced {len(tasks)} action items and reached {len(decisions)} key decisions. "
                f"{len(questions)} discussions or open questions were noted."
            )
            return {
                "executive_summary": exec_summary,
                "key_decisions": decisions[:10],
                "action_items": tasks[:10],
                "open_questions": questions[:10],
                "sentiment_summary": sentiments
            }

        try:
            formatted_msgs = "\n".join([f"[{m.get('sender_name', 'User')}]: {m.get('content', '')}" for m in messages[:50]])
            res: BriefingSchema = self.briefing_chain.invoke({
                "group_name": group_name,
                "messages_text": formatted_msgs
            })
            return {
                "executive_summary": res.executive_summary,
                "key_decisions": decisions[:10],
                "action_items": tasks[:10],
                "open_questions": questions[:10],
                "sentiment_summary": sentiments
            }
        except Exception as e:
            logger.error(f"Briefing Synthesis Error: {e}")
            return {
                "executive_summary": f"Team activity summary for {group_name}: {len(messages)} messages analyzed.",
                "key_decisions": decisions[:10],
                "action_items": tasks[:10],
                "open_questions": questions[:10],
                "sentiment_summary": sentiments
            }

# Singleton
ai_engine = AIEngine()
