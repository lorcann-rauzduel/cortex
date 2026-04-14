"""
Tests for edge cases: confidence boundary, session context, LLM guards, boundedness
"""
import pytest
from orchestrator import CortexOrchestrator
from coordination.petri_net import PetriNet, Place, Transition, Token
from rules.rule_engine import (
    RuleEngine, Rule, RuleCondition, RuleAction, 
    AmbiguousIntentPolicy
)


class TestConfidenceBoundary:
    """Test ambiguous intent handling"""

    def setup_method(self):
        self.orchestrator = CortexOrchestrator(use_llm=False)
        self.orchestrator.initialize()

    def test_normal_confidence_passes(self):
        """High confidence should pass through normally"""
        result = self.orchestrator.orchestrate("Approuver la demande")
        assert result.confidence >= 0.6

    def test_ambiguous_suspend_policy(self):
        """Test SUSPEND policy for low confidence"""
        orchestrator = CortexOrchestrator(
            use_llm=False,
            ambiguous_policy=AmbiguousIntentPolicy.SUSPEND,
            confidence_threshold=0.99
        )
        orchestrator.initialize()
        
        result = orchestrator.orchestrate("Approuver")
        assert result.ambiguous is True
        assert result.clarification_needed is False

    def test_ambiguous_clarify_policy(self):
        """Test CLARIFY policy for low confidence"""
        orchestrator = CortexOrchestrator(
            use_llm=False,
            ambiguous_policy=AmbiguousIntentPolicy.CLARIFY,
            confidence_threshold=0.9
        )
        orchestrator.initialize()
        
        result = orchestrator.orchestrate("Peut-etre")
        assert result.ambiguous is True
        assert result.clarification_needed is True

    def test_fallback_policy(self):
        """Test FALLBACK policy uses default"""
        orchestrator = CortexOrchestrator(
            use_llm=False,
            ambiguous_policy=AmbiguousIntentPolicy.FALLBACK,
            confidence_threshold=0.95
        )
        orchestrator.initialize()
        
        result = orchestrator.orchestrate("Un truc")
        assert result.ambiguous is False


class TestSessionContext:
    """Test session turn history"""

    def setup_method(self):
        self.orchestrator = CortexOrchestrator(use_llm=False)
        self.orchestrator.initialize()

    def test_session_creation(self):
        """New session should be created"""
        result = self.orchestrator.orchestrate(
            "Creer une tache",
            session_id="test_session"
        )
        assert "test_session" in self.orchestrator._sessions

    def test_turn_history_accumulates(self):
        """Turn history should accumulate"""
        session_id = "history_test"
        
        self.orchestrator.orchestrate("Je veux commander", session_id=session_id)
        self.orchestrator.orchestrate("Pour demain", session_id=session_id)
        self.orchestrator.orchestrate("Maintenant annuler", session_id=session_id)
        
        session = self.orchestrator._sessions[session_id]
        assert len(session["turn_history"]) == 3

    def test_turn_history_limit(self):
        """Turn history should be limited to 10"""
        session_id = "limit_test"
        
        for i in range(15):
            self.orchestrator.orchestrate(f"Turn {i}", session_id=session_id)
        
        session = self.orchestrator._sessions[session_id]
        assert len(session["turn_history"]) <= 10

    def test_different_sessions_independent(self):
        """Different sessions should have independent history"""
        self.orchestrator.orchestrate("Message A", session_id="s1")
        self.orchestrator.orchestrate("Message B", session_id="s2")
        
        assert self.orchestrator._sessions["s1"]["turn_history"] == ["Message A"]
        assert self.orchestrator._sessions["s2"]["turn_history"] == ["Message B"]


class TestLLMGuards:
    """Test LLM-evaluated guard conditions"""

    def setup_method(self):
        self.orchestrator = CortexOrchestrator(use_llm=False)
        self.orchestrator.initialize()
        self.orchestrator.workflow_engine.register_workflow("test", PetriNet("test"))

    def test_register_llm_guard(self):
        """Test LLM guard registration"""
        self.orchestrator.register_llm_guard(
            name="report_complete",
            prompt="Is this report complete?"
        )
        assert "report_complete" in self.orchestrator.rule_engine._llm_guards

    def test_llm_guard_in_rule(self):
        """Test rule with LLM guard"""
        self.orchestrator.rule_engine.register_llm_guard(
            "needs_review",
            "Does this need manager review?"
        )
        
        self.orchestrator.rule_engine.add_rule(Rule(
            name="check_review",
            description="Check if review needed",
            condition=RuleCondition(intent="SUBMIT"),
            action=RuleAction.FIRE_TRANSITION,
            target="check",
            guard="needs_review"
        ))
        
        results = self.orchestrator.rule_engine.evaluate(
            {"intent": "SUBMIT"},
            {}
        )
        assert len(results) == 1


class TestPetriNetBoundedness:
    """Test Petri Net boundedness validation"""

    def test_bounded_workflow_loads(self):
        """Valid bounded workflow should load"""
        orchestrator = CortexOrchestrator(use_llm=False)
        orchestrator.initialize()
        
        net = PetriNet("bounded_test")
        net.add_place(Place(id="start", type="initial"))
        net.add_place(Place(id="end", type="final"))
        net.add_transition(Transition(id="t1", from_places=["start"], to_place="end"))
        net.initialize()
        net.state.marking["start"] = [Token(id="t", data={})]
        
        orchestrator.workflow_engine.register_workflow("bounded", net)
        
        is_bounded, issue = orchestrator._validate_boundedness(net)
        assert is_bounded is True
        assert issue is None

    def test_unbounded_no_input_places(self):
        """Transition without input places should fail"""
        orchestrator = CortexOrchestrator(use_llm=False)
        orchestrator.initialize()
        
        net = PetriNet("unbounded_test")
        net.add_place(Place(id="p1"))
        net.add_transition(Transition(id="t1", from_places=[], to_place="p1"))
        
        is_bounded, issue = orchestrator._validate_boundedness(net)
        assert is_bounded is False
        assert "no input places" in issue

    def test_unbounded_self_loop(self):
        """Transition that doesn't consume tokens should fail"""
        orchestrator = CortexOrchestrator(use_llm=False)
        orchestrator.initialize()
        
        net = PetriNet("unbounded_selfloop")
        net.add_place(Place(id="p1"))
        net.add_transition(Transition(id="t1", from_places=["p1"], to_place="p1"))
        
        is_bounded, issue = orchestrator._validate_boundedness(net)
        assert is_bounded is False

    def test_workflow_load_validates_boundedness(self):
        """load_workflow should validate boundedness"""
        orchestrator = CortexOrchestrator(use_llm=False)
        orchestrator.initialize()
        
        net = PetriNet("test")
        net.add_place(Place(id="start", type="initial"))
        net.add_place(Place(id="end", type="final"))
        net.add_transition(Transition(id="go", from_places=["start"], to_place="end"))
        net.state.marking["start"] = [Token(id="init", data={})]
        
        orchestrator.workflow_engine.register_workflow("valid_test", net)
        
        is_bounded, _ = orchestrator._validate_boundedness(net)
        assert is_bounded is True


class TestOrchestrationResult:
    """Test OrchestrationResult dataclass"""

    def test_result_has_all_fields(self):
        """Result should have all expected fields"""
        from orchestrator import OrchestrationResult
        
        result = OrchestrationResult(
            success=True,
            intent="APPROVE",
            confidence=0.95,
            action_taken="approve",
            new_state={"active_places": ["approved"]},
            message="Done"
        )
        
        assert result.success is True
        assert result.intent == "APPROVE"
        assert result.confidence == 0.95
        assert result.ambiguous is False
        assert result.clarification_needed is False

    def test_ambiguous_result_fields(self):
        """Ambiguous result should have clarification fields"""
        from orchestrator import OrchestrationResult
        
        result = OrchestrationResult(
            success=False,
            intent="UNKNOWN",
            confidence=0.3,
            action_taken="clarification_needed",
            new_state=None,
            message="Please clarify",
            ambiguous=True,
            clarification_needed=True
        )
        
        assert result.ambiguous is True
        assert result.clarification_needed is True
