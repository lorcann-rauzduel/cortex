"""
Neuro-symbolic Rule Engine for Cortex
Bridges semantic understanding with formal coordination
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Union
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
        """Create RuleCondition from dict for convenience"""
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
        """Create Rule from dict for convenience"""
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


class RuleEngine:
    """
    Neuro-symbolic rule engine that translates semantic context
    into formal coordination actions.
    """

    def __init__(self):
        self._rules: List[Rule] = []
        self._guard_functions: Dict[str, Callable] = {}

    def register_guard(self, name: str, func: Callable[[Dict], bool]) -> None:
        """Register a guard function for conditional transitions"""
        self._guard_functions[name] = func

    def add_rule(self, rule: Union[Rule, Dict]) -> None:
        """Add a rule to the engine"""
        if isinstance(rule, dict):
            rule = Rule.from_dict(rule)
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    def load_rules_from_yaml(self, path: str) -> int:
        """Load rules from YAML definition file"""
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
        Evaluate all rules against combined context
        Returns list of matching rules to fire
        """
        context = {**semantic_context, **workflow_context}
        results = []

        for rule in self._rules:
            if rule.evaluate(context):
                guard_passed = True
                if rule.guard and rule.guard in self._guard_functions:
                    guard_passed = self._guard_functions[rule.guard](context)
                
                result = RuleResult(
                    rule=rule,
                    action=rule.action,
                    target=rule.target,
                    success=guard_passed,
                    metadata={"guard_checked": rule.guard is not None}
                )
                results.append(result)
                
                if not guard_passed:
                    logger.debug(f"Rule {rule.name} matched but guard {rule.guard} failed")

        logger.info(f"Evaluated {len(self._rules)} rules, {len(results)} matched")
        return results

    def resolve_conflicts(self, results: List[RuleResult]) -> RuleResult:
        """
        Resolve conflicts when multiple rules match.
        Strategy: highest priority wins
        """
        if not results:
            raise ValueError("No rules to resolve")
        
        if len(results) == 1:
            return results[0]
        
        valid_results = [r for r in results if r.success]
        if not valid_results:
            raise ValueError(f"All {len(results)} matching rules blocked by guards")
        
        valid_results.sort(key=lambda r: r.rule.priority, reverse=True)
        winner = valid_results[0]
        
        logger.info(
            f"Conflict resolved: '{winner.rule.name}' won over "
            f"{[r.rule.name for r in valid_results[1:]]}"
        )
        return winner

    def explain(self, results: List[RuleResult]) -> str:
        """Generate explanation of rule evaluation"""
        if not results:
            return "No rules matched the current context."
        
        lines = [f"Matched {len(results)} rule(s):"]
        for r in results:
            status = "PASS" if r.success else "BLOCKED"
            lines.append(f"  - [{status}] {r.rule.name}: {r.action.value} → {r.target}")
        
        return "\n".join(lines)
