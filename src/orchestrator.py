"""
Cortex Orchestrator - Main orchestration engine
Bridges semantic understanding with formal coordination
"""
from __future__ import annotations
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid
import logging

from semantic.intent_classifier import IntentClassifier, SemanticResult
from coordination.petri_net import WorkflowEngine, PetriNet, Place, Transition, Token
from rules.rule_engine import RuleEngine, RuleAction, Rule, RuleCondition

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationResult:
    success: bool
    intent: str
    action_taken: str
    new_state: Optional[Dict[str, Any]]
    message: str
    workflow_instance_id: Optional[str] = None
    error: Optional[str] = None


class CortexOrchestrator:
    """
    Main orchestration engine for Cortex.
    
    Flow:
    1. Semantic Layer: Classify user intent (LLM or mock)
    ↓
    2. Rule Engine: Map intent to coordination action
    ↓
    3. Coordination Layer: Execute workflow via Petri Net
    """

    def __init__(
        self,
        use_llm: bool = True,
        llm_config: Optional[Dict] = None
    ):
        self.intent_classifier = IntentClassifier(
            use_llm=use_llm,
            llm_config=llm_config or {"provider": "ollama", "model": "llama3.2"}
        )
        self.workflow_engine = WorkflowEngine()
        self.rule_engine = RuleEngine()
        
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._register_builtin_rules()
        self._register_builtin_guards()

    def initialize(self) -> bool:
        """Initialize all components"""
        self.intent_classifier.initialize()
        logger.info("Cortex Orchestrator initialized")
        return True

    def _register_builtin_rules(self) -> None:
        """Register built-in rules for common intents"""
        rules = [
            Rule(
                name="create_task",
                description="Create a new task",
                condition=RuleCondition(intent="CREATE", topics=["task"]),
                action=RuleAction.FIRE_TRANSITION,
                target="create",
                priority=10
            ),
            Rule(
                name="approve_action",
                description="Approve pending item",
                condition=RuleCondition(intent="APPROVE"),
                action=RuleAction.FIRE_TRANSITION,
                target="approve",
                priority=10
            ),
            Rule(
                name="reject_action",
                description="Reject pending item",
                condition=RuleCondition(intent="REJECT"),
                action=RuleAction.FIRE_TRANSITION,
                target="reject",
                priority=10
            ),
            Rule(
                name="cancel_task",
                description="Cancel a task",
                condition=RuleCondition(intent="CANCEL"),
                action=RuleAction.FIRE_TRANSITION,
                target="cancel",
                priority=8
            ),
            Rule(
                name="escalate_issue",
                description="Escalate to higher authority",
                condition=RuleCondition(intent="ESCALATE"),
                action=RuleAction.FIRE_TRANSITION,
                target="escalate",
                priority=7
            ),
            Rule(
                name="query_status",
                description="Query workflow status",
                condition=RuleCondition(intent="QUERY"),
                action=RuleAction.GOTO_STATE,
                target="query_status",
                priority=5
            ),
        ]
        
        for rule in rules:
            self.rule_engine.add_rule(rule)
        
        logger.info(f"Registered {len(rules)} built-in rules")

    def _register_builtin_guards(self) -> None:
        """Register built-in guard functions"""
        self.workflow_engine.register_guard(
            "has_description",
            lambda ctx: bool(ctx.get("entities", {}).get("description"))
        )
        self.workflow_engine.register_guard(
            "requires_approval",
            lambda ctx: ctx.get("role") == "MANAGER" or ctx.get("confidence", 0) < 0.8
        )

    def orchestrate(
        self,
        message: str,
        session_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> OrchestrationResult:
        """
        Main orchestration entry point.
        
        1. Semantic understanding (LLM or mock)
        2. Rule matching
        3. Workflow execution
        """
        session_id = session_id or str(uuid.uuid4())
        context = context or {}
        
        if session_id not in self._sessions:
            self._sessions[session_id] = {"workflows": {}, "context": {}}
        
        semantic = self.intent_classifier.classify(message, context)
        
        workflow_context = {}
        if workflow_id:
            if workflow_id not in self._sessions[session_id]["workflows"]:
                instance_id = f"{workflow_id}_{session_id[:8]}"
                self.workflow_engine.create_instance(workflow_id, instance_id)
                self._sessions[session_id]["workflows"][workflow_id] = instance_id
            
            instance_id = self._sessions[session_id]["workflows"][workflow_id]
            workflow_state = self.workflow_engine.get_state(instance_id)
            workflow_context = workflow_state
        
        semantic_context = semantic.to_context()
        semantic_context["session_id"] = session_id
        semantic_context["workflow_context"] = workflow_context
        
        try:
            rule_results = self.rule_engine.evaluate(
                semantic_context, 
                workflow_context
            )
            
            if not rule_results:
                return OrchestrationResult(
                    success=False,
                    intent=semantic.intent.value if isinstance(semantic.intent, str) else str(semantic.intent),
                    action_taken="none",
                    new_state=None,
                    message="No matching rules found",
                    error="No rules matched the current context"
                )
            
            selected_rule = self.rule_engine.resolve_conflicts(rule_results)
            
            action_result = self._execute_action(
                selected_rule.action,
                selected_rule.target,
                semantic_context,
                workflow_context
            )
            
            if action_result["success"] and workflow_id:
                instance_id = self._sessions[session_id]["workflows"].get(workflow_id)
                if instance_id:
                    new_state = self.workflow_engine.get_state(instance_id)
                    action_result["workflow_state"] = new_state
            
            return OrchestrationResult(
                success=action_result["success"],
                intent=semantic.intent.value if isinstance(semantic.intent, str) else str(semantic.intent),
                action_taken=selected_rule.target,
                new_state=action_result.get("workflow_state"),
                message=action_result.get("message", "Action completed"),
                workflow_instance_id=self._sessions[session_id]["workflows"].get(workflow_id),
                error=action_result.get("error")
            )
            
        except Exception as e:
            logger.error(f"Orchestration error: {e}")
            return OrchestrationResult(
                success=False,
                intent=semantic.intent.value if isinstance(semantic.intent, str) else str(semantic.intent),
                action_taken="error",
                new_state=None,
                message=f"Orchestration failed: {str(e)}",
                error=str(e)
            )

    def _execute_action(
        self,
        action: RuleAction,
        target: str,
        semantic_context: Dict[str, Any],
        workflow_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute coordination action based on rule result"""
        
        if action == RuleAction.FIRE_TRANSITION:
            instance_id = semantic_context.get("workflow_context", {}).get("instance_id")
            if instance_id:
                result = self.workflow_engine.fire_by_action(instance_id, target)
                return {
                    "success": result.success,
                    "message": f"Fired transition '{target}'" if result.success else result.error,
                    "error": result.error if not result.success else None
                }
            return {
                "success": False,
                "message": f"No active workflow for action '{target}'",
                "error": "No active workflow instance"
            }
        
        elif action == RuleAction.GOTO_STATE:
            return {
                "success": True,
                "message": f"State query: {target}",
                "state": semantic_context.get("workflow_context", {})
            }
        
        elif action == RuleAction.ESCALATE:
            instance_id = semantic_context.get("workflow_context", {}).get("instance_id")
            if instance_id:
                result = self.workflow_engine.fire_by_action(instance_id, "escalate")
                return {
                    "success": result.success,
                    "message": f"Escalated to manager" if result.success else result.error,
                    "error": result.error if not result.success else None
                }
            return {
                "success": True,
                "message": "Escalation queued"
            }
        
        return {
            "success": False,
            "message": f"Unknown action type: {action}",
            "error": f"Unknown action: {action}"
        }

    def load_workflow(self, workflow_id: str, yaml_path: str) -> bool:
        """Load a workflow definition"""
        try:
            self.workflow_engine.load_workflow_from_yaml(workflow_id, yaml_path)
            return True
        except Exception as e:
            logger.error(f"Failed to load workflow {workflow_id}: {e}")
            return False

    def get_workflows(self) -> List[str]:
        """List available workflows"""
        return self.workflow_engine.list_workflows()

    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session state"""
        return self._sessions.get(session_id)

    def cleanup_session(self, session_id: str) -> bool:
        """Clean up a session"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
