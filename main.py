import os
from shared.models import TaskGoal, StepStatus
from member1_executor import Planner, Executor
from member2_evidence import EvidenceCollector
from member3_verifier import Verifier
from member4_recovery import RecoveryAgent, RecoveryContext, Replanner

def run_pipeline():
    print("==================================================")
    print("Starting A1-Evidence-Gated-Self-Healing-Agent...")
    print("==================================================")
    
    # 1. Initialize members
    planner = Planner()
    executor = Executor()
    verifier = Verifier()
    recovery_agent = RecoveryAgent()
    replanner = Replanner()
    
    # Simple explicit goal
    goal = TaskGoal(
        goal_id="goal-app-001", 
        description="Verify the system environment is healthy."
    )
    
    print(f"\n[MEMBER 1] Planning Goal: {goal.description}")
    plan = planner.create_plan(goal)
    
    print(f"[MEMBER 1] Generated Plan with {len(plan.steps)} steps.")
    
    max_total_iterations = 10
    iterations = 0
    recovery_contexts = {}
    
    while iterations < max_total_iterations:
        iterations += 1
        all_completed = True
        
        for step in plan.steps:
            if step.status == StepStatus.SYSTEM_ERROR:
                print("\n[SYSTEM] Plan is structurally unrecoverable. Halting.")
                return
                
            if step.status == StepStatus.PENDING:
                all_completed = False
                print(f"\n--- [MEMBER 1] EXECUTING: {step.step_id} ---")
                print(f"Tool: {step.tool_call.tool_name} | Args: {step.tool_call.arguments}")
                
                # Execute Zero-Trust
                execution_result = executor.execute_step(step)
                print(f"Result -> Exit Code: {execution_result.status_code}")
                
                # Evidence Zero-Trust
                print(f"[MEMBER 2] Minting tamper-evident artifacts for {step.step_id}")
                evidence_collector = EvidenceCollector(execution_id="exec-run-1", agent_id="agent-main")
                
                if step.tool_call.tool_name == "bash_tool":
                    artifact = evidence_collector.collect_process_evidence(
                        step.step_id, 
                        exit_code=execution_result.status_code or 0, 
                        stdout=execution_result.stdout, 
                        stderr=execution_result.stderr,
                        execution_time_ms=execution_result.execution_duration_ms
                    )
                else:
                    artifact = evidence_collector.collect_custom_json(step.step_id, {"status": "mock"}, "mock")
                
                from member2_evidence.evidence_schema import EvidenceCollectionResult
                collection_result = EvidenceCollectionResult(step_id=step.step_id, artifacts=[artifact])
                
                # Verifier Zero-Trust
                print(f"[MEMBER 3] Verifying raw physical proofs...")
                step_criteria = {
                    "PROCESS_EXIT_CODE": {
                        "expected_exit_code": 0
                    }
                }
                
                verification_result = verifier.verify_step(step, collection_result, step_criteria)
                
                if verification_result.is_valid:
                    print(f"PASS - Step {step.step_id} VERIFIED SUCCESSFULLY. Confidence: {verification_result.confidence_score}")
                    step.status = StepStatus.VERIFIED_SUCCESS
                else:
                    print(f"FAIL - Step {step.step_id} FAILED VERIFICATION: {verification_result.failed_rules}")
                    
                    if step.step_id not in recovery_contexts:
                        recovery_contexts[step.step_id] = RecoveryContext(step_id=step.step_id, max_retries=2) # Demo limit
                        
                    context = recovery_contexts[step.step_id]
                    
                    # Recovery Healer
                    print(f"[MEMBER 4] Intercepting failure and determining mitigation strategy...")
                    action = recovery_agent.analyze_failure(step, verification_result, context)
                    print(f"[MEMBER 4] Action Strategy: {action.strategy.value}")
                    
                    if action.strategy.value == "ABORT_HALT":
                        print("CRITICAL: Runaway prevention loop triggered. Execution HALTED safely.")
                        return
                    
                    # Replan
                    plan = replanner.generate_recovery_plan(plan, step.step_id, action, verification_result.analysis_summary)
                    print(f"[MEMBER 4] Plan successfully mutated. Re-entering execution loop.")
                    
                    # Break loop to start fresh over mutated plan steps
                    break
        
        if all_completed:
            print("\n==================================================")
            print("ALL STEPS VERIFIED AND COMPLETED SUCCESSFULLY.")
            print("==================================================")
            break
            
    if iterations >= max_total_iterations:
        print("Pipeline timed out.")

if __name__ == "__main__":
    run_pipeline()
