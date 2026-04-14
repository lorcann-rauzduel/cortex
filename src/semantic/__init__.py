from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


class IntentType(str, Enum):
    CREATE = "CREATE"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    QUERY = "QUERY"
    CANCEL = "CANCEL"
    ESCALATE = "ESCALATE"
    NOTIFY = "NOTIFY"
    UNKNOWN = "UNKNOWN"


class AgentRole(str, Enum):
    MANAGER = "MANAGER"
    WORKER = "WORKER"
    CONSULTANT = "CONSULTANT"
    SUPERVISOR = "SUPERVISOR"


@dataclass
class SemanticResult:
    intent: IntentType
    topics: List[str]
    entities: Dict[str, Any]
    confidence: float
    raw_reasoning: str
    session_id: Optional[str] = None


@dataclass
class WorkflowState:
    workflow_id: str
    current_places: set
    tokens: Dict[str, Any]
    history: List[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class TransitionResult:
    success: bool
    new_places: set
    new_tokens: Dict[str, Any]
    fired_transition: str
    error: Optional[str] = None
