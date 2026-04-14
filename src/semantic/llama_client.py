"""
Llama Client for semantic understanding
Wraps llama-cpp-python for intent extraction
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json
import logging
import os
import re

logger = logging.getLogger(__name__)


@dataclass
class LlamaConfig:
    model_path: str = "models/llama-3.2-3b-instruct-q4_k_m.gguf"
    n_ctx: int = 2048
    n_threads: int = 4
    temperature: float = 0.3
    max_tokens: int = 256


class LlamaClient:
    """
    Client for Llama-3.2 inference.
    Provides intent extraction and topic classification.
    """

    INTENT_PROMPT_TEMPLATE = """Tu es un classificateur d'intentions pour un système d'orchestration d'agents.

Analyse le message utilisateur et extray:
1. L'intention principale (CREATE, APPROVE, REJECT, QUERY, CANCEL, ESCALATE, NOTIFY)
2. Les topics pertinents (task, approval, notification, report, etc.)
3. Les entités mentionnées (IDs, noms, etc.)

Réponds STRICTEMENT en JSON:
{{
    "intent": "INTENTION",
    "topics": ["topic1", "topic2"],
    "entities": {{"key": "value"}},
    "confidence": 0.0-1.0,
    "reasoning": "explication courte"
}}

Message: {message}

JSON:"""

    def __init__(self, config: Optional[Dict] = None):
        if config:
            self.config = LlamaConfig(**config) if isinstance(config, dict) else config
        else:
            self.config = LlamaConfig()
        self._model = None
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize the Llama model"""
        try:
            from llama_cpp import Llama
            
            model_path = self.config.model_path
            
            if not os.path.exists(model_path):
                logger.warning(
                    f"Model not found at {model_path}. "
                    "Using mock mode for development."
                )
                self._initialized = False
                return False
            
            self._model = Llama(
                model_path=model_path,
                n_ctx=self.config.n_ctx,
                n_threads=self.config.n_threads,
                verbose=False
            )
            self._initialized = True
            logger.info(f"Llama model loaded: {model_path}")
            return True
            
        except ImportError:
            logger.warning("llama-cpp-python not installed. Using mock mode.")
            self._initialized = False
            return False
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self._initialized = False
            return False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def extract_intent(self, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Extract intent from user message.
        Returns structured semantic result.
        """
        if not self._initialized:
            return self._mock_intent_extraction(message)

        prompt = self.INTENT_PROMPT_TEMPLATE.format(message=message)
        
        try:
            response = self._model(
                prompt,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                stop=["```", "\n\n"]
            )
            
            raw_text = response['choices'][0]['text'].strip()
            
            json_start = raw_text.find('{')
            json_end = raw_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                result = json.loads(raw_text[json_start:json_end])
            else:
                logger.warning("Could not parse JSON from response")
                result = self._fallback_intent(message)
            
            result['raw_reasoning'] = raw_text
            return result
            
        except Exception as e:
            logger.error(f"Intent extraction failed: {e}")
            return self._fallback_intent(message)

    def _mock_intent_extraction(self, message: str) -> Dict[str, Any]:
        """Mock intent extraction for development without model"""
        message_lower = message.lower()
        
        intent = "QUERY"
        topics = []
        entities = {}
        confidence = 0.7
        
        if any(kw in message_lower for kw in ["approuv", "approve", "approuver", "valider", "validé"]):
            intent = "APPROVE"
            topics.append("approval")
        elif any(kw in message_lower for kw in ["rejet", "reject", "rejeter", "refuser"]):
            intent = "REJECT"
            topics.append("approval")
        elif any(kw in message_lower for kw in ["cré", "créer", "create", "nouveau", "nouvelle"]):
            intent = "CREATE"
            topics.append("task")
        elif any(kw in message_lower for kw in ["annul", "cancel", "annuler"]):
            intent = "CANCEL"
            topics.append("task")
        elif any(kw in message_lower for kw in ["escalad", "escalate", "escalader"]):
            intent = "ESCALATE"
            topics.append("escalation")
        elif any(kw in message_lower for kw in ["notify", "notifi", "envoyer", "message"]):
            intent = "NOTIFY"
            topics.append("notification")
        else:
            topics.append("general")
        
        id_pattern = r'(?:T-|ID-|#|TASK-)\d+'
        ids = re.findall(id_pattern, message, re.IGNORECASE)
        if ids:
            entities['task_ids'] = ids
        
        return {
            "intent": intent,
            "topics": topics,
            "entities": entities,
            "confidence": confidence,
            "raw_reasoning": "[MOCK MODE] Development simulation"
        }

    def _fallback_intent(self, message: str) -> Dict[str, Any]:
        """Fallback when model fails"""
        return {
            "intent": "QUERY",
            "topics": ["general"],
            "entities": {},
            "confidence": 0.3,
            "raw_reasoning": "Fallback due to extraction error"
        }


class MockIntentClassifier:
    """
    Mock classifier for testing without LLM.
    Uses keyword-based rules for intent classification.
    """

    KEYWORD_INTENTS = {
        "APPROVE": ["approuv", "approve", "approuver", "valider", "validé"],
        "REJECT": ["rejet", "reject", "rejeter", "refuser"],
        "CANCEL": ["annul", "cancel", "annuler"],
        "CREATE": ["cré", "créer", "create", "nouveau", "nouvelle"],
        "ESCALATE": ["escalad", "escalate", "escalader"],
        "NOTIFY": ["notify", "notifi", "envoyer", "message"],
    }

    TOPICS = {
        "task": ["tâche", "task", "job", "travail"],
        "approval": ["approbat", "approuv", "valid"],
        "report": ["rapport", "report", "bilan"],
        "user": ["utilisateur", "user", "employé"],
        "system": ["système", "system", "serveur"],
    }

    def classify(self, message: str) -> Dict[str, Any]:
        message_lower = message.lower()
        
        intent = "QUERY"
        
        for intent_value, keywords in self.KEYWORD_INTENTS.items():
            if any(kw in message_lower for kw in keywords):
                intent = intent_value
                break
        
        topics = []
        for topic, keywords in self.TOPICS.items():
            if any(kw in message_lower for kw in keywords):
                topics.append(topic)
        
        if not topics:
            topics = ["general"]
        
        entities = {}
        id_pattern = r'(?:T-|ID-|#)\d+'
        ids = re.findall(id_pattern, message)
        if ids:
            entities['ids'] = ids
        
        return {
            "intent": intent,
            "topics": topics,
            "entities": entities,
            "confidence": 0.8,
            "raw_reasoning": f"Mock classification: intent={intent}, topics={topics}"
        }
