from orchestrator import CortexOrchestrator
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

print('=== Cortex - Full Workflow Test ===')
print()

o = CortexOrchestrator(use_llm=True, llm_config={'provider': 'ollama', 'model': 'gemma4:e4b'})
o.initialize()
o.load_workflow('task_approval', '../workflows/task_approval.yaml')

wf_id = 'task_approval'

print('1. Create task')
r1 = o.orchestrate('Creer une nouvelle tache', workflow_id=wf_id)
print(f'   Intent: {r1.intent}')
print(f'   Success: {r1.success}')
if r1.new_state:
    print(f'   State: {r1.new_state.get("active_places", [])}')
print()

print('2. Submit for approval')
instance_id = r1.workflow_instance_id
o.workflow_engine.fire_by_action(instance_id, 'submit')
state = o.workflow_engine.get_state(instance_id)
print(f'   After submit: {state.get("active_places", [])}')
print()

print('3. Approve')
r2 = o.orchestrate('Approuver maintenant', workflow_id=wf_id)
print(f'   Intent: {r2.intent}')
print(f'   Success: {r2.success}')
if r2.new_state:
    print(f'   State: {r2.new_state.get("active_places", [])}')
    print(f'   Complete: {r2.new_state.get("is_complete", False)}')

print()
print('=== Architecture Demo ===')
print('LLM (Gemma4): 2 calls for intent classification')
print('Petri Net: Formal coordination (no LLM)')
