"""
Petri Net Engine for formal workflow coordination
Based on Colored Petri Net semantics
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime
import networkx as nx
import logging

logger = logging.getLogger(__name__)


@dataclass
class Place:
    id: str
    type: str = "normal"
    tokens: List[Any] = field(default_factory=list)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, Place) and self.id == other.id


@dataclass
class Transition:
    id: str
    from_places: List[str]
    to_place: str
    guard: Optional[str] = None
    action: Optional[str] = None
    description: str = ""

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, Transition) and self.id == other.id


@dataclass
class Token:
    id: str
    data: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class PetriNetState:
    marking: Dict[str, List[Token]]
    history: List[str]

    def __init__(self):
        self.marking = {}
        self.history = []


@dataclass
class TransitionResult:
    success: bool
    transition_id: str
    new_marking: Dict[str, List[Token]]
    consumed_tokens: List[Token]
    produced_tokens: List[Token]
    error: Optional[str] = None


class PetriNet:
    """
    Colored Petri Net implementation for workflow coordination.
    
    Key properties:
    - Places represent states
    - Transitions represent actions
    - Tokens carry data (colored)
    - Guards control transition enablement
    """

    def __init__(self, name: str):
        self.name = name
        self.places: Dict[str, Place] = {}
        self.transitions: Dict[str, Transition] = {}
        self.initial_marking: Dict[str, List[Token]] = {}
        self.state = PetriNetState()
        self.guard_functions: Dict[str, callable] = {}
        
        self._graph = nx.DiGraph()

    def add_place(self, place: Place) -> None:
        self.places[place.id] = place
        self._graph.add_node(f"P:{place.id}", type="place", obj=place)
        logger.debug(f"Added place: {place.id}")

    def add_transition(self, transition: Transition) -> None:
        self.transitions[transition.id] = transition
        self._graph.add_node(f"T:{transition.id}", type="transition", obj=transition)
        
        for from_place in transition.from_places:
            if from_place in self.places:
                self._graph.add_edge(f"P:{from_place}", f"T:{transition.id}")
        
        self._graph.add_edge(f"T:{transition.id}", f"P:{transition.to_place}")
        logger.debug(f"Added transition: {transition.id}")

    def register_guard_function(self, name: str, func: callable) -> None:
        self.guard_functions[name] = func

    def initialize(self, tokens: Optional[Dict[str, List[Token]]] = None) -> None:
        if tokens:
            self.state.marking = tokens
        else:
            self.state.marking = {
                pid: [] for pid in self.places
            }
        self.state.history = []

    def get_enabled_transitions(self, context: Dict[str, Any] = None) -> List[str]:
        """Find all transitions that can fire given current marking"""
        enabled = []
        context = context or {}
        
        for tid, transition in self.transitions.items():
            required_places = set(transition.from_places)
            
            has_tokens = all(
                len(self.state.marking.get(pid, [])) > 0 
                for pid in required_places
            )
            
            guard_passed = True
            if transition.guard and transition.guard in self.guard_functions:
                guard_passed = self.guard_functions[transition.guard](context)
            
            if has_tokens and guard_passed:
                enabled.append(tid)
        
        return enabled

    def fire_transition(
        self, 
        transition_id: str, 
        token_data: Optional[Dict[str, Any]] = None
    ) -> TransitionResult:
        """
        Fire a transition, consuming tokens from input places
        and producing tokens in output place.
        """
        if transition_id not in self.transitions:
            return TransitionResult(
                success=False,
                transition_id=transition_id,
                new_marking=self.state.marking.copy(),
                consumed_tokens=[],
                produced_tokens=[],
                error=f"Unknown transition: {transition_id}"
            )
        
        transition = self.transitions[transition_id]
        
        if not all(len(self.state.marking.get(pid, [])) > 0 for pid in transition.from_places):
            return TransitionResult(
                success=False,
                transition_id=transition_id,
                new_marking=self.state.marking.copy(),
                consumed_tokens=[],
                produced_tokens=[],
                error="Missing tokens in input places"
            )
        
        consumed = []
        for pid in transition.from_places:
            if self.state.marking.get(pid):
                consumed.append(self.state.marking[pid].pop(0))
        
        new_token = Token(
            id=f"{transition_id}_{datetime.now().timestamp()}",
            data=token_data or {}
        )
        produced = [new_token]
        
        if transition.to_place not in self.state.marking:
            self.state.marking[transition.to_place] = []
        self.state.marking[transition.to_place].append(new_token)
        
        self.state.history.append(transition_id)
        
        logger.info(f"Fired transition {transition_id}, marking: {self._get_marking_summary()}")
        
        return TransitionResult(
            success=True,
            transition_id=transition_id,
            new_marking=self.state.marking.copy(),
            consumed_tokens=consumed,
            produced_tokens=produced
        )

    def fire_transition_by_name(self, name: str, context: Dict[str, Any] = None) -> TransitionResult:
        """Find and fire a transition by action name"""
        for tid, t in self.transitions.items():
            if t.action == name:
                return self.fire_transition(tid, context)
        return TransitionResult(
            success=False,
            transition_id=name,
            new_marking=self.state.marking.copy(),
            consumed_tokens=[],
            produced_tokens=[],
            error=f"No transition with action: {name}"
        )

    def _get_marking_summary(self) -> str:
        summary = []
        for pid, tokens in self.state.marking.items():
            if tokens:
                summary.append(f"{pid}:{len(tokens)}")
        return ", ".join(summary) if summary else "(empty)"

    def detect_deadlock(self) -> bool:
        """Check if system is in a deadlock state"""
        return len(self.get_enabled_transitions()) == 0 and self._has_active_tokens()

    def _has_active_tokens(self) -> bool:
        return any(len(tokens) > 0 for tokens in self.state.marking.values())

    def get_active_places(self) -> List[str]:
        """Get places that have tokens"""
        return [pid for pid, tokens in self.state.marking.items() if tokens]

    def get_graph(self) -> nx.DiGraph:
        """Return NetworkX graph for visualization"""
        return self._graph

    def to_dot(self) -> str:
        """Export to DOT format for GraphViz"""
        lines = ["digraph {", f'  label="{self.name}"']
        
        for pid, place in self.places.items():
            token_count = len(self.state.marking.get(pid, []))
            shape = "circle" if place.type == "initial" else "doublecircle" if place.type == "final" else "box"
            lines.append(f'  {pid} [shape={shape}, label="{pid}\\n({token_count} tokens)"]')
        
        for tid, transition in self.transitions.items():
            label = transition.description or tid
            lines.append(f'  {tid} [shape=box, style=filled, fillcolor=lightgray, label="{label}"]')
            for fp in transition.from_places:
                lines.append(f"  {fp} -> {tid}")
            lines.append(f"  {tid} -> {transition.to_place}")
        
        lines.append("}")
        return "\n".join(lines)


@dataclass
class WorkflowInstance:
    id: str
    workflow_id: str
    petri_net: PetriNet
    state: PetriNetState
    variables: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class WorkflowEngine:
    """
    Manages workflow instances and their execution
    """

    def __init__(self):
        self._workflows: Dict[str, PetriNet] = {}
        self._instances: Dict[str, WorkflowInstance] = {}
        self._workflow_definitions: Dict[str, Dict] = {}

    def register_workflow(self, workflow_id: str, net: PetriNet) -> None:
        self._workflows[workflow_id] = net
        logger.info(f"Registered workflow: {workflow_id}")

    def load_workflow_from_yaml(self, workflow_id: str, path: str) -> PetriNet:
        """Load workflow definition from YAML"""
        import yaml
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        self._workflow_definitions[workflow_id] = data
        
        net = PetriNet(name=data.get('name', workflow_id))
        
        for place_def in data.get('places', []):
            place = Place(
                id=place_def['id'],
                type=place_def.get('type', 'normal')
            )
            net.add_place(place)
        
        for trans_def in data.get('transitions', []):
            transition = Transition(
                id=trans_def['id'],
                from_places=trans_def['from'],
                to_place=trans_def['to'],
                guard=trans_def.get('guard'),
                action=trans_def.get('action'),
                description=trans_def.get('description', '')
            )
            net.add_transition(transition)
        
        initial_places = [p.id for p in net.places.values() if p.type == 'initial']
        if initial_places:
            for pid in initial_places:
                net.state.marking[pid] = [Token(id=f"init_{pid}", data={})]
        
        self.register_workflow(workflow_id, net)
        return net

    def create_instance(
        self, 
        workflow_id: str, 
        instance_id: str,
        initial_data: Optional[Dict[str, Any]] = None
    ) -> WorkflowInstance:
        """Create a new workflow instance"""
        if workflow_id not in self._workflows:
            raise ValueError(f"Unknown workflow: {workflow_id}")
        
        workflow = self._workflows[workflow_id]
        net = PetriNet(name=workflow.name)
        net.places = workflow.places.copy()
        net.transitions = workflow.transitions.copy()
        net.guard_functions = workflow.guard_functions.copy()
        net.state = PetriNetState()
        net.state.marking = {
            pid: [Token(id=f"{pid}_{i}", data=t.data.copy()) for i, t in enumerate(tokens)]
            for pid, tokens in workflow.state.marking.items()
        }
        net.state.history = []
        
        if initial_data:
            for pid, tokens in net.state.marking.items():
                if tokens:
                    tokens[0].data.update(initial_data)
        
        instance = WorkflowInstance(
            id=instance_id,
            workflow_id=workflow_id,
            petri_net=net,
            state=net.state,
            variables=initial_data or {},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self._instances[instance_id] = instance
        logger.info(f"Created instance {instance_id} for workflow {workflow_id}")
        return instance

    def fire_transition(self, instance_id: str, transition_id: str) -> TransitionResult:
        """Fire a transition on a workflow instance"""
        if instance_id not in self._instances:
            raise ValueError(f"Unknown instance: {instance_id}")
        
        instance = self._instances[instance_id]
        result = instance.petri_net.fire_transition(transition_id)
        
        if result.success:
            instance.updated_at = datetime.now()
        
        return result

    def fire_by_action(self, instance_id: str, action: str) -> TransitionResult:
        """Fire transition by action name"""
        if instance_id not in self._instances:
            raise ValueError(f"Unknown instance: {instance_id}")
        
        instance = self._instances[instance_id]
        return instance.petri_net.fire_transition_by_name(action)

    def get_state(self, instance_id: str) -> Dict[str, Any]:
        """Get current state of a workflow instance"""
        if instance_id not in self._instances:
            raise ValueError(f"Unknown instance: {instance_id}")
        
        instance = self._instances[instance_id]
        return {
            "instance_id": instance.id,
            "workflow_id": instance.workflow_id,
            "active_places": instance.petri_net.get_active_places(),
            "enabled_transitions": instance.petri_net.get_enabled_transitions(),
            "marking": {
                pid: [t.id for t in tokens] 
                for pid, tokens in instance.state.marking.items() 
                if tokens
            },
            "history": instance.state.history,
            "variables": instance.variables,
            "is_deadlock": instance.petri_net.detect_deadlock(),
            "is_complete": self._is_complete(instance)
        }

    def _is_complete(self, instance: WorkflowInstance) -> bool:
        final_places = [p.id for p in instance.petri_net.places.values() if p.type == "final"]
        return any(
            len(instance.state.marking.get(pid, [])) > 0 
            for pid in final_places
        )

    def list_workflows(self) -> List[str]:
        return list(self._workflows.keys())

    def register_guard(self, name: str, func: callable) -> None:
        """Register a guard function for all workflows"""
        for net in self._workflows.values():
            net.register_guard_function(name, func)

    def list_instances(self, workflow_id: Optional[str] = None) -> List[str]:
        if workflow_id:
            return [i.id for i in self._instances.values() if i.workflow_id == workflow_id]
        return [i.id for i in self._instances.values()]
