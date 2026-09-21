import hashlib
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from shared.models import Step
from member2_evidence.evidence_schema import EvidenceCollectionResult, EvidenceArtifact
from .rules import RuleRegistry

class VerificationResult(BaseModel):
    step_id: str
    is_valid: bool
    confidence_score: float
    failed_rules: List[str] = Field(default_factory=list)
    analysis_summary: str

class Verifier:
    """
    Core trust arbiter of the system. Evaluates EvidenceArtifacts against strict 
    deterministic verification rules, guaranteeing zero-trust principles.
    """
    
    def _verify_artifact_integrity(self, artifact: EvidenceArtifact) -> bool:
        """
        Recalculates the checksum to ensure the artifact was not tampered with.
        """
        try:
            raw_data_str = json.dumps(artifact.raw_data, sort_keys=True, default=str)
        except (TypeError, ValueError):
            raw_data_str = str(artifact.raw_data)
            
        metadata_str = artifact.metadata.model_dump_json()
        
        combined = f"{raw_data_str}|{metadata_str}"
        expected_checksum = hashlib.sha256(combined.encode('utf-8')).hexdigest()
        
        return expected_checksum == artifact.checksum

    def verify_step(self, step: Step, collection_result: EvidenceCollectionResult, step_criteria: Optional[Dict[str, Any]] = None) -> VerificationResult:
        """
        Verifies all artifacts for a given step against specified strict rules.
        """
        if not collection_result.has_artifacts:
            return VerificationResult(
                step_id=step.step_id,
                is_valid=False,
                confidence_score=0.0,
                failed_rules=["MissingEvidence"],
                analysis_summary="No evidence artifacts provided for verification."
            )
            
        step_criteria = step_criteria or {}
        failed_rules: List[str] = []
        is_valid = True
        
        for artifact in collection_result.artifacts:
            # 1. Check artifact checksum integrity (detect tampering)
            if not self._verify_artifact_integrity(artifact):
                is_valid = False
                failed_rules.append(f"IntegrityTampering:{artifact.evidence_type.value}")
                continue
                
            # 2. Match artifacts against step criteria using RuleRegistry
            rule = RuleRegistry.get_rule(artifact.evidence_type)
            if not rule:
                # Under zero-trust, missing a rule definition for a type results in failure
                is_valid = False
                failed_rules.append(f"MissingRuleForType:{artifact.evidence_type.value}")
                continue
                
            # Lookup specific criteria dict for the evidence type, default to empty
            criteria_for_type = step_criteria.get(artifact.evidence_type.value, {})
            rule_result = rule.evaluate(artifact, criteria_for_type)
            
            if not rule_result.is_valid:
                is_valid = False
                reason = rule_result.failure_reason or "Unknown logical failure."
                failed_rules.append(f"{rule_result.rule_name}:{reason}")
                
        # 3. Return VerificationResult with strict zero-trust parameters
        confidence_score = 1.0 if is_valid else 0.0
        
        if is_valid:
            summary = "All evidence artifacts successfully verified against deterministic rules. Cryptographic integrity confirmed."
        else:
            summary = f"Verification failed. Integrity or rule violations detected: {', '.join(failed_rules)}"
            
        return VerificationResult(
            step_id=step.step_id,
            is_valid=is_valid,
            confidence_score=confidence_score,
            failed_rules=failed_rules,
            analysis_summary=summary
        )
