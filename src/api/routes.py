"""
Cortex API - FastAPI routes
"""
from __future__ import annotations
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import logging

from orchestrator import CortexOrchestrator, OrchestrationResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cortex",
    description="Neuro-symbolic orchestration engine for agents",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = CortexOrchestrator(use_llm=True)


class OrchestrateRequest(BaseModel):
    message: str = Field(..., description="User message to orchestrate")
    session_id: Optional[str] = Field(None, description="Session ID for context")
    workflow_id: Optional[str] = Field(None, description="Target workflow ID")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)


class WorkflowCreateRequest(BaseModel):
    workflow_id: str
    yaml_path: str


class TransitionRequest(BaseModel):
    instance_id: str
    transition_id: str


class SemanticQueryRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None


@app.on_event("startup")
async def startup():
    orchestrator.initialize()
    logger.info("Cortex API started")


@app.get("/")
async def root():
    return {
        "service": "Cortex",
        "version": "0.1.0",
        "description": "Neuro-symbolic orchestration engine",
        "status": "running",
        "llm_mode": orchestrator.intent_classifier.is_llm_mode
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "orchestrator": "initialized",
        "llm_available": orchestrator.intent_classifier.is_llm_mode,
        "workflows_loaded": len(orchestrator.get_workflows())
    }


@app.post("/orchestrate", response_model=OrchestrationResult)
async def orchestrate(request: OrchestrateRequest):
    """Main orchestration endpoint"""
    result = orchestrator.orchestrate(
        message=request.message,
        session_id=request.session_id,
        workflow_id=request.workflow_id,
        context=request.context
    )
    return result


@app.post("/semantic/classify")
async def classify_intent(request: SemanticQueryRequest):
    """Direct semantic classification without orchestration"""
    result = orchestrator.intent_classifier.classify(
        request.message, 
        request.context
    )
    return {
        "intent": result.intent.value if hasattr(result.intent, 'value') else result.intent,
        "topics": result.topics,
        "entities": result.entities,
        "confidence": result.confidence,
        "raw_reasoning": result.raw_reasoning,
        "use_mock": result.use_mock
    }


@app.get("/workflows")
async def list_workflows():
    """List available workflows"""
    return {
        "workflows": orchestrator.get_workflows()
    }


@app.post("/workflows")
async def load_workflow(request: WorkflowCreateRequest):
    """Load a workflow from YAML definition"""
    success = orchestrator.load_workflow(
        request.workflow_id, 
        request.yaml_path
    )
    if success:
        return {"status": "loaded", "workflow_id": request.workflow_id}
    raise HTTPException(status_code=400, detail="Failed to load workflow")


@app.get("/workflow/{workflow_id}/state/{instance_id}")
async def get_workflow_state(workflow_id: str, instance_id: str):
    """Get current state of a workflow instance"""
    try:
        state = orchestrator.workflow_engine.get_state(instance_id)
        return state
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/workflow/fire")
async def fire_transition(request: TransitionRequest):
    """Fire a transition on a workflow instance"""
    result = orchestrator.workflow_engine.fire_transition(
        request.instance_id,
        request.transition_id
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return {
        "success": True,
        "transition_id": result.transition_id,
        "consumed": [t.id for t in result.consumed_tokens],
        "produced": [t.id for t in result.produced_tokens]
    }


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session state"""
    state = orchestrator.get_session_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    return state


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    success = orchestrator.cleanup_session(session_id)
    if success:
        return {"status": "deleted", "session_id": session_id}
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/rules")
async def list_rules():
    """List active rules"""
    rules_info = [
        {
            "name": r.name,
            "description": r.description,
            "action": r.action.value,
            "target": r.target,
            "priority": r.priority
        }
        for r in orchestrator.rule_engine._rules
    ]
    return {"rules": rules_info}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
