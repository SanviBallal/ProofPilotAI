from typing import Dict, Any, Type, Optional, List
from abc import ABC, abstractmethod
from pydantic import BaseModel
from member2_evidence.evidence_schema import EvidenceArtifact, EvidenceType

class RuleResult(BaseModel):
    is_valid: bool
    rule_name: str
    failure_reason: Optional[str] = None

class BaseVerificationRule(ABC):
    @abstractmethod
    def evaluate(self, artifact: EvidenceArtifact, criteria: Dict[str, Any]) -> RuleResult:
        """Evaluates an evidence artifact against specified criteria."""
        pass

class FileChecksumRule(BaseVerificationRule):
    def evaluate(self, artifact: EvidenceArtifact, criteria: Dict[str, Any]) -> RuleResult:
        data = artifact.raw_data
        
        if not data.get("exists", False):
            return RuleResult(is_valid=False, rule_name=self.__class__.__name__, failure_reason="File does not exist.")
        
        if data.get("size_bytes", 0) <= 0:
            return RuleResult(is_valid=False, rule_name=self.__class__.__name__, failure_reason="File is empty (size 0).")
            
        expected_hash = criteria.get("expected_hash")
        actual_hash = data.get("file_hash_sha256")
        
        if expected_hash and actual_hash:
            if expected_hash != actual_hash:
                return RuleResult(
                    is_valid=False, 
                    rule_name=self.__class__.__name__, 
                    failure_reason=f"Hash mismatch. Expected {expected_hash}, got {actual_hash}."
                )
                
        return RuleResult(is_valid=True, rule_name=self.__class__.__name__)

class HTTPStatusRule(BaseVerificationRule):
    def evaluate(self, artifact: EvidenceArtifact, criteria: Dict[str, Any]) -> RuleResult:
        data = artifact.raw_data
        expected_status = criteria.get("expected_status_code", 200)
        
        if data.get("status_code") != expected_status:
            return RuleResult(
                is_valid=False, 
                rule_name=self.__class__.__name__, 
                failure_reason=f"Status code {data.get('status_code')} != expected {expected_status}."
            )
            
        required_keys = criteria.get("required_json_keys", [])
        if required_keys:
            body = data.get("body", {})
            if not isinstance(body, dict):
                return RuleResult(
                    is_valid=False, 
                    rule_name=self.__class__.__name__, 
                    failure_reason="Response body is not a JSON dictionary."
                )
            for key in required_keys:
                if key not in body:
                    return RuleResult(
                        is_valid=False, 
                        rule_name=self.__class__.__name__, 
                        failure_reason=f"Missing required JSON key: {key}"
                    )
                    
        return RuleResult(is_valid=True, rule_name=self.__class__.__name__)

class ProcessExitCodeRule(BaseVerificationRule):
    def evaluate(self, artifact: EvidenceArtifact, criteria: Dict[str, Any]) -> RuleResult:
        data = artifact.raw_data
        expected_code = criteria.get("expected_exit_code", 0)
        
        if data.get("exit_code") != expected_code:
            return RuleResult(
                is_valid=False, 
                rule_name=self.__class__.__name__, 
                failure_reason=f"Exit code {data.get('exit_code')} != expected {expected_code}."
            )
            
        must_contain = criteria.get("stdout_must_contain", [])
        stdout_str = data.get("stdout_snippet", "")
        for sub in must_contain:
            if sub not in stdout_str:
                return RuleResult(
                    is_valid=False, 
                    rule_name=self.__class__.__name__, 
                    failure_reason=f"stdout snippet missing required string: '{sub}'"
                )
                
        must_not_contain = criteria.get("stderr_must_not_contain", [])
        stderr_str = data.get("stderr_snippet", "")
        for sub in must_not_contain:
            if sub in stderr_str:
                return RuleResult(
                    is_valid=False, 
                    rule_name=self.__class__.__name__, 
                    failure_reason=f"stderr snippet contains forbidden string: '{sub}'"
                )
                
        return RuleResult(is_valid=True, rule_name=self.__class__.__name__)

class JSONSchemaRule(BaseVerificationRule):
    def evaluate(self, artifact: EvidenceArtifact, criteria: Dict[str, Any]) -> RuleResult:
        data = artifact.raw_data
        payload = data.get("payload", {})
        
        required_keys = criteria.get("required_keys", [])
        for key in required_keys:
            if key not in payload:
                return RuleResult(
                    is_valid=False, 
                    rule_name=self.__class__.__name__, 
                    failure_reason=f"JSON payload missing required structural key: '{key}'"
                )
                
        return RuleResult(is_valid=True, rule_name=self.__class__.__name__)

class RuleRegistry:
    """Dynamically looks up and applies verification rules based on EvidenceType."""
    
    _rules: Dict[EvidenceType, Type[BaseVerificationRule]] = {
        EvidenceType.FILE_CHECKSUM: FileChecksumRule,
        EvidenceType.HTTP_RESPONSE: HTTPStatusRule,
        EvidenceType.PROCESS_EXIT_CODE: ProcessExitCodeRule,
        EvidenceType.JSON_PAYLOAD: JSONSchemaRule
    }
    
    @classmethod
    def get_rule(cls, evidence_type: EvidenceType) -> Optional[BaseVerificationRule]:
        rule_class = cls._rules.get(evidence_type)
        if rule_class:
            return rule_class()
        return None

    @classmethod
    def register_rule(cls, evidence_type: EvidenceType, rule_class: Type[BaseVerificationRule]):
        cls._rules[evidence_type] = rule_class
