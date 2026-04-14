# Cortex - Formal Workflow Engine for Agentic AI

Cortex is a formal workflow engine for agentic AI that separates semantic intent recognition (one LLM call) from state machine coordination (zero LLM calls), enabling deadlock detection, guard conditions, and formal verification on any workflow — with any model.

Inspired by **TB-CSPN** (Borghoff et al., 2025): [doi.org/10.3390/fi17080363](https://www.mdpi.com/1999-5903/17/8/363)

---

## Overview

### The Problem

Current agentic AI frameworks conflate semantic reasoning with orchestration:
- Every coordination decision = 1 LLM API call
- No formal verification
- No deadlock detection
- Workflow state not verifiable

### The Solution

Cortex separates concerns:

```
USER INPUT
        │
   1. SEMANTIC (LLM)
      - Intent classification
      - One call per message
        │
   2. RULES (Local)
      - Map intent → action
      - Zero LLM calls
        │
   3. PETRI NET (Formal)
      - State machine execution
      - Deadlock detection
      - Guard conditions
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Deadlock Detection** | Formal verification of workflow liveness |
| **Guard Conditions** | Preconditions for transitions |
| **Boundedness Check** | Workflows validated at load time |
| **Ambiguous Intent Handling** | Configurable fallback policies |
| **Session Context** | Historical turns for better classification |

---

## Installation

```bash
git clone https://github.com/lorcann-rauzduel/cortex.git
cd cortex
pip install fastapi uvicorn pydantic pyyaml networkx httpx pytest
```

### LLM Setup (Any Model Works)

Cortex is **model-agnostic**:

```bash
# Ollama (local, free)
ollama pull llama3.2
ollama pull gemma4:e4b
ollama pull phi4
```

```python
# Or use a remote API
config = {'provider': 'openai', 'model': 'gpt-4o', 'api_key': 'sk-...'}

# Or no LLM at all
orchestrator = CortexOrchestrator(use_llm=False)
```

---

## Quick Start

```python
from orchestrator import CortexOrchestrator

orchestrator = CortexOrchestrator(use_llm=True)
orchestrator.initialize()
orchestrator.load_workflow('task_approval', 'workflows/task_approval.yaml')

result = orchestrator.orchestrate(
    message="Approve task T-123",
    workflow_id='task_approval'
)
```

### API

```bash
cd src
uvicorn api.routes:app --reload --port 8000
```

```bash
curl -X POST http://localhost:8000/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a new task", "workflow_id": "task_approval"}'
```

---

## Architecture

### Semantic Layer (LLM)

Classifies user intent:

```python
# Input: "Reject the deployment"
# Output:
{
    "intent": "REJECT",
    "topics": ["approval"],
    "entities": {"id": "deployment_456"},
    "confidence": 0.95
}
```

**Ambiguous Intent Handling:**
- `confidence > threshold` → proceed normally
- `confidence < threshold` → configurable policy:
  - `FALLBACK`: Use default intent
  - `CLARIFY`: Return `AMBIGUOUS_INTENT` state
  - `SUSPEND`: Pause workflow

### Rule Engine (Local)

Maps semantic context to actions:

```python
Rule(
    condition=RuleCondition(intent="APPROVE"),
    action=RuleAction.FIRE_TRANSITION,
    target="approve"
)
```

**Conditional Transitions (LLM-evaluated):**
```python
# For decisions requiring judgment:
guard_type: "llm_evaluated"
guard_prompt: "Is this report complete enough to proceed? Answer yes or no."
```

### Petri Net Engine (Formal)

State machine with formal guarantees:

```
Places:     created → pending_review → pending_approval → approved
            │                                        │
            └───────────── reject ──────────────────┘

Features:
- Boundedness validation at load time
- Deadlock detection
- Guard conditions
- DOT export for visualization
```

---

## Workflow Definition

```yaml
name: "task_approval"

places:
  - id: "created"
    type: "initial"
  - id: "pending_review"
  - id: "pending_approval"
  - id: "approved"
    type: "final"
  - id: "rejected"
    type: "final"

transitions:
  - id: "create"
    from: ["created"]
    to: "pending_review"
    action: "create"
  - id: "approve"
    from: ["pending_approval"]
    to: "approved"
    action: "approve"
```

### Guard Conditions

```yaml
transitions:
  - id: "escalate"
    from: ["pending_review"]
    to: "pending_approval"
    guard:
      type: "deterministic"
      condition: "amount > 1000"
    
  - id: "evaluate"
    from: ["submitted"]
    to: "review_ok"
    guard:
      type: "llm_evaluated"
      prompt: "Is this expense report complete? yes or no."
```

---

## Use Cases

### Business Process Automation
```yaml
# Expense approval with auto-escalation
guard: "amount > 1000"
```

### Conversational Assistants
```
User: "Cancel order #12345"
LLM: intent=CANCEL, entity=order_12345
Rules: CANCEL + order → fire_transition("cancel")
Petri: Verify → Cancel → Confirm
```

### Multi-Agent Systems
```
[Agent-1] ──topic:request──→ [Agent-2]
                                │
                            Petri Net
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
               [Agent-3]              [Agent-4]
```

### DevOps / CI-CD Pipelines
```yaml
# Deployment with rollback
guard:
  type: "deterministic"
  condition: "test_results.passed == false"
transition: "rollback"
```

### Customer Support
```
User: "Refund for order #789"
LLM: intent=REFUND, entity=order_789
Rules: REFUND → fire_transition("process_refund")
Petri: Check → Calculate → Process → Notify
```

---

## Configuration

### Ambiguous Intent Policy

```python
orchestrator = CortexOrchestrator(
    use_llm=True,
    intent_config={
        'confidence_threshold': 0.7,
        'on_ambiguous': 'CLARIFY'  # FALLBACK, CLARIFY, SUSPEND
    }
)
```

### Session Context

```python
# Pass conversation history to semantic layer
result = orchestrator.orchestrate(
    message="Actually, cancel it",
    session_id="support_123",
    context={'turn_history': [
        "I want to place an order",
        "Here's your order #456",
        "Actually, cancel it"
    ]}
)
```

### LLM-Evaluated Guards

```python
# For decisions requiring judgment
orchestrator.workflow_engine.register_llm_guard(
    name="report_complete",
    prompt="Is this report complete enough to proceed to review?",
    llm_config={'model': 'llama3.2'}
)
```

---

## Testing

```bash
pytest tests/ -v
```

---

## Requirements

- Python 3.11+

**For local LLM:**
- Ollama installed
- Any model (tested: llama3.2, gemma4:e4b, phi4)

**For API-based LLM:**
- API key for OpenAI/Anthropic/etc.

**Without LLM:**
- Use `use_llm=False` for mock mode

---

## Key Differences from Traditional Frameworks

Based on TB-CSPN findings:

| Aspect | Traditional | **Cortex** |
|--------|-----------|------------|
| Semantic/Coordination | Conflated | **Separated** |
| Formal Verification | ❌ | ✅ |
| Deadlock Detection | ❌ | ✅ |
| Workflow Boundedness | ❌ | ✅ |
| Guard Conditions | Limited | **Full + LLM-evaluated** |

---

## Reference

**Borghoff, U. M., Bottoni, P., & Pareschi, R. (2025)**  
*Beyond Prompt Chaining: The TB-CSPN Architecture for Agentic AI*  
Future Internet, 17(8), 363.  
[doi.org/10.3390/fi17080363](https://www.mdpi.com/1999-5903/17/8/363)

---

## License

MIT License - See [LICENSE](LICENSE)
