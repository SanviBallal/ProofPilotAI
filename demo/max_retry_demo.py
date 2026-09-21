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
    print("DEMO 3: RUNAWAY LOOP PREVENTION (ABORT HALT)")
    print("Scenario: A step fails repeatedly. Member 4 terminates execution to prevent infinite looping.")
    print("==================================================\n")
    
    planner, executor, verifier = Planner(), Executor(), Verifier()
    recovery_agent, replanner = RecoveryAgent(), Replanner()
    
    goal = TaskGoal(goal_id="demo-3", description="Irrecoverable database failure.")
    plan = planner.create_plan(goal)
    plan.steps = plan.steps[:1]
    
    recovery_contexts = {}
    iterations = 0
    
    while iterations < 10:
        iterations += 1
        
        for step in plan.steps:
            if step.status == StepStatus.SYSTEM_ERROR:
                print("\n[SYSTEM] Plan marked as unrecoverable. Exiting gracefully.")
                return
                
            if step.status == StepStatus.PENDING:
                print(f"--- [MEMBER 1] EXECUTING: {step.step_id} ---")
                result = executor.execute_step(step)
                
                # Permanently force failure
                result.status_code = 1
                
                collector = EvidenceCollector(execution_id="run-3", agent_id="demo")
                artifact = collector.collect_process_evidence(step.step_id, exit_code=result.status_code, stdout="", stderr="")
                collection_result = EvidenceCollectionResult(step_id=step.step_id, artifacts=[artifact])
                
                verification = verifier.verify_step(step, collection_result, {"PROCESS_EXIT_CODE": {"expected_exit_code": 0}})
                
                if verification.is_valid:
                    step.status = StepStatus.VERIFIED_SUCCESS
                else:
                    print(f"FAIL - {step.step_id} FAILED VERIFICATION.")
                    if step.step_id not in recovery_contexts:
                        recovery_contexts[step.step_id] = RecoveryContext(step_id=step.step_id, max_retries=2)
                    
                    context = recovery_contexts[step.step_id]
                    action = recovery_agent.analyze_failure(step, verification, context)
                    
                    print(f"[MEMBER 4] RETRY {context.retry_count}/{context.max_retries} | Action -> {action.strategy.value}")
                    
                    if action.strategy.value == "ABORT_HALT":
                        print("CRITICAL: Max retries exceeded. Member 4 terminating execution safely.\n")
                        plan = replanner.generate_recovery_plan(plan, step.step_id, action, verification.analysis_summary)
                        break
                    
                    plan = replanner.generate_recovery_plan(plan, step.step_id, action, verification.analysis_summary)
                    print("Retrying...\n")
                    break

if __name__ == "__main__":
    run()
