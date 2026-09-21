import hashlib
import json
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from pathlib import Path

from .evidence_schema import (
    EvidenceType,
    EvidenceMetaData,
    EvidenceArtifact
)

class EvidenceCollector:
    """
    Collects robust, physical proof from system operations to provide 
    zero-trust execution evidence.
    """
    
    def __init__(self, execution_id: str, agent_id: str, environment: Optional[Dict[str, str]] = None):
        self.execution_id = execution_id
        self.agent_id = agent_id
        self.environment = environment or {}

    def _create_metadata(self, step_id: str) -> EvidenceMetaData:
        return EvidenceMetaData(
            timestamp=datetime.now(timezone.utc).isoformat(),
            execution_id=self.execution_id,
            step_id=step_id,
            agent_id=self.agent_id,
            environment=self.environment
        )

    def _compute_artifact_checksum(self, raw_data: Any, metadata: EvidenceMetaData) -> str:
        """
        Computes a SHA-256 checksum of the raw data and metadata to enforce tamper-evident records.
        """
        # Serialize raw_data to string form for consistent hashing
        try:
            raw_data_str = json.dumps(raw_data, sort_keys=True, default=str)
        except (TypeError, ValueError):
            raw_data_str = str(raw_data)
        
        metadata_str = metadata.model_dump_json()
        
        combined = f"{raw_data_str}|{metadata_str}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()

    def _create_artifact(self, step_id: str, evidence_type: EvidenceType, raw_data: Any) -> EvidenceArtifact:
        metadata = self._create_metadata(step_id)
        checksum = self._compute_artifact_checksum(raw_data, metadata)
        return EvidenceArtifact(
            evidence_type=evidence_type,
            raw_data=raw_data,
            metadata=metadata,
            checksum=checksum
        )

    def collect_file_evidence(self, step_id: str, file_path: str) -> EvidenceArtifact:
        """
        Verifies file existence, calculates SHA-256 hash, retrieves file size (bytes), 
        and last modified timestamp.
        """
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raw_data = {
                "file_path": file_path,
                "exists": False,
                "error": "File does not exist or is not a file."
            }
        else:
            try:
                # Calculate SHA-256 hash in blocks to handle large files
                sha256_hash = hashlib.sha256()
                with open(path, "rb") as f:
                    for byte_block in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(byte_block)
                
                stat = path.stat()
                raw_data = {
                    "file_path": file_path,
                    "exists": True,
                    "file_hash_sha256": sha256_hash.hexdigest(),
                    "size_bytes": stat.st_size,
                    "last_modified_timestamp": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                }
            except Exception as e:
                raw_data = {
                    "file_path": file_path,
                    "exists": True,
                    "error": f"Failed to read file attributes: {str(e)}"
                }
        
        return self._create_artifact(step_id, EvidenceType.FILE_CHECKSUM, raw_data)

    def collect_http_evidence(self, step_id: str, response_obj: Any) -> EvidenceArtifact:
        """
        Extracts status code, headers (filtered/redacted for secrets), response body hash or payload, and latency.
        Accepts a dictionary or a requests.Response-like object.
        """
        raw_data: Dict[str, Any] = {}
        
        def redact_headers(headers: Dict[str, str]) -> Dict[str, str]:
            sensitive_keys = {'authorization', 'cookie', 'set-cookie', 'x-api-key', 'token'}
            redacted = {}
            for k, v in headers.items():
                if k.lower() in sensitive_keys:
                    redacted[k] = "***REDACTED***"
                else:
                    redacted[k] = str(v)
            return redacted

        if isinstance(response_obj, dict):
            raw_data["status_code"] = response_obj.get("status_code")
            raw_data["headers"] = redact_headers(response_obj.get("headers", {}))
            raw_data["latency_ms"] = response_obj.get("latency_ms")
            
            body = response_obj.get("body", "")
            if isinstance(body, str):
                raw_data["body_hash_sha256"] = hashlib.sha256(body.encode('utf-8')).hexdigest()
                raw_data["body_snippet"] = body[:200]
            else:
                raw_data["body"] = body
        else:
            try:
                raw_data["status_code"] = getattr(response_obj, "status_code", None)
                headers = dict(getattr(response_obj, "headers", {}))
                raw_data["headers"] = redact_headers(headers)
                
                elapsed = getattr(response_obj, "elapsed", None)
                if elapsed is not None:
                    raw_data["latency_ms"] = elapsed.total_seconds() * 1000

                text = getattr(response_obj, "text", "")
                if text:
                    raw_data["body_hash_sha256"] = hashlib.sha256(text.encode('utf-8')).hexdigest()
                    raw_data["body_snippet"] = text[:200]
            except Exception as e:
                raw_data["error"] = f"Failed to parse HTTP response object: {str(e)}"
                
        return self._create_artifact(step_id, EvidenceType.HTTP_RESPONSE, raw_data)

    def collect_process_evidence(self, step_id: str, exit_code: int, stdout: Optional[str], stderr: Optional[str], execution_time_ms: Optional[float] = None) -> EvidenceArtifact:
        """
        Captures process exit codes, stdout snippet, stderr snippet, and execution time.
        """
        stdout_str = stdout if stdout is not None else ""
        stderr_str = stderr if stderr is not None else ""
        
        raw_data = {
            "exit_code": exit_code,
            "stdout_snippet": stdout_str[:500],
            "stderr_snippet": stderr_str[:500],
        }
        if execution_time_ms is not None:
            raw_data["execution_time_ms"] = execution_time_ms
            
        return self._create_artifact(step_id, EvidenceType.PROCESS_EXIT_CODE, raw_data)

    def collect_custom_json(self, step_id: str, payload: dict, schema_type: str) -> EvidenceArtifact:
        """
        Captures structured JSON outputs for custom verification rules.
        """
        raw_data = {
            "schema_type": schema_type,
            "payload": payload
        }
        return self._create_artifact(step_id, EvidenceType.JSON_PAYLOAD, raw_data)
