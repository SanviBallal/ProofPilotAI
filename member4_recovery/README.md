# Member 4: Recovery Module

## Overview
Member 4 handles failure detection, automated recovery strategies, and safe re-planning. When Member 3 (Verifier) determines that a step failed its physical evidence check, Member 4 steps in to analyze the precise failure vector, track internal state (such as strict retry limitations), and compute the safest pathway to remediation.

## Core Mechanisms

### 1. Recovery Decision Logic (`recovery_agent.py`)
- **`RecoveryContext`**: Maintains deterministic state regarding a step's health, including a strictly enforced `max_retries` property to prevent runaway looping.
- **`RecoveryAgent`**: Parses a `VerificationResult`, increments contextual retry trackers, and dynamically selects an automated `RecoveryStrategy` (e.g., `RETRY_STEP` for transient network drops using exponential backoff, or `REPLAN_SUBTREE` for structural dependencies requiring new prerequisite mitigation steps).

### 2. Dynamic Replanner (`replanner.py`)
- **`Replanner`**: Once the `RecoveryAgent` decides *what* needs to be done, the `Replanner` actively mutates the current `ExecutionPlan` safely. It injects fallback operations and reverts step statuses back to `PENDING` where applicable. 

## Stopping Infinite Loops (Runaway Prevention)
Under zero-trust autonomous constraints, agents possess an inherent risk of encountering unresolvable errors and retrying indefinitely. Member 4 intercepts this loop securely. 
If `history.has_exceeded_retries` triggers natively, the `RecoveryAgent` forcibly emits an `ABORT_HALT` strategy. The `Replanner` consumes this strategy and marks all remaining plan execution paths as `SYSTEM_ERROR`, halting the active plan reliably.

## Usage Example

```python
from shared.models import Step, ExecutionPlan
from member3_verifier import VerificationResult
from member4_recovery import RecoveryAgent, RecoveryContext, Replanner

# Assume these objects exist from earlier execution stages
current_plan: ExecutionPlan = ...
failed_step: Step = ...
verification_result: VerificationResult = ...

# 1. Initialize context specifically tracking this step's health parameters
context = RecoveryContext(step_id=failed_step.step_id, max_retries=3)

# 2. Agent analyzes the specific verification failure (e.g., checksum mismatch)
agent = RecoveryAgent()
recovery_action = agent.analyze_failure(failed_step, verification_result, context)

print(f"Decided strategy: {recovery_action.strategy}")
print(f"Reason: {recovery_action.reason}")

# 3. Replanner mutates the actual ExecutionPlan securely
replanner = Replanner()
new_plan = replanner.generate_recovery_plan(current_plan, failed_step.step_id, recovery_action)

if recovery_action.strategy == "ABORT_HALT":
    print("Execution halted safely due to unrecoverable states.")
else:
    print("Plan safely mutated. Execution can naturally resume.")
```
