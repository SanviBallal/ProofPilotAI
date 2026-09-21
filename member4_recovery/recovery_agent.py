from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from shared.models import Step, ToolCall
from member3_verifier import VerificationResult

class RecoveryStrategy(str, Enum):
    RETRY_STEP = "RETRY_STEP"
    FALLBACK_TOOL = "FALLBACK_TOOL"
    REPLAN_SUBTREE = "REPLAN_SUBTREE"
    ABORT_HALT = "ABORT_HALT"

class RecoveryContext(BaseModel):
    step_id: str
    retry_count: int = 0
    max_retries: int = 3
    failure_history: List[str] = Field(default_factory=list)
    
    def record_failure(self, reason: str):
        self.retry_count += 1
        self.failure_history.append(reason)
        
    @property
    def has_exceeded_retries(self) -> bool:
        """Enforces a strict upper bound to prevent infinite looping."""
        return self.retry_count >= self.max_retries

class RecoveryAction(BaseModel):
    strategy: RecoveryStrategy
    delay_ms: float = 0.0
    injected_steps: List[Step] = Field(default_factory=list)
    reason: str

class RecoveryAgent:
    """
    Analyzes failed verification reports, maintains strict state bounds (e.g. max retries),
    and determines the safest automated recovery pattern for the system.
    """
    
    def analyze_failure(self, step: Step, verification_result: VerificationResult, history: RecoveryContext) -> RecoveryAction:
        """
        Evaluates a step failure and returns the optimal recovery action.
        """
        history.record_failure(verification_result.analysis_summary)
        
        # Zero-trust safety threshold
        if history.has_exceeded_retries:
            return RecoveryAction(
                strategy=RecoveryStrategy.ABORT_HALT,
                reason=f"Max retries ({history.max_retries}) exceeded for step {step.step_id}. Halting execution to prevent runaway state."
            )
            
        # Analyze failed rules to categorize the failure
        failed_rules = verification_result.failed_rules
        
        # Transient error heuristic (e.g., Network timeouts, 503s)
        if any("HTTPStatusRule" in r for r in failed_rules) or any("Timeout" in r for r in failed_rules):
            delay = 1000.0 * (2 ** (history.retry_count - 1)) # Exponential backoff
            return RecoveryAction(
                strategy=RecoveryStrategy.RETRY_STEP,
                delay_ms=delay,
                reason=f"Transient failure detected. Retrying with {delay}ms exponential backoff."
            )
            
        # Missing dependency / State mismatch heuristic (e.g. Expected file not generated)
        if any("FileChecksumRule" in r for r in failed_rules) or any("ProcessExitCodeRule" in r for r in failed_rules):
            # Formulate an automated mitigation step
            mitigation_step = Step(
                step_id=f"{step.step_id}_mitigation_{history.retry_count}",
                description=f"Automatic mitigation injected for failing step: {step.step_id}",
                tool_call=ToolCall(
                    tool_name="bash_tool",
                    arguments={"command": "echo 'Executing generic automated state remediation'"}
                ),
                required_evidence_types=["PROCESS_EXIT_CODE"]
            )
            return RecoveryAction(
                strategy=RecoveryStrategy.REPLAN_SUBTREE,
                injected_steps=[mitigation_step],
                reason="State corruption or failed execution detected. Injecting mitigation prerequisite step."
            )
            
        # Default fallback mechanism
        return RecoveryAction(
            strategy=RecoveryStrategy.RETRY_STEP,
            delay_ms=1000.0,
            reason="Generic failure. Retrying with basic 1000ms delay."
        )
