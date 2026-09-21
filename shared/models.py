from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class StepStatus(str, Enum):
    PENDING = "PENDING"
    EXECUTED_PENDING_VERIFICATION = "EXECUTED_PENDING_VERIFICATION"
    VERIFIED_SUCCESS = "VERIFIED_SUCCESS"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"

class ToolCall(BaseModel):
    tool_name: str
    arguments: Dict[str, str]

class Step(BaseModel):
    step_id: str
    description: str
    tool_call: ToolCall
    preconditions: List[str] = Field(default_factory=list)
    required_evidence_types: List[str] = Field(default_factory=list)
    status: StepStatus = StepStatus.PENDING

class TaskGoal(BaseModel):
    goal_id: str
    description: str

class ExecutionPlan(BaseModel):
    goal_id: str
    steps: List[Step] = Field(default_factory=list)
