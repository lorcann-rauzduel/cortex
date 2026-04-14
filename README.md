# Cortex - Neuro-Symbolic Orchestration Engine

A hybrid neuro-symbolic orchestration engine that separates semantic understanding (LLM) from formal coordination (Petri Nets). Inspired by **TB-CSPN architecture** (Borghoff et al., 2025).

**Paper**: [Beyond Prompt Chaining: The TB-CSPN Architecture for Agentic AI](https://www.mdpi.com/1999-5903/17/8/363)

---

## Overview

### The Problem

Current agentic AI frameworks **conflate** semantic reasoning with orchestration:
- Every coordination decision = 1 LLM API call
- No formal verification
- Brittle prompt dependencies

### The Solution

Cortex implements **strict separation**:

```
USER INPUT: "Approve task T-123"
                │
        ┌───────┴───────┐
        │               │
   1. SEMANTIC      2. RULES
   (LLM)           (Mapping)
        │               │
        └───────┬───────┘
                │
        3. PETRI NET
      (Coordination)
```

### Results (from TB-CSPN study)

| Metric | Traditional | Cortex |
|--------|-------------|--------|
| LLM calls (10-step workflow) | 10 | 1 |
| Coordination latency | LLM (2-30s) | <1ms (local) |
| Formal verification | ❌ | ✅ |
| Deadlock detection | ❌ | ✅ |

---

## Installation

```bash
git clone https://github.com/lorcann-rauzduel/cortex.git
cd cortex
pip install fastapi uvicorn pydantic pyyaml networkx httpx pytest
```

### LLM Setup (Any Model Works)

Cortex is **model-agnostic**. Use any LLM via Ollama or direct API:

```bash
# Ollama (recommended - local, free)
# Install from https://ollama.com
ollama pull llama3.2     # fast, 4GB
ollama pull gemma4:e4b    # powerful, 6GB
ollama pull phi4          # small, 3GB
ollama pull qwen2.5       # multilingual
```

**Or use remote APIs:**
```python
# OpenAI
config = {'provider': 'openai', 'model': 'gpt-4o', 'api_key': 'sk-...'}

# Anthropic  
config = {'provider': 'anthropic', 'model': 'claude-3-5-sonnet', 'api_key': 'sk-...'}

# Ollama (any local model)
config = {'provider': 'ollama', 'model': 'any-model-you-have'}

# Or just use the mock classifier (no LLM needed)
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

print(f"Intent: {result.intent}")      # APPROVE
print(f"Action: {result.action_taken}") # approve
print(f"State: {result.new_state}")    # workflow state
```

### API

```bash
cd src
uvicorn api.routes:app --reload --port 8000
```

```bash
# Semantic classification
curl -X POST http://localhost:8000/semantic/classify \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a new task"}'

# Full orchestration
curl -X POST http://localhost:8000/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"message": "Approve the report", "workflow_id": "task_approval"}'
```

---

## Architecture

### Semantic Layer (`src/semantic/`)

Understands user intent via LLM:

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

### Rule Engine (`src/rules/`)

Maps semantic context to coordination actions:

```python
Rule(
    condition=RuleCondition(intent="APPROVE"),
    action=RuleAction.FIRE_TRANSITION,
    target="approve"
)
```

### Petri Net Engine (`src/coordination/`)

Formal coordination:

```
Places:     created → pending_review → pending_approval → approved
            │                                        │
            └───────────── reject ────────────────────┘

Transitions: [create] [submit] [approve/reject]
```

Features:
- Deadlock detection
- Guard conditions
- DOT export for visualization

---

## Workflow Definition

```yaml
# workflows/task_approval.yaml
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

---

## Testing

```bash
pytest tests/ -v
```

---

## Project Structure

```
cortex/
├── SPEC.md                    # TB-CSPN specification
├── README.md                  # This file
├── pyproject.toml
├── src/
│   ├── orchestrator.py        # Main orchestrator
│   ├── semantic/              # LLM integration
│   ├── coordination/          # Petri Net engine
│   ├── rules/                 # Rule engine
│   └── api/                   # FastAPI routes
├── workflows/                 # YAML definitions
└── tests/                    # Unit tests
```

---

## Use Cases

### Business Process Automation
```yaml
# Expense approval with auto-escalation
guard: "amount > 1000"  # Escalate large expenses
```

### Multi-Agent Coordination
```
[Agent-1] ──topic:request──→ [Agent-2] ──Petri Net──→ [Supervisor]
```

### Conversational Assistants
```
User: "Cancel order #12345"
LLM: intent=CANCEL, entity=order_12345
Rules: CANCEL + order → fire_transition("cancel")
Petri: Verify → Cancel → Confirm
```

---

## Requirements

- Python 3.11+

**For local LLM (recommended):**
- Ollama installed
- Any model you want (tested: llama3.2, gemma4:e4b, phi4)

**For API-based LLM:**
- API key for OpenAI/Anthropic/etc.

**Without LLM:**
- Use `use_llm=False` for mock mode (no API key needed)

---

## Key Differences from Traditional Frameworks

Based on TB-CSPN findings:

| Aspect | Traditional | **Cortex** |
|--------|-----------|------------|
| Semantic/Coordination | Conflated | **Separated** |
| LLM for coordination | Every step | **Only for intent** |
| Formal verification | ❌ | ✅ |

---

## Use Cases

### Business Process Automation
```yaml
# Expense approval workflow
places:
  - id: "submitted"
  - id: "manager_review"
  - id: "finance_review"
  - id: "approved"

# Auto-escalate large expenses
guard: "amount > 1000"
```

### Conversational Assistants
```
User: "I need to cancel my order #12345"

LLM: intent=CANCEL, entity=order_12345
Rules: CANCEL + order → fire_transition("cancel_order")
Petri: Verify status → Process → Send confirmation
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
                    │                       │
                    └───────────┬───────────┘
                                ▼
                          [Supervisor]
```

### DevOps / CI-CD Pipelines
```yaml
# Deployment pipeline
places:
  - id: "build"
  - id: "test"
  - id: "staging"
  - id: "production"
  - id: "rollback"

# Auto-rollback on failure
guard: "test_results.passed == false"
transition: "rollback"
```

### Customer Support
```
User: "I want a refund for order #789"
LLM: intent=REFUND, entity=order_789, topic=support
Rules: REFUND + pending → fire_transition("process_refund")
Petri: Check eligibility → Calculate → Process → Notify
```

### Trading Systems (from original TB-CSPN paper)
```
Market data → LLM extracts intent → Rules map to strategy
Petri Net: Validates → Executes → Monitors → Alerts
```

---

## Reference

**Borghoff, U. M., Bottoni, P., & Pareschi, R. (2025)**  
*Beyond Prompt Chaining: The TB-CSPN Architecture for Agentic AI*  
Future Internet, 17(8), 363.  
[doi.org/10.3390/fi17080363](https://www.mdpi.com/1999-5903/17/8/363)
