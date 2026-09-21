# Member 2: Evidence Module

## Zero-Trust Evidence Philosophy
The core principle of this agent system is **ZERO-TRUST EXECUTION**. 
In our architecture, no task step is considered complete simply because an agent or process claims it finished. Every action must produce machine-checkable evidence that can be independently verified by other agents in the system.

This module is responsible for gathering raw, physical proof from system operations, forming deterministic and tamper-evident `EvidenceArtifact` records. Every artifact includes a strictly calculated SHA-256 checksum covering both the metadata and the raw data payload to ensure integrity and prevent tampering.

## Usage & Integration

### Core Components
- **`EvidenceCollector`**: The main class responsible for capturing evidence from files, HTTP responses, sub-processes, and custom JSON payloads.
- **`EvidenceArtifact`**: A strict Pydantic model representing the collected evidence, including a tamper-evident checksum.

### Code Example: Generating Evidence (Member 1 -> Member 2)

Member 1 (Executor) performs an action and immediately passes the raw execution results into the `EvidenceCollector`. This generates a valid `EvidenceArtifact` object which will later be evaluated by Member 3 (Verifier).

```python
import requests
from member2_evidence import EvidenceCollector

# 1. Initialize the Evidence Collector with context
collector = EvidenceCollector(
    execution_id="exec-4029384",
    agent_id="member1-executor",
    environment={"os": "linux", "env": "production"}
)

# 2. Example: Collecting evidence from an HTTP Request
step_id = "step-001-fetch-data"
try:
    response = requests.get("https://api.example.com/data")
    # Pass the raw response to generate immutable evidence
    http_evidence = collector.collect_http_evidence(step_id, response)
except Exception as e:
    # Construct a mock dictionary for failed requests
    http_evidence = collector.collect_http_evidence(step_id, {
        "status_code": 500,
        "error": str(e)
    })

print(http_evidence.model_dump_json(indent=2))

# 3. Example: Collecting evidence from a File Operation
step_id_2 = "step-002-write-file"
file_path = "/tmp/output.json"
# ... Member 1 writes to file ...
file_evidence = collector.collect_file_evidence(step_id_2, file_path)

print(f"Generated artifact with checksum: {file_evidence.checksum}")
```
