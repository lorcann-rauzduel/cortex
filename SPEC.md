# Cortex: Moteur d'Orchestration Hybride Neuro-Symbolique

## Concept & Vision

Cortex implémente une architecture **strictement découplée** pour les agents IA:
- **Cerveau gauche (Symbolique)**: Réseaux de Petri pour coordination formelle, déterministe, vérifiable
- **Cerveau droit (Neuro)**: Petit LLM (Llama-3.2) pour compréhension sémantique de l'intention

L'agent **pense** avec un modèle léger (compréhension), mais **agit** selon des workflows validés mathématiquement (coordination).

Inspiré de TB-CSPN (Borghoff et al., 2025) mais simplifié pour un prototype recherche.

## Architecture Globale

```
┌─────────────────────────────────────────────────────────────┐
│                    COUCHE MÉTA (Orchestrateur)              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐      ┌─────────────────────────────┐  │
│  │  COUCHE         │      │  COUCHE                      │  │
│  │  SÉMANTIQUE     │──────│  COORDINATION               │  │
│  │  (Llama-3.2)    │  ↑   │  (Réseau de Petri)          │  │
│  │                 │  │   │                             │  │
│  │  • Intention    │  │   │  • Transitions formelles    │  │
│  │  • Topics       │  │   │  • Places/Tokens           │  │
│  │  • Contexte     │  │   │  • Vérification deadlock    │  │
│  └─────────────────┘  │   └─────────────────────────────┘  │
│         ↓             │                                   │
│  ┌─────────────────┐  │                                   │
│  │  MOTEUR DE      │──┘                                   │
│  │  RÈGLES         │                                      │
│  │  Neuro-symbolique│                                     │
│  └─────────────────┘                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Modules

### 1. Semantic Layer (`src/semantic/`)

**Responsabilité**: Comprendre l'intention utilisateur via Llama-3.2

**Fonctions**:
- `IntentClassifier`: Extrait l'intention (CREATE_TASK, APPROVE, QUERY, etc.)
- `TopicExtractor`: Identifie les topics pertinents pour router vers les workflows
- `ContextAnalyzer`: Contexte conversationnel pour désambiguïsation

**Interface**:
```python
class SemanticResult:
    intent: IntentType
    topics: List[str]
    entities: Dict[str, Any]
    confidence: float
    raw_reasoning: str
```

### 2. Coordination Layer (`src/coordination/`)

**Responsabilité**: Exécution formelle des workflows via Petri Nets

**Concepts**:
- **Place**: État du système (en attente, en cours, terminé, erreur)
- **Transition**: Action atomique (valider, rejeter, notifier)
- **Token**: Données transitant dans le réseau
- **Arc**: Flux entre places et transitions

**Fonctions**:
- `PetriNetEngine`: Exécution du réseau
- `TransitionValidator`: Vérifie pré-conditions/post-conditions
- `DeadlockDetector`: Détection de blocages formels
- `StateSerializer`: Persistance d'état

### 3. Rules Engine (`src/rules/`)

**Responsabilité**: Pont neuro-symbolique entre intention et coordination

**Règles**:
```python
Rule:
  IF semantic.intent == "APPROVE" 
  AND context.role == "MANAGER"
  AND workflow.state == "PENDING_APPROVAL"
  THEN fire_transition("approve")
```

**Fonctions**:
- `RuleEngine`: Évaluation des règles
- `RuleCompiler`: Compilation des règles YAML → exécutable
- `ConflictResolver`: Résolution d'ambiguïtés

### 4. API Layer (`src/api/`)

**Endpoints FastAPI**:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/orchestrate` | Orchestrer une requête utilisateur |
| GET | `/workflow/{id}` | État d'un workflow |
| POST | `/workflow` | Créer un nouveau workflow |
| GET | `/petri/net/{id}` | Visualiser le réseau de Petri |
| POST | `/rules/reload` | Recharger les règles |

## Format des Workflows (YAML)

```yaml
name: "task_approval"
description: "Workflow d'approbation de tâche"

places:
  - id: "created"
    type: "initial"
  - id: "pending_review"
  - id: "pending_approval"
  - id: "approved"
    type: "final"
  - id: "rejected"

transitions:
  - id: "submit"
    from: ["created"]
    to: "pending_review"
    guard: "has_description"
  - id: "escalate"
    from: ["pending_review"]
    to: "pending_approval"
    guard: "requires_approval"
  - id: "approve"
    from: ["pending_approval"]
    to: "approved"
  - id: "reject"
    from: ["pending_approval"]
    to: "rejected"

rules:
  - trigger: "submit"
    condition:
      intent: "CREATE"
      topic: "task"
    action: "fire"
```

## Flux d'Exécution

```
1. INPUT: "Je veux approuver la tâche T-123"
                    ↓
2. SEMANTIC: Llama-3.2 extrait
   - intent: APPROVE
   - topic: task
   - entity: T-123
                    ↓
3. RULES: Matching avec workflows actifs
   - Rule: IF intent=APPROVE AND topic=task
   - Action: fire_transition("approve")
                    ↓
4. COORDINATION: Réseau de Petri
   - Vérifie pré-conditions
   - Fire transition "approve"
   - Met à jour état → "approved"
   - Émet token vers workflow suivant
                    ↓
5. OUTPUT: { status: "success", new_state: "approved" }
```

## Critères de Succès

1. **Découplage vérifiable**: Le LLM ne prend jamais de décisions de coordination
2. **Vérifiabilité**: Chaque workflow peut être model-checké
3. **Réduction LLM**: Intentions résolues en 1 appel LLM, coordination 0 appel
4. **Testabilité**: Simulation de workflows sans LLM

## Stack Technique

- **Python 3.11+**
- **FastAPI** (API REST)
- **Llama-cpp-python** (inférence Llama-3.2 locale)
- **NetworkX** (modélisation Petri Net)
- **PyYAML** (définition workflows)
- **pytest** (tests)

## Livrables

```
cortex/
├── SPEC.md
├── pyproject.toml
├── src/
│   ├── __init__.py
│   ├── semantic/
│   │   ├── __init__.py
│   │   ├── intent_classifier.py
│   │   └── llama_client.py
│   ├── coordination/
│   │   ├── __init__.py
│   │   ├── petri_net.py
│   │   └── workflow_engine.py
│   ├── rules/
│   │   ├── __init__.py
│   │   ├── rule_engine.py
│   │   └── rule_loader.py
│   └── api/
│       ├── __init__.py
│       └── routes.py
├── workflows/
│   └── examples/
├── tests/
└── README.md
```
