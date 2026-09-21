import time
import subprocess
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel
from shared.models import Step, StepStatus

class ExecutionResult(BaseModel):
    step_id: str
    status: StepStatus
    status_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    raw_payload: Optional[Dict[str, Any]] = None
    execution_duration_ms: float = 0.0
    error_message: Optional[str] = None

class Executor:
    """
    Executes a single Step via tool wrappers.
    Under ZERO-TRUST Principles, this execution engine MUST NOT verify its own completion.
    """
    
    def execute_step(self, step: Step) -> ExecutionResult:
        """Executes tool calls defined in a step, emitting raw results strictly awaiting verification."""
        start_time = time.time()
        result = ExecutionResult(
            step_id=step.step_id,
            status=StepStatus.SYSTEM_ERROR # Default to system error in case of unhandled crash
        )
        
        try:
            tool_name = step.tool_call.tool_name
            args = step.tool_call.arguments
            
            # Map tools
            if tool_name == "bash_tool":
                res = self._bash_tool(**args)
            elif tool_name == "http_tool":
                res = self._http_tool(**args)
            elif tool_name == "file_tool":
                res = self._file_tool(**args)
            elif tool_name == "json_transform_tool":
                res = self._json_transform_tool(**args)
            else:
                raise ValueError(f"Unknown tool designated: {tool_name}")
                
            # Bind wrapper execution results to the output
            for key, value in res.items():
                if hasattr(result, key):
                    setattr(result, key, value)
                
            # CRITICAL ZERO-TRUST RULE: 
            # Executor MUST NOT mark a step as VERIFIED_SUCCESS. 
            result.status = StepStatus.EXECUTED_PENDING_VERIFICATION
            step.status = StepStatus.EXECUTED_PENDING_VERIFICATION
            
        except Exception as e:
            result.status = StepStatus.SYSTEM_ERROR
            result.error_message = f"Runtime exception during tool execution: {str(e)}"
            step.status = StepStatus.SYSTEM_ERROR
            
        finally:
            end_time = time.time()
            result.execution_duration_ms = (end_time - start_time) * 1000.0
            
        return result

    def _bash_tool(self, command: str) -> Dict[str, Any]:
        """Lightweight wrapper for shell command execution."""
        process = subprocess.run(
            command,
            shell=True,
            text=True,
            capture_output=True
        )
        return {
            "status_code": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr
        }

    def _http_tool(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Lightweight wrapper for HTTP requests."""
        response = requests.request(method=method, url=url, **kwargs)
        return {
            "status_code": response.status_code,
            "stdout": response.text,
            "raw_payload": dict(response.headers)
        }

    def _file_tool(self, action: str, path: str, content: str = "") -> Dict[str, Any]:
        """Lightweight wrapper for file creation/manipulation."""
        target_path = Path(path)
        if action == "write":
            target_path.write_text(content)
            return {"status_code": 0, "stdout": f"Successfully wrote to {path}"}
        elif action == "read":
            if target_path.exists():
                return {"status_code": 0, "stdout": target_path.read_text()}
            return {"status_code": 1, "stderr": f"File not found: {path}"}
        else:
            raise ValueError(f"Unknown file action: {action}")

    def _json_transform_tool(self, payload: Dict[str, Any], operation: str) -> Dict[str, Any]:
        """Lightweight wrapper for JSON manipulations."""
        transformed = payload.copy()
        if operation == "clear_keys":
            transformed = {}
        return {
            "status_code": 0,
            "raw_payload": transformed
        }
