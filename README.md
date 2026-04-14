# Cortex - Neuro-Symbolic Orchestration Engine

> **"Think" with AI. "Act" with formal methods.**

Cortex is a hybrid neuro-symbolic orchestration engine that separates semantic understanding (LLM) from formal coordination (Petri Nets). Inspired by **TB-CSPN architecture** (Borghoff et al., 2025).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)

---

## 📖 Overview

### The Problem

Current agentic AI frameworks (LangGraph, AutoGen) **conflate** semantic reasoning with orchestration:
- Every coordination decision = 1 LLM API call
- No formal verification
- Brittle prompt dependencies
- Cost: $0.01-0.10 per workflow step

### The Solution

Cortex implements **strict separation**:

```
┌─────────────────────────────────────────────────────────────────┐
│                         CORTEX                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   USER INPUT: "Approve task T-123"                              │
│                    │                                             │
│                    ▼                                             │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  1. SEMANTIC LAYER (LLM)                              │   │
│   │     - Intent: APPROVE                                   │   │
│   │     - Entity: T-123                                     │   │
│   │     → 1 API call                                        │   │
│   └─────────────────────────────────────────────────────────┘   │
│                    │                                             │
│                    ▼                                             │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  2. RULE ENGINE (Neuro-Symbolic)                       │   │
│   │     - IF intent=APPROVE → fire_transition("approve")   │   │
│   │     → 0 API calls                                       │   │
│   └─────────────────────────────────────────────────────────┘   │
│                    │                                             │
│                    ▼                                             │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  3. PETRI NET (Formal Coordination)                    │   │
│   │     - Verify preconditions                              │   │
│   │     - Fire transition                                   │   │
│   │     - Update state                                      │   │
│   │     → 0 API calls, <1ms latency                        │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Results (from TB-CSPN study)

| Metric | Traditional (LLM-coordination) | Cortex (TB-CSPN) |
|--------|------------------------------|------------------|
| LLM calls (10-step workflow) | 10 | 1 |
| Coordination latency | 2-30s (LLM) | <1ms (local) |
| Formal verification | ❌ | ✅ |
| Deadlock detection | ❌ | ✅ |

> Source: [TB-CSPN paper](https://www.mdpi.com/1999-5903/17/8/363) - Section 6

---

## 🔬 Research Background

### TB-CSPN: Topic-Based Communication Space Petri Net

**Paper**: [Beyond Prompt Chaining: The TB-CSPN Architecture for Agentic AI](https://www.mdpi.com/1999-5903/17/8/363)  
**Authors**: Uwe M. Borghoff, Paolo Bottoni, Remo Pareschi  
**Published**: Future Internet, 2025

### Key Insights from TB-CSPN

1. **Architectural Separation**: LLMs handle semantic processing (topic extraction), while Petri Net semantics manage coordination deterministically

2. **Reduced LLM Dependency**: TB-CSPN achieves 66.7% fewer LLM API calls compared to LangGraph-style orchestration

3. **Formal Verification**: Built on Colored Petri Net foundations, enabling mathematical verification of coordination properties

4. **Sub-linear Scaling**: Memory scaling demonstrates 10x efficiency improvement per agent compared to traditional systems

### Why Petri Nets?

- **Formal semantics**: Well-understood mathematical foundation
- **Verification**: Deadlock freedom, liveness, bounded response times
- **Visualization**: Graphical representation of workflows
- **Model checking**: Tools like CPN Tools for formal analysis

### Why Neuro-Symbolic?

- **LLMs**: Excellent at understanding intent, nuance, ambiguity
- **Symbolic**: Perfect for deterministic coordination, verification
- **Hybrid**: Best of both worlds

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- 8GB+ RAM (16GB recommended)
- GPU: NVIDIA with 6GB+ VRAM (GTX 1060 works!)

### Installation

```bash
# Clone the repository
git clone https://github.com/lorcann-rauzduel/cortex.git
cd cortex

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install fastapi uvicorn pydantic pyyaml networkx httpx pytest
```

### With Ollama (Recommended for Local LLM)

```bash
# Install Ollama
# Linux/Mac:
curl -fsSL https://ollama.com/install.sh | sh

# Windows: Download from https://ollama.com/download

# Pull a model (6GB VRAM = gemma4:e4b or llama3.2)
ollama pull gemma4:e4b
# or for faster inference:
ollama pull llama3.2

# Verify
ollama list
```

### Your First Orchestration

```python
from orchestrator import CortexOrchestrator

# Initialize (uses Ollama if available, mock otherwise)
orchestrator = CortexOrchestrator(
    use_llm=True,
    llm_config={'provider': 'ollama', 'model': 'gemma4:e4b'}
)
orchestrator.initialize()

# Load a workflow
orchestrator.load_workflow('task_approval', 'workflows/task_approval.yaml')

# Orchestrate!
result = orchestrator.orchestrate(
    message="Approve task T-123",
    workflow_id='task_approval'
)

print(f"Intent: {result.intent}")      # APPROVE
print(f"Action: {result.action_taken}") # approve
print(f"Success: {result.success}")     # True/False
print(f"State: {result.new_state}")     # {'active_places': ['approved'], ...}
```

---

## 📡 API Reference

### Start the Server

```bash
cd cortex/src
uvicorn api.routes:app --reload --host 0.0.0.0 --port 8000
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Service info |
| `GET` | `/health` | Health check |
| `POST` | `/orchestrate` | Main orchestration endpoint |
| `POST` | `/semantic/classify` | Intent classification only |
| `GET` | `/workflows` | List loaded workflows |
| `POST` | `/workflows` | Load a workflow from YAML |
| `GET` | `/workflow/{id}/state/{instance}` | Get workflow state |
| `POST` | `/workflow/fire` | Fire a transition |
| `GET` | `/rules` | List active rules |
| `GET` | `/session/{id}` | Get session state |

### API Examples

```bash
# Health check
curl http://localhost:8000/health

# Semantic classification
curl -X POST http://localhost:8000/semantic/classify \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a new task for tomorrow"}'

# Full orchestration
curl -X POST http://localhost:8000/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Approve the expense report",
    "workflow_id": "task_approval"
  }'

# Get workflow state
curl http://localhost:8000/workflow/task_approval/state/instance_123
```

---

## 🏗️ Architecture Deep Dive

### 1. Semantic Layer (`src/semantic/`)

**Responsibility**: Understand user intent using LLM

```python
# Input: "Reject the deployment request"
# Output:
{
    "intent": "REJECT",
    "topics": ["approval"],
    "entities": {"id": "request_456"},
    "confidence": 0.95
}
```

**Supported Providers**:
- **Ollama** (default): Local inference via HTTP API
- **llama-cpp-python**: Direct GGUF model loading
- **Mock**: Keyword-based fallback for development

### 2. Rule Engine (`src/rules/`)

**Responsibility**: Map semantic context to coordination actions

```python
Rule(
    name="approve_action",
    description="Approve pending item",
    condition=RuleCondition(intent="APPROVE"),
    action=RuleAction.FIRE_TRANSITION,
    target="approve",
    priority=10,
    guard="is_manager"  # Optional condition
)
```

**Rule Evaluation**:
```
IF semantic.intent == "APPROVE"
AND workflow.current_place == "pending_approval"
THEN fire_transition("approve")
```

### 3. Petri Net Engine (`src/coordination/`)

**Responsibility**: Formal coordination of workflow execution

```
Places (States):
  ○ created        (initial)
  ○ pending_review
  ○ pending_approval
  ● approved       (final)
  ● rejected       (final)

Transitions (Actions):
  [create]    created → pending_review
  [submit]    pending_review → pending_approval
  [approve]   pending_approval → approved
  [reject]    pending_approval → rejected
```

**Features**:
- Deadlock detection
- Guard conditions
- Token-based state
- DOT export for visualization

---

## 📁 Workflow Definition

Workflows are defined in YAML:

```yaml
# workflows/task_approval.yaml
name: "task_approval"
description: "Task approval workflow with manager review"

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
    description: "Create new task"

  - id: "submit"
    from: ["pending_review"]
    to: "pending_approval"
    guard: "requires_approval"
    action: "submit"
    description: "Submit for approval"

  - id: "approve"
    from: ["pending_approval"]
    to: "approved"
    action: "approve"
    description: "Approve task"

  - id: "reject"
    from: ["pending_approval"]
    to: "rejected"
    action: "reject"
    description: "Reject task"
```

---

## 🧪 Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Test Coverage

| Module | Tests | Coverage |
|--------|-------|----------|
| Petri Net Engine | 13 | 95% |
| Rule Engine | 10 | 92% |
| Semantic Layer | 9 | 88% |
| Orchestrator | 9 | 85% |
| **Total** | **41** | **90%** |

### Manual Testing

```bash
# Mock mode (instant, no LLM)
python src/test_demo.py

# Ollama mode (actual LLM inference)
python src/test_ollama.py
```

---

## 💻 Hardware Requirements & Performance

### Tested Configuration

| Component | Specification |
|-----------|---------------|
| CPU | Intel i7-7700HQ @ 2.8GHz |
| RAM | 16 GB DDR4 |
| GPU | NVIDIA GTX 1060 6GB |
| Storage | 256GB SSD + 1TB HDD |
| OS | Windows 10/11 |

### Performance Benchmarks

| Operation | Latency | Throughput |
|-----------|---------|------------|
| Intent Classification (Gemma4) | 8-30s | 2-4 req/min |
| Intent Classification (Llama3.2) | 3-8s | 8-15 req/min |
| Petri Net Transition | <1ms | >10,000 ops/s |
| Rule Evaluation | <0.1ms | >100,000 ops/s |

### GPU Memory Usage

| Model | VRAM | quantization |
|-------|------|--------------|
| gemma4:e4b | ~6GB | Q4_K_M |
| llama3.2 | ~4GB | Q4_K_M |
| phi4 | ~3GB | Q4_K_M |

---

## 🎯 Use Cases

### 1. Business Process Automation

```yaml
# Expense approval workflow
places:
  - id: "submitted"
  - id: "manager_review"
  - id: "finance_review"
  - id: "approved"
  - id: "rejected"

# Auto-escalate if > $1000
guard: "amount > 1000"
```

### 2. Multi-Agent Coordination

```
[User] ──topic:request──→ [Agent-1]
                                │
                            Petri Net
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
               [Agent-2]              [Agent-3]
                    │                       │
                    └───────────┬───────────┘
                                ▼
                          [Supervisor]
```

### 3. Conversational Assistants

```python
# Input: "I need to cancel my order #12345"
# Semantic: intent=CANCEL, entity=order_12345
# Rules: CANCEL + order → fire_transition("cancel_order")
# Petri: Verify status → Process cancellation → Send confirmation
```

### 4. DevOps Automation

```yaml
# CI/CD pipeline
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

---

## 🔧 Configuration

### LLM Configuration

```python
# Ollama (recommended)
config = {
    'provider': 'ollama',
    'model': 'gemma4:e4b',  # or 'llama3.2', 'phi4'
    'ollama_url': 'http://localhost:11434',
    'temperature': 0.3,
    'max_tokens': 256
}

# Direct GGUF loading
config = {
    'provider': 'llama-cpp',
    'model_path': 'models/llama-3.2-3b-instruct-q4_k_m.gguf'
}
```

### Rule Engine Configuration

```python
# Custom rules
orchestrator.rule_engine.add_rule(Rule(
    name="urgent_approval",
    condition=RuleCondition(
        intent="APPROVE",
        topics=["urgent"],
        confidence_min=0.8
    ),
    action=RuleAction.FIRE_TRANSITION,
    target="fast_approve",
    priority=100  # Higher = evaluated first
))

# Guard functions
orchestrator.workflow_engine.register_guard(
    "is_manager",
    lambda ctx: ctx.get("user_role") == "MANAGER"
)
```

---

## 📊 Key Differences from Traditional Agentic Frameworks

Based on TB-CSPN findings:

| Aspect | Traditional (per TB-CSPN) | **Cortex** |
|--------|-------------------------|------------|
| Semantic/Coordination | Conflated | **Separated** |
| LLM for coordination | Every step | **Only for intent** |
| Formal verification | ❌ | ✅ |
| Deadlock detection | ❌ | ✅ |

> See [TB-CSPN paper](https://www.mdpi.com/1999-5903/17/8/363) Section 2.2 for details on traditional approaches

---

## 🔮 Future Work

- [ ] Model checking integration (PNML export)
- [ ] Visual workflow editor
- [ ] Distributed Petri Net execution
- [ ] Integration with LangChain/LangGraph
- [ ] Temporal logic guards (LTL/CTL)
- [ ] WebUI for workflow monitoring

---

## 📚 References

1. **Borghoff, U. M., Bottoni, P., & Pareschi, R. (2025)**  
   *Beyond Prompt Chaining: The TB-CSPN Architecture for Agentic AI*  
   Future Internet, 17(8), 363.  
   [https://doi.org/10.3390/fi17080363](https://www.mdpi.com/1999-5903/17/8/363)

2. **Jensen, K., & Kristensen, L. M. (2009)**  
   *Colored Petri Nets: Modeling and Validation of Concurrent Systems*  
   Springer.

3. **Russell, S., & Norvig, P. (2020)**  
   *Artificial Intelligence: A Modern Approach* (4th ed.)  
   Pearson.

4. **Marcus, G. (2020)**  
   *The Next Decade in AI: Four Steps Towards Robust Artificial Intelligence*  
   arXiv:2004.05107.

---

## 📄 License

MIT License - see [LICENSE](LICENSE)

---

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

---

## 👤 Author

**lorcann-rauzduel**  
GitHub: [@lorcann-rauzduel](https://github.com/lorcann-rauzduel)

---

<p align="center">
  <strong>Built with ❤️ and formal methods</strong>
</p>
