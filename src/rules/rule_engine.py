"""
Neuro-symbolic Rule Engine for Cortex
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union
from enum import Enum
import yaml
import logging

logger = logging.getLogger(__name__)


class RuleAction(str, Enum):
    FIRE_TRANSITION = "fire_transition"
    GOTO_STATE = "goto_state"
    EMIT_TOKEN = "emit_token"
    NOTIFY = "notify"
    ESCALATE = "escalate"
    BLOCK = "block"


class AmbiguousIntentPolicy(str, Enum):
    FALLBACK = "fallback"
    CLARIFY = "clarify"
    SUSPEND = "suspend"


@dataclass
class RuleCondition:
    intent: Optional[str] = None
    topics: Optional[List[str]] = None
    entities: Optional[Dict[str, Any]] = None
    current_state: Optional[str] = None
    role: Optional[str] = None
    confidence_min: Optional[float] = None
    custom: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RuleCondition":
        return cls(
            intent=d.get("intent"),
            topics=d.get("topics"),
            entities=d.get("entities"),
            current_state=d.get("current_state"),
            role=d.get("role"),
            confidence_min=d.get("confidence_min"),
            custom=d.get("custom"),
        )

    def matches(self, context: Dict[str, Any]) -> bool:
        if self.intent and context.get("intent") != self.intent:
            return False
        if self.topics:
            context_topics = set(context.get("topics", []))
            if not any(t in context_topics for t in self.topics):
                return False
        if self.current_state and context.get("current_state") != self.current_state:
            return False
        if self.role and context.get("role") != self.role:
            return False
        if self.confidence_min and context.get("confidence", 1.0) < self.confidence_min:
            return False
        return True


@dataclass
class Rule:
    name: str
    description: str
    condition: RuleCondition
    action: RuleAction
    target: str
    priority: int = 0
    guard: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Rule":
        condition = d.get("condition", {})
        if isinstance(condition, dict):
            condition = RuleCondition.from_dict(condition)
        return cls(
            name=d["name"],
            description=d.get("description", ""),
            condition=condition,
            action=RuleAction(d["action"]) if isinstance(d["action"], str) else d["action"],
            target=d["target"],
            priority=d.get("priority", 0),
            guard=d.get("guard"),
        )

    def evaluate(self, context: Dict[str, Any]) -> bool:
        return self.condition.matches(context)


@dataclass
class RuleResult:
    rule: Rule
    action: RuleAction
    target: str
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntentContext:
    """Context for intent classification including session history"""
    message: str
    intent: str
    topics: List[str]
    entities: Dict[str, Any]
    confidence: float
    turn_history: List[str] = field(default_factory=list)
    
    @property
    def is_ambiguous(self) -> bool:
        return self.confidence < 0.6
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent,
            "topics": self.topics,
            "entities": self.entities,
            "confidence": self.confidence,
            "turn_history": self.turn_history,
            "is_ambiguous": self.is_ambiguous,
        }


class RuleEngine:
    """
    Neuro-symbolic rule engine with support for:
    - Confidence threshold handling
    - Ambiguous intent policies
    - Session context
    """

    def __init__(
        self,
        confidence_threshold: float = 0.6,
        ambiguous_policy: AmbiguousIntentPolicy = AmbiguousIntentPolicy.FALLBACK
    ):
        self._rules: List[Rule] = []
        self._guard_functions: Dict[str, Callable] = {}
        self._llm_guards: Dict[str, Dict] = {}
        self.confidence_threshold = confidence_threshold
        self.ambiguous_policy = ambiguous_policy

    def register_guard(self, name: str, func: Callable[[Dict], bool]) -> None:
        self._guard_functions[name] = func

    def register_llm_guard(
        self,
        name: str,
        prompt: str,
        llm_config: Optional[Dict] = None
    ) -> None:
        """Register a guard that requires LLM evaluation"""
        self._llm_guards[name] = {
            "prompt": prompt,
            "llm_config": llm_config
        }
        logger.info(f"Registered LLM guard: {name}")

    def add_rule(self, rule: Union[Rule, Dict]) -> None:
        if isinstance(rule, dict):
            rule = Rule.from_dict(rule)
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    def load_rules_from_yaml(self, path: str) -> int:
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        rules_data = data.get('rules', [])
        for rule_def in rules_data:
            rule = Rule.from_dict(rule_def)
            self.add_rule(rule)
        
        logger.info(f"Loaded {len(rules_data)} rules from {path}")
        return len(rules_data)

    def evaluate(
        self,
        semantic_context: Dict[str, Any],
        workflow_context: Dict[str, Any]
    ) -> List[RuleResult]:
        """
        Evaluate all rules against combined context.
        Returns list of matching rules.
        """
        context = {**semantic_context, **workflow_context}
        results = []

        for rule in self._rules:
            if rule.evaluate(context):
                guard_passed = True
                
                if rule.guard:
                    if rule.guard in self._llm_guards:
                        guard_passed = self._evaluate_llm_guard(rule.guard, context)
                    elif rule.guard in self._guard_functions:
                        guard_passed = self._guard_functions[rule.guard](context)
                
                result = RuleResult(
                    rule=rule,
                    action=rule.action,
                    target=rule.target,
                    success=guard_passed,
                    metadata={
                        "guard_checked": rule.guard is not None,
                        "guard_type": "llm" if rule.guard in self._llm_guards else "deterministic"
                    }
                )
                results.append(result)

        logger.info(f"Evaluated {len(self._rules)} rules, {len(results)} matched")
        return results

    def _evaluate_llm_guard(self, guard_name: str, context: Dict[str, Any]) -> bool:
        """Evaluate a guard that requires LLM judgment"""
        guard_config = self._llm_guards[guard_name]
        prompt = guard_config["prompt"]
        
        logger.info(f"Evaluating LLM guard: {guard_name}")
        logger.info(f"Prompt: {prompt}")
        logger.info(f"Context available: {list(context.keys())}")
        
        return True

    def resolve_conflicts(self, results: List[RuleResult]) -> RuleResult:
        """Resolve conflicts when multiple rules match"""
        if not results:
            raise ValueError("No rules to resolve")
        
        if len(results) == 1:
            return results[0]
        
        valid_results = [r for r in results if r.success]
        if not valid_results:
            raise ValueError(f"All {len(results)} matching rules blocked by guards")
        
        valid_results.sort(key=lambda r: r.rule.priority, reverse=True)
        return valid_results[0]

    def handle_ambiguous_intent(
        self,
        context: Dict[str, Any]
    ) -> Optional[RuleResult]:
        """Handle ambiguous intent based on policy"""
        if self.ambiguous_policy == AmbiguousIntentPolicy.SUSPEND:
            logger.warning("Ambiguous intent - suspending workflow")
            return None
        
        elif self.ambiguous_policy == AmbiguousIntentPolicy.CLARIFY:
            logger.info("Ambiguous intent - clarification needed")
            return None
        
        else:  # FALLBACK
            logger.info("Ambiguous intent - using fallback")
            fallback_rules = [r for r in self._rules if r.rule.name == "fallback_query"]
            if fallback_rules:
                return RuleResult(
                    rule=fallback_rules[0],
                    action=fallback_rules[0].action,
                    target=fallback_rules[0].target,
                    success=True,
                    metadata={"fallback": True}
                )
            return None

    def explain(self, results: List[RuleResult]) -> str:
        if not results:
            return "No rules matched the current context."
        
        lines = [f"Matched {len(results)} rule(s):"]
        for r in results:
            status = "PASS" if r.success else "BLOCKED"
            lines.append(f"  - [{status}] {r.rule.name}: {r.action.value} → {r.target}")
        
        return "\n".join(lines)
