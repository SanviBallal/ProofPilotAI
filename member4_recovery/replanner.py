import json
from typing import Optional, List
from pydantic import BaseModel
from google.genai import types

from shared.models import ExecutionPlan, Step, StepStatus, ToolCall
from .recovery_agent import RecoveryAction, RecoveryStrategy
from shared.gemini_client import get_gemini_client
from shared.constants import GEMINI_MODEL

class StepList(BaseModel):
    steps: list[Step]

class Replanner:
    """
    Mutates execution plans in-flight to safely facilitate automated recovery.
    Integrates Gemini AI to intelligently inject recovery/mitigation steps when needed.
    """
    
    def __init__(self):
        try:
            self.client = get_gemini_client()
        except Exception:
            self.client = None
            
    def generate_recovery_plan(self, current_plan: ExecutionPlan, failed_step_id: str, action: RecoveryAction, verification_summary: str = "") -> ExecutionPlan:
        """
        Modifies the execution graph safely based on an emitted RecoveryAction and Member 3 feedback.
        """
        failed_idx = next((idx for idx, step in enumerate(current_plan.steps) if step.step_id == failed_step_id), -1)
        
        if failed_idx == -1:
            raise ValueError(f"Failed step '{failed_step_id}' not found in the current execution plan.")
            
        if action.strategy == RecoveryStrategy.ABORT_HALT:
            for idx in range(failed_idx, len(current_plan.steps)):
                current_plan.steps[idx].status = StepStatus.SYSTEM_ERROR
            return current_plan
            
        elif action.strategy == RecoveryStrategy.RETRY_STEP:
            current_plan.steps[failed_idx].status = StepStatus.PENDING
            
        elif action.strategy == RecoveryStrategy.FALLBACK_TOOL:
            if action.injected_steps:
                fallback_tool = action.injected_steps[0].tool_call
                current_plan.steps[failed_idx].tool_call = fallback_tool
            current_plan.steps[failed_idx].status = StepStatus.PENDING
            
        elif action.strategy == RecoveryStrategy.REPLAN_SUBTREE:
            # Let Gemini formulate an intelligent recovery step sequence based on the verification context
            if self.client:
                prompt = f"""
                You are a Zero-Trust Recovery Replanner. The execution plan failed at step: {failed_step_id}.
                Member 3 (Verifier) Failure Summary: {verification_summary}
                
                Current step that failed:
                {current_plan.steps[failed_idx].model_dump_json()}
                
                Generate a list of exactly ONE mitigation Step to execute immediately prior to retrying the failed step.
                You MUST return a JSON object in this format:
                {{
                    "steps": [
                        {{
                            "step_id": "string",
                            "description": "string",
                            "tool_call": {{"tool_name": "string", "arguments": {{"key": "value"}}}},
                            "preconditions": ["string"],
                            "required_evidence_types": ["string"]
                        }}
                    ]
                }}
                """
                try:
                    response = self.client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json"
                        )
                    )
                    step_data = json.loads(response.text)
                    action.injected_steps = [Step(**s) for s in step_data.get("steps", [])]
                except Exception as e:
                    print(f"Warning: Gemini API replanning failed: {e}. Falling back to default heuristics.")
            
            # Reset failed step so it can re-trigger after mitigations run
            current_plan.steps[failed_idx].status = StepStatus.PENDING
            
            # Inject new mitigation steps
            for step in reversed(action.injected_steps):
                current_plan.steps.insert(failed_idx, step)
                
        return current_plan
