# Member 1: Executor & Planner Module

## Overview
Member 1 is responsible for decomposing complex user goals into atomic, executable steps and driving their execution via deterministic system tool interfaces (bash, HTTP, file operations). 

### Zero-Trust Execution Rule
Under the zero-trust principles of this architecture, Member 1 **NEVER** marks a step as complete or successful on its own. It acts purely as the execution engine. Upon executing a step, Member 1 transitions the state strictly to `EXECUTED_PENDING_VERIFICATION` (or `SYSTEM_ERROR` in the event of an unhandled runtime exception before execution finishes), collects raw outputs, and defers true verification to the rest of the agent system.

## Interaction with Other Members

### With Member 2 (Evidence)
After Member 1 executes a `Step`, it takes the resulting raw output elements (stdout, exit codes, HTTP payloads, processing durations) and passes them to Member 2 (Evidence). Member 2 evaluates these outputs to mint deterministic, immutable `EvidenceArtifact`s securely containing physical proof of the execution parameters.

### With Member 4 (Healer)
If Member 3 (Verifier) ultimately determines that the executed step failed to achieve the desired outcome, Member 4 formulates a recovery strategy. Member 4 invokes Member 1's `Planner.resequence_plan()` to dynamically mutate the current `ExecutionPlan`, inserting mitigation steps or modifying future execution paths before retrying the step logic.

## Code Example

```python
from shared.models import TaskGoal, StepStatus
from member1_executor import Planner, Executor
from member2_evidence import EvidenceCollector

# 1. Initialize Planner and Executor
planner = Planner()
executor = Executor()
evidence_collector = EvidenceCollector(execution_id="exec-123", agent_id="agent-01")

# 2. Plan the Goal
goal = TaskGoal(goal_id="goal-001", description="Fetch system configuration and save to file.")
plan = planner.create_plan(goal)

# 3. Execute Steps (Zero-Trust Enforcement)
for step in plan.steps:
    if step.status == StepStatus.PENDING:
        # Executor runs the tool and returns raw outputs
        # Note: step.status explicitly shifts to EXECUTED_PENDING_VERIFICATION
        execution_result = executor.execute_step(step)
        
        # 4. Pass execution results to Member 2 for Evidence Artifact generation
        if step.tool_call.tool_name == "bash_tool":
            artifact = evidence_collector.collect_process_evidence(
                step_id=step.step_id,
                exit_code=execution_result.status_code,
                stdout=execution_result.stdout,
                stderr=execution_result.stderr,
                execution_time_ms=execution_result.execution_duration_ms
            )
            print(f"Generated Evidence for {step.step_id} - Checksum: {artifact.checksum}")
```
