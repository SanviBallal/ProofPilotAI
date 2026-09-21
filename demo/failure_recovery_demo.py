import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models import TaskGoal, StepStatus
from member1_executor import Planner, Executor
from member2_evidence import EvidenceCollector
from member3_verifier import Verifier
from member4_recovery import RecoveryAgent, RecoveryContext, Replanner
from member2_evidence.evidence_schema import EvidenceCollectionResult

def run():
    print("==================================================")
    print("DEMO 2: FAILURE & AUTOMATED RECOVERY")
    print("Scenario: A step fails verification. Member 4 intercepts, mutates the plan, and self-heals.")
    print("==================================================\n")
    
    planner, executor, verifier = Planner(), Executor(), Verifier()
    recovery_agent, replanner = RecoveryAgent(), Replanner()
    
    goal = TaskGoal(goal_id="demo-2", description="Unstable API interaction.")
    plan = planner.create_plan(goal)
    plan.steps = plan.steps[:1]  # Simplify to 1 step for the demo
    
    recovery_contexts = {}
    force_fail_flag = True
    iterations = 0
    
    while iterations < 5:
        iterations += 1
        all_completed = True
        
        for step in plan.steps:
            if step.status == StepStatus.PENDING:
                all_completed = False
                print(f"--- [MEMBER 1] EXECUTING: {step.step_id} ---")
                result = executor.execute_step(step)
                
                # Mock failure on first attempt, success on second
                if force_fail_flag:
                    result.status_code = 1
                    force_fail_flag = False
                    print(f"    (Mocking execution failure...)")
                else:
                    result.status_code = 0
                    print(f"    (Mocking execution success...)")
                
                collector = EvidenceCollector(execution_id="run-2", agent_id="demo")
                artifact = collector.collect_process_evidence(step.step_id, exit_code=result.status_code, stdout="", stderr="")
                collection_result = EvidenceCollectionResult(step_id=step.step_id, artifacts=[artifact])
                
                verification = verifier.verify_step(step, collection_result, {"PROCESS_EXIT_CODE": {"expected_exit_code": 0}})
                
                if verification.is_valid:
                    print(f"PASS - {step.step_id} VERIFIED SUCCESSFULLY.\n")
                    step.status = StepStatus.VERIFIED_SUCCESS
                else:
                    print(f"FAIL - {step.step_id} FAILED VERIFICATION: {verification.failed_rules}")
                    if step.step_id not in recovery_contexts:
                        recovery_contexts[step.step_id] = RecoveryContext(step_id=step.step_id, max_retries=3)
                    
                    action = recovery_agent.analyze_failure(step, verification, recovery_contexts[step.step_id])
                    print(f"[MEMBER 4] HEALER ACTIVATED: Strategy selected -> {action.strategy.value}")
                    
                    plan = replanner.generate_recovery_plan(plan, step.step_id, action, verification.analysis_summary)
                    print(f"[MEMBER 4] Plan mutated. Retrying...\n")
                    break
        
        if all_completed:
            print("[SUCCESS] Demo 2 Finished successfully after automated healing.")
            break

if __name__ == "__main__":
    run()
