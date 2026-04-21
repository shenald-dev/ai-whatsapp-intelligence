import os
import logging
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Setup LangChain to use OpenRouter (or fallback to OpenAI)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
BASE_URL = "https://openrouter.ai/api/v1"

class MessageAnalysis(BaseModel):
    sentiment: str = Field(description="The sentiment of the message: positive, negative, or neutral")
    classification: str = Field(description="One of: question, task, announcement, discussion, or other")

class AIEngine:
    def __init__(self):
        # We prefer a fast, cheap model for per-message analysis like Haiku or a specific OpenRouter model.
        # If no openrouter key, fallback to local or mocked for testing.
        if OPENROUTER_API_KEY:
            self.llm = ChatOpenAI(
                openai_api_key=OPENROUTER_API_KEY,
                openai_api_base=BASE_URL,
                model_name="anthropic/claude-3-haiku:beta", # Fast & cheap on OpenRouter
                temperature=0.1
            )
        else:
            self.llm = None # Handled gracefully in analyze()

        self.parser = PydanticOutputParser(pydantic_object=MessageAnalysis)

        self.prompt = PromptTemplate(
            template="Analyze the following WhatsApp group message.\n{format_instructions}\n\nMessage: '{message}'\n",
            input_variables=["message"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )

        self.chain = self.prompt | self.llm | self.parser if self.llm else None


    def analyze_message_sync(self, content: str) -> dict:
        """Runs the message through the LLM to extract metadata (synchronous)."""
        if not content.strip() or len(content) < 5:
            return {"sentiment": "neutral", "classification": "other"}

        if not self.llm:
            # Mock mode if no API key
            return {
                "sentiment": "neutral",
                "classification": "discussion"
            }

        try:
            result: MessageAnalysis = self.chain.invoke({"message": content})
            return result.model_dump()
        except Exception as e:
            logger.error(f"AI Analysis Error: {e}")
            raise

# Singleton
ai_engine = AIEngine()
