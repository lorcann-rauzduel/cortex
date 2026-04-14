"""
Tests pour le Petri Net Engine
"""
import pytest
from coordination.petri_net import (
    PetriNet, Place, Transition, Token, WorkflowEngine
)


class TestPetriNet:
    def setup_method(self):
        self.net = PetriNet(name="test_net")

    def test_add_place(self):
        place = Place(id="p1", type="initial")
        self.net.add_place(place)
        assert "p1" in self.net.places
        assert self.net.places["p1"].type == "initial"

    def test_add_transition(self):
        self.net.add_place(Place(id="p1", type="initial"))
        self.net.add_place(Place(id="p2"))
        
        transition = Transition(
            id="t1",
            from_places=["p1"],
            to_place="p2"
        )
        self.net.add_transition(transition)
        
        assert "t1" in self.net.transitions
        assert transition in self.net.transitions.values()

    def test_fire_transition(self):
        self.net.add_place(Place(id="p1", type="initial"))
        self.net.add_place(Place(id="p2"))
        
        self.net.add_transition(Transition(
            id="t1",
            from_places=["p1"],
            to_place="p2"
        ))
        
        self.net.initialize()
        self.net.state.marking["p1"] = [Token(id="token1", data={})]
        
        result = self.net.fire_transition("t1")
        
        assert result.success
        assert len(self.net.state.marking["p1"]) == 0
        assert len(self.net.state.marking["p2"]) == 1
        assert "t1" in self.net.state.history

    def test_fire_unknown_transition(self):
        result = self.net.fire_transition("unknown")
        assert not result.success
        assert "Unknown transition" in result.error

    def test_fire_without_tokens(self):
        self.net.add_place(Place(id="p1"))
        self.net.add_place(Place(id="p2"))
        self.net.add_transition(Transition(
            id="t1",
            from_places=["p1"],
            to_place="p2"
        ))
        self.net.initialize()
        
        result = self.net.fire_transition("t1")
        assert not result.success
        assert "Missing tokens" in result.error

    def test_guard_function(self):
        self.net.add_place(Place(id="p1", type="initial"))
        self.net.add_place(Place(id="p2"))
        
        self.net.add_transition(Transition(
            id="t1",
            from_places=["p1"],
            to_place="p2",
            guard="approved"
        ))
        
        self.net.register_guard_function("approved", lambda ctx: ctx.get("approved", False))
        self.net.initialize()
        self.net.state.marking["p1"] = [Token(id="token1", data={})]
        
        assert "t1" not in self.net.get_enabled_transitions()
        assert "t1" in self.net.get_enabled_transitions({"approved": True})

    def test_detect_deadlock(self):
        self.net.add_place(Place(id="p1", type="initial"))
        self.net.add_place(Place(id="p2"))
        self.net.add_transition(Transition(
            id="t1",
            from_places=["p1"],
            to_place="p2"
        ))
        self.net.initialize()
        self.net.state.marking["p1"] = [Token(id="token1", data={})]
        
        assert not self.net.detect_deadlock()

    def test_to_dot_export(self):
        self.net.add_place(Place(id="p1", type="initial"))
        self.net.add_place(Place(id="p2", type="final"))
        self.net.add_transition(Transition(
            id="t1",
            from_places=["p1"],
            to_place="p2"
        ))
        self.net.initialize()
        
        dot = self.net.to_dot()
        assert "digraph" in dot
        assert "p1" in dot
        assert "t1" in dot


class TestWorkflowEngine:
    def setup_method(self):
        self.engine = WorkflowEngine()
        
        net = PetriNet(name="test_workflow")
        net.add_place(Place(id="start", type="initial"))
        net.add_place(Place(id="middle"))
        net.add_place(Place(id="end", type="final"))
        
        net.add_transition(Transition(
            id="step1",
            from_places=["start"],
            to_place="middle",
            action="step1"
        ))
        net.add_transition(Transition(
            id="step2",
            from_places=["middle"],
            to_place="end",
            action="step2"
        ))
        
        initial_places = [p.id for p in net.places.values() if p.type == 'initial']
        if initial_places:
            for pid in initial_places:
                net.state.marking[pid] = [Token(id=f"init_{pid}", data={})]
        
        self.engine.register_workflow("test", net)

    def test_create_instance(self):
        instance = self.engine.create_instance("test", "inst1")
        assert instance.id == "inst1"
        assert instance.workflow_id == "test"
        assert len(instance.state.marking["start"]) == 1

    def test_fire_by_action(self):
        instance = self.engine.create_instance("test", "inst1")
        
        result = self.engine.fire_by_action("inst1", "step1")
        assert result.success
        
        state = self.engine.get_state("inst1")
        assert "middle" in state["active_places"]

    def test_get_state(self):
        instance = self.engine.create_instance("test", "inst1")
        state = self.engine.get_state("inst1")
        
        assert state["instance_id"] == "inst1"
        assert state["workflow_id"] == "test"
        assert "start" in state["active_places"]

    def test_unknown_instance(self):
        with pytest.raises(ValueError):
            self.engine.fire_transition("unknown", "step1")
