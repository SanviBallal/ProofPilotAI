# Member 3: Verifier Module

## Overview
Member 3 is the **Core Trust Arbiter** of the zero-trust AI Agent system. It never trusts plain text assertions or claims made by agents (Member 1). Instead, it demands machine-checkable `EvidenceArtifact` objects collected by Member 2 and subjects them to rigorous evaluation using strict, deterministic verification rules.

### Zero-Trust Principles
- **No False Claims**: If evidence is missing, corrupted, or fails structural rule checks, the step's verification result strictly resolves to `is_valid: False` with a `confidence_score: 0.0`. 
- **Integrity First**: Before running logical rule evaluations, the Verifier independently recalculates the SHA-256 checksum of the raw physical proof and metadata to detect any potential tampering in-flight.
- **Fail-Safe Processing**: If an `EvidenceArtifact` does not have a registered rule mapping, the step automatically fails securely.

## Key Components

### 1. Rule Engine (`rules.py`)
Houses concrete verification logic enforcing strict policies over execution proofs.
- **`FileChecksumRule`**: Validates file existence, non-zero size limits, and exact hash matches.
- **`ProcessExitCodeRule`**: Evaluates stdout/stderr content against required substrings and mandates a proper `0` exit code.
- **`HTTPStatusRule`**: Verifies HTTP status codes and strict schema matches on the response payload.
- **`JSONSchemaRule`**: Validates structural key-value consistency for JSON.
- **`RuleRegistry`**: Dynamically looks up and routes evidence to the correct validation rule based on `EvidenceType`.

### 2. Core Verifier (`verifier.py`)
Provides the `Verifier` class and acts as the entrypoint for evidence arbitration. It produces a `VerificationResult` containing the final `is_valid` flag, confidence score, failed policies, and a human-readable analysis summary.

## Feedback Loop with Member 4 (Healer)
The `VerificationResult` output by this module is crucial for self-healing. If `is_valid` is `False`, the output is passed directly to **Member 4**. Member 4 analyzes the `failed_rules` array and the `analysis_summary` to deduce a recovery plan, which it then feeds back to Member 1 for plan mutation.

## Usage Example

```python
from member3_verifier import Verifier
from shared.models import Step
from member2_evidence import EvidenceCollectionResult

# Initialize the Arbiter
verifier = Verifier()

# Define strict criteria required for a given step's artifacts
step_criteria = {
    "PROCESS_EXIT_CODE": {
        "expected_exit_code": 0,
        "stdout_must_contain": ["Successfully completed"]
    }
}

# Assume 'step' and 'collection_result' are provided by Member 1 and 2
verification_result = verifier.verify_step(step, collection_result, step_criteria)

if verification_result.is_valid:
    print(f"Step {step.step_id} verified successfully!")
else:
    print(f"Step {step.step_id} failed verification.")
    print(f"Confidence: {verification_result.confidence_score}")
    print(f"Violations: {verification_result.failed_rules}")
    print(f"Summary: {verification_result.analysis_summary}")
    
    # -> Pass verification_result to Member 4 for healing
```
