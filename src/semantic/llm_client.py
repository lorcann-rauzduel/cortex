"""
LLM Client for semantic understanding
Supports Ollama (OpenAI-compatible API) or llama-cpp-python
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json
import logging
import os
import re
import httpx

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    provider: str = "ollama"
    model: str = "llama3.2"
    ollama_url: str = "http://localhost:11434"
    temperature: float = 0.3
    max_tokens: int = 256


class LLMClient:
    """
    LLM Client supporting Ollama (default) or llama-cpp-python.
    """

    INTENT_PROMPT = """Tu es un classificateur d'intentions. Réponds UNIQUEMENT avec du JSON valide, rien d'autre.

Intents valides: CREATE, APPROVE, REJECT, QUERY, CANCEL, ESCALATE, NOTIFY
Topics valides: task, approval, report, notification, general

Réponds STRICTEMENT avec ce format JSON (et rien d'autre):
{{"intent":"XXX","topics":["xxx"],"entities":{{"key":"value"}},"confidence":0.9}}

Message: {message}
"""

    def __init__(self, config: Optional[Dict] = None):
        if config:
            self.config = LLMConfig(**config) if isinstance(config, dict) else config
        else:
            self.config = LLMConfig()
        self._initialized = False

    def initialize(self) -> bool:
        """Check Ollama availability"""
        if self.config.provider == "ollama":
            try:
                with httpx.Client() as client:
                    resp = client.get(f"{self.config.ollama_url}/api/tags", timeout=3)
                    if resp.status_code == 200:
                        models = resp.json().get("models", [])
                        logger.info(f"Ollama available. Models: {[m['name'] for m in models]}")
                        self._initialized = True
                        return True
            except Exception as e:
                logger.warning(f"Ollama not available: {e}. Using mock mode.")
        
        self._initialized = False
        return False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def extract_intent(self, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Extract intent from message using LLM"""
        if not self._initialized:
            return self._mock_intent_extraction(message)

        prompt = self.INTENT_PROMPT.format(message=message)
        
        try:
            with httpx.Client(timeout=120) as client:
                resp = client.post(
                    f"{self.config.ollama_url}/api/generate",
                    json={
                        "model": self.config.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": self.config.temperature,
                            "num_predict": self.config.max_tokens,
                        }
                    }
                )
                resp.raise_for_status()
                result = resp.json()
                text = result.get("response", "").strip()
                
                import re
                match = re.search(r'\{[^{}]*"intent"[^{}]*\}', text, re.DOTALL)
                if match:
                    try:
                        parsed = json.loads(match.group())
                        parsed['raw_reasoning'] = text
                        return parsed
                    except json.JSONDecodeError:
                        pass
                
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if match:
                    try:
                        parsed = json.loads(match.group())
                        if 'intent' in parsed:
                            parsed['raw_reasoning'] = text
                            return parsed
                    except json.JSONDecodeError:
                        pass
                
                logger.warning(f"Could not parse JSON from Ollama. Response: {text[:200]}")
                return self._mock_intent_extraction(message)
                
        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
            return self._mock_intent_extraction(message)

    def _mock_intent_extraction(self, message: str) -> Dict[str, Any]:
        """Mock intent extraction for development"""
        message_lower = message.lower()
        
        intent = "QUERY"
        topics = []
        entities = {}
        
        if any(kw in message_lower for kw in ["approuv", "approve", "approuver", "valider"]):
            intent = "APPROVE"
            topics.append("approval")
        elif any(kw in message_lower for kw in ["rejet", "reject", "rejeter", "refuser"]):
            intent = "REJECT"
            topics.append("approval")
        elif any(kw in message_lower for kw in ["cré", "creer", "créer", "create", "nouveau", "nouvelle"]):
            intent = "CREATE"
            topics.append("task")
        elif any(kw in message_lower for kw in ["annul", "cancel", "annuler"]):
            intent = "CANCEL"
            topics.append("task")
        elif any(kw in message_lower for kw in ["escalad", "escalate"]):
            intent = "ESCALATE"
        elif any(kw in message_lower for kw in ["notify", "notifi", "envoyer"]):
            intent = "NOTIFY"
        else:
            topics.append("general")
        
        ids = re.findall(r'(?:T-|ID-|#)\d+', message, re.IGNORECASE)
        if ids:
            entities['task_ids'] = ids
        
        return {
            "intent": intent,
            "topics": topics or ["general"],
            "entities": entities,
            "confidence": 0.7,
            "raw_reasoning": "[MOCK MODE]"
        }


class MockIntentClassifier:
    """Keyword-based classifier for testing"""
    
    KEYWORDS = {
        "APPROVE": ["approuv", "approve", "approuver", "valider"],
        "REJECT": ["rejet", "reject", "rejeter", "refuser"],
        "CANCEL": ["annul", "cancel", "annuler"],
        "CREATE": ["cré", "créer", "create", "nouveau", "nouvelle"],
        "ESCALATE": ["escalad", "escalate", "escalader"],
        "NOTIFY": ["notify", "notifi", "envoyer", "message"],
    }
    
    TOPICS = {
        "task": ["tâche", "tache", "task", "job"],
        "approval": ["approbat", "approuv", "valid"],
        "report": ["rapport", "report"],
    }

    def classify(self, message: str) -> Dict[str, Any]:
        msg_lower = message.lower()
        
        intent = "QUERY"
        for value, kws in self.KEYWORDS.items():
            if any(kw in msg_lower for kw in kws):
                intent = value
                break
        
        topics = [t for t, kws in self.TOPICS.items() if any(kw in msg_lower for kw in kws)] or ["general"]
        
        entities = {}
        ids = re.findall(r'(?:T-|ID-|#)\d+', message)
        if ids:
            entities['ids'] = ids
        
        return {
            "intent": intent,
            "topics": topics,
            "entities": entities,
            "confidence": 0.8,
            "raw_reasoning": f"Mock: {intent}"
        }
