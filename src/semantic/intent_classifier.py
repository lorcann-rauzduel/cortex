"""
Intent Classifier - Semantic Understanding Layer
Separates "thinking" (intent) from "acting" (coordination)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from enum import Enum
import logging

from .llm_client import LLMClient, LLMConfig, MockIntentClassifier

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    CREATE = "CREATE"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    QUERY = "QUERY"
    CANCEL = "CANCEL"
    ESCALATE = "ESCALATE"
    NOTIFY = "NOTIFY"
    UNKNOWN = "UNKNOWN"


@dataclass
class SemanticResult:
    intent: IntentType
    topics: List[str]
    entities: Dict[str, Any]
    confidence: float
    raw_reasoning: str
    session_id: Optional[str] = None
    use_mock: bool = False

    def to_context(self) -> Dict[str, Any]:
        """Convert to context dict for rule engine"""
        return {
            "intent": self.intent.value if isinstance(self.intent, IntentType) else self.intent,
            "topics": self.topics,
            "entities": self.entities,
            "confidence": self.confidence,
        }


class IntentClassifier:
    """
    Semantic understanding layer using LLM for intent extraction.
    
    This is the "THINKING" part of Cortex:
    - Understands user intention via LLM
    - Does NOT make coordination decisions
    - Outputs structured semantic context for rule engine
    """

    def __init__(
        self,
        use_llm: bool = True,
        llm_config: Optional[Dict] = None
    ):
        self.use_llm = use_llm
        self.llm_config = llm_config
        self.llm_client = LLMClient(llm_config)
        self.mock_classifier = MockIntentClassifier()
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize the classifier"""
        if self.use_llm:
            success = self.llm_client.initialize()
            if success:
                self._initialized = True
                logger.info("IntentClassifier initialized with Ollama")
                return True
        
        logger.info("IntentClassifier initialized with mock classifier")
        self._initialized = True
        return True

    def classify(self, message: str, context: Optional[Dict[str, Any]] = None) -> SemanticResult:
        """Classify user message into structured semantic result."""
        logger.debug(f"Classifying: {message[:50]}...")
        
        if self.use_llm and self.llm_client.is_initialized:
            raw = self.llm_client.extract_intent(message, context)
        else:
            raw = self.mock_classifier.classify(message)
        
        intent_str = raw.get("intent", "UNKNOWN")
        try:
            intent = IntentType(intent_str)
        except ValueError:
            intent = IntentType.UNKNOWN
        
        result = SemanticResult(
            intent=intent,
            topics=raw.get("topics", []),
            entities=raw.get("entities", {}),
            confidence=raw.get("confidence", 0.0),
            raw_reasoning=raw.get("raw_reasoning", ""),
            use_mock=not self.llm_client.is_initialized
        )
        
        logger.info(f"Classification: {result.intent}, topics={result.topics}, mock={result.use_mock}")
        return result

    def batch_classify(self, messages: List[str]) -> List[SemanticResult]:
        """Classify multiple messages"""
        return [self.classify(msg) for msg in messages]

    @property
    def is_llm_mode(self) -> bool:
        return self.llm_client.is_initialized
