import json
import os
from typing import Dict, Any
from google.genai import types
from shared.models import TaskGoal, ExecutionPlan, Step, StepStatus, ToolCall
from shared.gemini_client import get_gemini_client
from shared.constants import GEMINI_MODEL

class Planner:
    """
    Decomposes high-level goals into atomic, executable steps using the Gemini API.
    """
    
    def __init__(self):
        try:
            self.client = get_gemini_client()
        except Exception as e:
            print(f"Failed to initialize Gemini Client: {e}")
            self.client = None
    
    def create_plan(self, goal: TaskGoal) -> ExecutionPlan:
        """
        Breaks down a high-level goal into an ordered sequence of atomic Step objects using the Gemini API.
        Enforces structured JSON output validated against the Pydantic ExecutionPlan schema.
        """
        if not self.client:
            print("Gemini client uninitialized. Using fallback plan.")
            return self._fallback_create_plan(goal)
            
        prompt = f"""
        You are a highly capable systems planner for a zero-trust autonomous agent.
        Break down the following goal into atomic, executable steps.
        Goal ID: {goal.goal_id}
        Goal Description: {goal.description}
        
        Available tools:
        - bash_tool: executes shell commands. (arguments: command)
        - http_tool: executes HTTP requests. (arguments: method, url)
        - file_tool: writes/reads files. (arguments: action, path, content)
        
        Available evidence types to assign to required_evidence_types:
        - FILE_CHECKSUM
        - HTTP_RESPONSE
        - PROCESS_EXIT_CODE
        - JSON_PAYLOAD
        
        You MUST return a JSON object that strictly maps to this Python schema:
        {{
            "goal_id": "{goal.goal_id}",
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
            plan_data = json.loads(response.text)
            return ExecutionPlan(**plan_data)
        except Exception as e:
            # Graceful fallback handling in case of API failure (network, quota, etc.)
            print(f"Warning: Failed to generate plan via Gemini API: {e}. Falling back to default mock plan.")
            return self._fallback_create_plan(goal)

    def _fallback_create_plan(self, goal: TaskGoal) -> ExecutionPlan:
        steps = [
            Step(
                step_id="step_001",
                description="Initial reconnaissance or setup execution.",
                tool_call=ToolCall(tool_name="bash_tool", arguments={"command": "echo 'Setup Phase'"}),
                required_evidence_types=["PROCESS_EXIT_CODE"]
            ),
            Step(
                step_id="step_002",
                description=f"Core execution step based on goal: {goal.description}",
                tool_call=ToolCall(tool_name="bash_tool", arguments={"command": "echo 'Executing Goal Phase'"}),
                preconditions=["step_001"],
                required_evidence_types=["PROCESS_EXIT_CODE"]
            )
        ]
        return ExecutionPlan(goal_id=goal.goal_id, steps=steps)

    def resequence_plan(self, current_plan: ExecutionPlan, failed_step_id: str, recovery_strategy: Dict[str, Any]) -> ExecutionPlan:
        # Same as previous logic, now dynamically replaced by Member 4's Replanner natively.
        failed_idx = next((idx for idx, step in enumerate(current_plan.steps) if step.step_id == failed_step_id), -1)
        if failed_idx == -1:
            raise ValueError(f"Failed step {failed_step_id} not found.")
        mitigation_step = Step(
            step_id=f"{failed_step_id}_recovery",
            description=recovery_strategy.get("description", "Recovery mitigation step."),
            tool_call=ToolCall(
                tool_name=recovery_strategy.get("tool_name", "bash_tool"),
                arguments=recovery_strategy.get("arguments", {"command": "echo 'Applying mitigations'"})
            ),
            required_evidence_types=["PROCESS_EXIT_CODE", "LOG_MATCH"]
        )
        current_plan.steps[failed_idx].status = StepStatus.PENDING
        current_plan.steps.insert(failed_idx, mitigation_step)
        return current_plan
