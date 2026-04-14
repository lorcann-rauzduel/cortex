"""
Tests pour le Rule Engine
"""
import pytest
from rules.rule_engine import (
    RuleEngine, Rule, RuleCondition, RuleAction, RuleResult
)


class TestRuleCondition:
    def test_intent_match(self):
        cond = RuleCondition(intent="APPROVE")
        assert cond.matches({"intent": "APPROVE"})
        assert not cond.matches({"intent": "REJECT"})

    def test_topics_match(self):
        cond = RuleCondition(topics=["task", "approval"])
        assert cond.matches({"topics": ["task", "other"]})
        assert cond.matches({"topics": ["approval"]})
        assert not cond.matches({"topics": ["other"]})

    def test_confidence_threshold(self):
        cond = RuleCondition(confidence_min=0.8)
        assert cond.matches({"confidence": 0.9})
        assert not cond.matches({"confidence": 0.5})


class TestRuleEngine:
    def setup_method(self):
        self.engine = RuleEngine()

    def test_add_rule(self):
        rule = Rule(
            name="test_rule",
            description="Test rule",
            condition=RuleCondition(intent="APPROVE"),
            action=RuleAction.FIRE_TRANSITION,
            target="approve"
        )
        self.engine.add_rule(rule)
        assert len(self.engine._rules) == 1

    def test_evaluate_matches(self):
        rule = Rule(
            name="approve_rule",
            description="Approve action",
            condition=RuleCondition(intent="APPROVE"),
            action=RuleAction.FIRE_TRANSITION,
            target="approve",
            priority=10
        )
        self.engine.add_rule(rule)
        
        results = self.engine.evaluate(
            {"intent": "APPROVE"},
            {}
        )
        assert len(results) == 1
        assert results[0].rule.name == "approve_rule"

    def test_evaluate_no_match(self):
        rule = Rule(
            name="reject_rule",
            description="Reject action",
            condition=RuleCondition(intent="REJECT"),
            action=RuleAction.FIRE_TRANSITION,
            target="reject"
        )
        self.engine.add_rule(rule)
        
        results = self.engine.evaluate(
            {"intent": "APPROVE"},
            {}
        )
        assert len(results) == 0

    def test_priority_ordering(self):
        low_priority = Rule(
            name="low",
            description="Low priority rule",
            condition=RuleCondition(intent="APPROVE"),
            action=RuleAction.FIRE_TRANSITION,
            target="approve",
            priority=1
        )
        high_priority = Rule(
            name="high",
            description="High priority rule",
            condition=RuleCondition(intent="APPROVE"),
            action=RuleAction.FIRE_TRANSITION,
            target="approve",
            priority=10
        )
        self.engine.add_rule(low_priority)
        self.engine.add_rule(high_priority)
        
        assert self.engine._rules[0].priority == 10

    def test_resolve_conflicts(self):
        rule1 = Rule(
            name="rule1",
            description="Rule 1",
            condition=RuleCondition(intent="APPROVE"),
            action=RuleAction.FIRE_TRANSITION,
            target="action1",
            priority=5
        )
        rule2 = Rule(
            name="rule2",
            description="Rule 2",
            condition=RuleCondition(intent="APPROVE"),
            action=RuleAction.FIRE_TRANSITION,
            target="action2",
            priority=10
        )
        self.engine.add_rule(rule1)
        self.engine.add_rule(rule2)
        
        results = self.engine.evaluate({"intent": "APPROVE"}, {})
        winner = self.engine.resolve_conflicts(results)
        
        assert winner.rule.name == "rule2"
        assert winner.target == "action2"

    def test_guard_function(self):
        self.engine.register_guard(
            "high_value",
            lambda ctx: ctx.get("value", 0) > 100
        )
        
        rule = Rule(
            name="guard_rule",
            description="Guard rule",
            condition=RuleCondition(intent="APPROVE"),
            action=RuleAction.FIRE_TRANSITION,
            target="approve",
            guard="high_value"
        )
        self.engine.add_rule(rule)
        
        results = self.engine.evaluate(
            {"intent": "APPROVE", "value": 150},
            {}
        )
        assert results[0].success

        results = self.engine.evaluate(
            {"intent": "APPROVE", "value": 50},
            {}
        )
        assert not results[0].success
