# Cortex - Moteur d'Orchestration Hybride Neuro-Symbolique

> **Cortex** implémente une architecture où les agents **pensent** (compréhension sémantique via LLM) mais **agissent** (coordination formelle via réseaux de Petri).

Basé sur l'architecture **TB-CSPN** (Borghoff et al., 2025).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    COUCHE MÉTA (Orchestrateur)              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐      ┌─────────────────────────────┐  │
│  │  COUCHE         │      │  COUCHE                      │  │
│  │  SÉMANTIQUE     │──────│  COORDINATION               │  │
│  │  (Gemma4/Llama)│  ↑   │  (Réseau de Petri)          │  │
│  │                 │  │   │                             │  │
│  │  • Intention    │  │   │  • Transitions formelles    │  │
│  │  • Topics       │  │   │  • Places/Tokens           │  │
│  │  • Contexte     │  │   │  • Vérification deadlock    │  │
│  └─────────────────┘  │   └─────────────────────────────┘  │
│         ↓             │                                   │
│  ┌─────────────────┐  │                                   │
│  │  MOTEUR DE      │──┘                                   │
│  │  RÈGLES         │  Neuro-symbolique                     │
│  │  Neuro-symbolique│                                      │
│  └─────────────────┘                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Principe Fondamental

| Couche | Responsabilité | LLM Calls |
|--------|---------------|-----------|
| **Sémantique** | Comprendre l'intention | 1/message |
| **Règles** | Mapper intent → action | 0 |
| **Coordination** | Exécuter workflow (Petri Net) | 0 |

## Installation

```bash
# Cloner le repo
git clone https://github.com/lorcann-rauzduel/cortex.git
cd cortex

# Installer les dépendances
pip install fastapi uvicorn pydantic pyyaml networkx httpx pytest
```

### Avec Ollama (optionnel)

```bash
# Installer Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Télécharger un modèle
ollama pull gemma4:e4b
# ou
ollama pull llama3.2

# Vérifier
ollama list
```

## Utilisation Rapide

### Mode Mock (sans LLM)

```python
from orchestrator import CortexOrchestrator

orchestrator = CortexOrchestrator(use_llm=False)
orchestrator.initialize()

# Classification d'intention
result = orchestrator.orchestrate("Approuver la tâche T-123")
print(result.intent)  # APPROVE
```

### Avec Ollama

```python
orchestrator = CortexOrchestrator(
    use_llm=True,
    llm_config={'provider': 'ollama', 'model': 'gemma4:e4b'}
)
orchestrator.initialize()

result = orchestrator.orchestrate("Créer une nouvelle tâche")
print(result.intent)  # CREATE
```

### API REST

```bash
cd src
uvicorn api.routes:app --reload --port 8000
```

```bash
# Classification sémantique
curl -X POST http://localhost:8000/semantic/classify \
  -H "Content-Type: application/json" \
  -d '{"message": "Approuver la demande"}'

# Orchestration complète
curl -X POST http://localhost:8000/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"message": "Créer une tâche", "workflow_id": "task_approval"}'

# État du workflow
curl http://localhost:8000/workflow/task_approval/state/instance123
```

## Structure du Projet

```
cortex/
├── SPEC.md                      # Spécification architecture TB-CSPN
├── README.md                    # Ce fichier
├── pyproject.toml              # Configuration Python
├── src/
│   ├── orchestrator.py         # Orchestrateur principal
│   ├── semantic/               # Couche sémantique (LLM)
│   │   ├── intent_classifier.py
│   │   └── llm_client.py      # Client Ollama/llama-cpp
│   ├── coordination/           # Couche coordination (Petri Net)
│   │   └── petri_net.py       # Colored Petri Net Engine
│   ├── rules/                  # Moteur de règles
│   │   └── rule_engine.py      # Règles neuro-symboliques
│   └── api/
│       └── routes.py           # API FastAPI
├── workflows/                   # Définitions YAML
│   ├── task_approval.yaml     # Workflow approbation
│   └── simple_query.yaml
└── tests/                      # Tests unitaires (41 tests)
```

## Référence Technique

### TB-CSPN: Topic-Based Communication Space Petri Net

L'architecture TB-CSPN (Borghoff et al., 2025) propose:

1. **Séparation sémantique-coordination**
   - LLM = extraction de topics/intentions
   - Petri Net = coordination formelle

2. **Réduction des appels LLM**
   - TB-CSPN original: -66.7% d'appels LLM vs LangGraph
   - Principe: coordination déterministe → 0 appel LLM

3. **Propriétés formelles**
   - Vérification deadlock possible
   - Model-checking sur les workflows
   - Traçabilité complète des états

### Petri Net (Réseau de Petri)

```python
# Places: états du système
Place(id="created", type="initial")    # État initial
Place(id="pending_approval")            # En attente
Place(id="approved", type="final")      # État final

# Transitions: actions atomiques
Transition(id="approve", from=["pending_approval"], to="approved")
```

### Moteur de Règles

```python
Rule(
    name="approve_action",
    condition=RuleCondition(intent="APPROVE"),
    action=RuleAction.FIRE_TRANSITION,
    target="approve",
    priority=10
)
```

**Évaluation**: `IF intent=APPROVE THEN fire_transition("approve")`

## Tests

```bash
# Tous les tests
pytest tests/ -v

# Couverture
pytest tests/ --cov=src --cov-report=html
```

**41 tests** couvrant:
- Petri Net Engine
- Rule Engine
- Intent Classifier (Mock + Ollama)
- Orchestrator (intégration)

## Cas d'Usage

### 1. Workflows Métier

```yaml
# workflows/approval.yaml
name: "approval_process"
places:
  - id: "submitted"
  - id: "pending_manager"
  - id: "approved"
  - id: "rejected"
transitions:
  - id: "escalate"
    from: ["submitted"]
    to: "pending_manager"
  - id: "approve"
    from: ["pending_manager"]
    to: "approved"
  - id: "reject"
    from: ["pending_manager"]
    to: "rejected"
```

### 2. Chatbot Orchestration

```
User: "Résoudre le problème #123"
     ↓
LLM: intent=RESOLVE, entity=123
     ↓
Rules: RESOLVE + ticket → fire_transition("resolve")
     ↓
Petri Net: Vérifie état → Execute transition → Met à jour BDD
```

### 3. Multi-Agents

```
[Agent-1] ──topic:request──→ [Agent-2]
                              ↓
                         Petri Net coordonne
                              ↓
                         [Supervisor] validation
```

## Comparaison

| Critère | LangGraph/AutoGen | Cortex |
|---------|------------------|--------|
| LLM pour coordination | Oui (chaque étape) | **Non** (Petri Net) |
| Vérifiabilité formelle | Non | **Oui** |
| Découplage sémantique/coordination | Non | **Oui** |
| LLM calls (10 étapes) | 10 | **1** |
| Latence coordination | LLM (2-30s) | **~0ms** (local) |

## Benchmarks (simulés)

```
Configuration: MacBook M3, Ollama local
Modèle: gemma4:e4b (8B params)

Intent Classification (Gemma4):
  - Latence: 8-30s (selon modèle)
  - Throughput: ~2-4 req/min

Coordination (Petri Net):
  - Latence: <1ms
  - Throughput: >10000 ops/s

Total: 1 LLM call + N transitions locales
```

## Étude: TB-CSPN et Neuro-Symbolic AI

### Problématique

Les frameworks agentiques actuels (LangGraph, AutoGen):
- **Conflation** sémantique et coordination
- Chaque décision = 1 appel LLM
- Pas de vérification formelle
- Prompts fragiles

### Solution TB-CSPN

1. **Architecture séparée**
   - Couche sémantique: LLM pour comprendre
   - Couche coordination: Petri Net pour agir

2. **Réduction drastique des coûts**
   - -66.7% appels LLM (TB-CSPN original)
   - Coordination locale (0 coût LLM)

3. **Garanties formelles**
   - Model-checking sur workflows
   - Détection deadlock
   - Traçabilité

### Implémentation Cortex

| Composant | Implémentation | Inspiration |
|-----------|----------------|-------------|
| Semantic Layer | Ollama/llama-cpp | TB-CSPN Semantic Space |
| Rule Engine | Pattern matching | TB-CSPN Topic Mapping |
| Petri Net | NetworkX + custom | TB-CSPN Coordination Net |
| API | FastAPI | RESTful pour agents |

## Licence

MIT License - Voir [LICENSE](LICENSE)

## Références

- Borghoff, U. M., Bottoni, P., & Pareschi, R. (2025). Beyond Prompt Chaining: The TB-CSPN Architecture for Agentic AI. *Future Internet*, 17(8), 363. https://doi.org/10.3390/fi17080363
