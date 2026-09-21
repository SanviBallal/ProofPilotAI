from enum import Enum
from typing import Any, Dict, List
from pydantic import BaseModel, Field, UUID4, ConfigDict
from datetime import datetime, timezone
import uuid

class EvidenceType(str, Enum):
    FILE_CHECKSUM = "FILE_CHECKSUM"
    HTTP_RESPONSE = "HTTP_RESPONSE"
    PROCESS_EXIT_CODE = "PROCESS_EXIT_CODE"
    JSON_PAYLOAD = "JSON_PAYLOAD"
    SYSTEM_METRIC = "SYSTEM_METRIC"
    LOG_MATCH = "LOG_MATCH"

class EvidenceMetaData(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    execution_id: str
    step_id: str
    agent_id: str
    environment: Dict[str, str] = Field(default_factory=dict)

class EvidenceArtifact(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    artifact_id: UUID4 = Field(default_factory=uuid.uuid4)
    evidence_type: EvidenceType
    raw_data: Any
    metadata: EvidenceMetaData
    checksum: str

class EvidenceCollectionResult(BaseModel):
    step_id: str
    artifacts: List[EvidenceArtifact] = Field(default_factory=list)
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def has_artifacts(self) -> bool:
        return len(self.artifacts) > 0
