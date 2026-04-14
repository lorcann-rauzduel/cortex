# Cortex - Neuro-Symbolic Orchestration Engine

> **"Think" with AI. "Act" with formal methods.**

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

### Ollama (for local LLM)

```bash
# Install Ollama from https://ollama.com
ollama pull gemma4:e4b   # 6GB VRAM
# or
ollama pull llama3.2     # faster
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

### Minimum
- Python 3.11+
- 4GB RAM

### Recommended (for local LLM)
- 8GB+ RAM
- 6GB+ VRAM GPU (GTX 1060 or better)
- Ollama with gemma4:e4b or llama3.2

> Tested on: Intel i7-7700HQ, 16GB RAM, GTX 1060 6GB

---

## Key Differences from Traditional Frameworks

Based on TB-CSPN findings:

| Aspect | Traditional | **Cortex** |
|--------|-----------|------------|
| Semantic/Coordination | Conflated | **Separated** |
| LLM for coordination | Every step | **Only for intent** |
| Formal verification | ❌ | ✅ |

---

## Future Work

- [ ] Model checking integration (PNML export)
- [ ] Visual workflow editor
- [ ] Distributed Petri Net execution
- [ ] Temporal logic guards (LTL/CTL)

---

## Reference

**Borghoff, U. M., Bottoni, P., & Pareschi, R. (2025)**  
*Beyond Prompt Chaining: The TB-CSPN Architecture for Agentic AI*  
Future Internet, 17(8), 363.  
[doi.org/10.3390/fi17080363](https://www.mdpi.com/1999-5903/17/8/363)
