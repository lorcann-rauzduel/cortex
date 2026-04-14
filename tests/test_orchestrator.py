"""
Tests d'intégration pour l'orchestrateur Cortex
"""
import pytest
from orchestrator import CortexOrchestrator


class TestCortexOrchestrator:
    def setup_method(self):
        self.orchestrator = CortexOrchestrator(use_llm=False)
        self.orchestrator.initialize()

    def test_initialization(self):
        assert self.orchestrator.intent_classifier is not None
        assert self.orchestrator.workflow_engine is not None
        assert self.orchestrator.rule_engine is not None

    def test_builtin_rules_registered(self):
        assert len(self.orchestrator.rule_engine._rules) >= 6
        rule_names = [r.name for r in self.orchestrator.rule_engine._rules]
        assert "approve_action" in rule_names
        assert "reject_action" in rule_names
        assert "create_task" in rule_names

    def test_orchestrate_create_intent(self):
        result = self.orchestrator.orchestrate("Créer une nouvelle tâche")
        assert result.intent == "CREATE"
        assert result.action_taken == "create"
        assert "No active workflow" in result.message

    def test_orchestrate_approve_intent(self):
        result = self.orchestrator.orchestrate("Approuver la demande")
        assert result.intent == "APPROVE"

    def test_orchestrate_query_intent(self):
        result = self.orchestrator.orchestrate("Quel est le statut?")
        assert result.intent == "QUERY"

    def test_orchestrate_with_session(self):
        session_id = "test_session_123"
        result = self.orchestrator.orchestrate(
            "Créer une tâche",
            session_id=session_id
        )
        assert session_id in self.orchestrator._sessions
        assert result.intent == "CREATE"

    def test_multiple_sessions(self):
        session1 = self.orchestrator.orchestrate("Créer une tâche", session_id="s1")
        session2 = self.orchestrator.orchestrate("Approuver", session_id="s2")
        
        assert "s1" in self.orchestrator._sessions
        assert "s2" in self.orchestrator._sessions
        assert session1.intent != session2.intent

    def test_cleanup_session(self):
        session_id = "cleanup_test"
        self.orchestrator.orchestrate("Test", session_id=session_id)
        assert self.orchestrator.cleanup_session(session_id)
        assert session_id not in self.orchestrator._sessions

    def test_cleanup_nonexistent_session(self):
        assert not self.orchestrator.cleanup_session("nonexistent")

    def test_get_workflows_empty(self):
        workflows = self.orchestrator.get_workflows()
        assert isinstance(workflows, list)

    def test_explain_rules(self):
        results = self.orchestrator.rule_engine.evaluate(
            {"intent": "APPROVE"},
            {}
        )
        explanation = self.orchestrator.rule_engine.explain(results)
        assert "approve_action" in explanation
