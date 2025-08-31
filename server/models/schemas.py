from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime
import uuid

class Citation(BaseModel):
    doc_id: str
    chunk_id: str
    snippet: str

class HumanInteraction(BaseModel):
    timestamp: datetime
    type: Literal["clarification", "approval", "upload_request"]
    prompt: str
    response: str
    status: Literal["approved", "denied", "provided", "timeout"]

class ComplianceResult(BaseModel):
    decision: Literal["compliant", "non_compliant", "insufficient_evidence"]
    confidence: float = Field(ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=1.0)
    rationale: str
    citations: List[Citation]
    open_questions: List[str]
    human_interactions: List[HumanInteraction]

class HITLRequest(BaseModel):
    session_id: str
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: Literal["clarification", "approval", "upload_request"]
    prompt: str
    required_artifact: Optional[Literal["image", "text"]] = None

class HITLResponse(BaseModel):
    session_id: str
    request_id: str
    response_type: Literal["text", "approval", "upload"]
    payload: Dict[str, Any]

class ProgressUpdate(BaseModel):
    stage: str
    status: str
    meta: Optional[Dict[str, Any]] = None

class SessionState(BaseModel):
    session_id: str
    created_at: datetime
    updated_at: datetime
    query: str
    attachments: List[str] = []
    agent_outputs: Dict[str, Any] = {}
    human_interactions: List[HumanInteraction] = []
    final_result: Optional[ComplianceResult] = None