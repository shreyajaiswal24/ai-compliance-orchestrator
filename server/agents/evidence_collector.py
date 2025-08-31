from .base_agent import BaseAgent
from typing import Dict, Any, List
import asyncio

class EvidenceCollectorAgent(BaseAgent):
    def __init__(self):
        super().__init__("EvidenceCollector", timeout=25)
        
    async def execute(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        # Mock implementation
        await asyncio.sleep(2.5)
        
        # Dummy evidence collection
        mock_evidence = [
            {
                "doc_id": "SPEC-001",
                "chunk_id": "LOGIN-FLOW-001",
                "snippet": "User enters credentials -> SMS OTP sent to registered phone -> User enters OTP -> Access granted",
                "source": "Product Specification",
                "confidence": 0.92
            },
            {
                "doc_id": "API-DOC-001", 
                "chunk_id": "AUTH-ENDPOINT-001",
                "snippet": "POST /auth/login - Requires username, password, and otp_token parameters",
                "source": "API Documentation",
                "confidence": 0.88
            }
        ]
        
        return {
            "agent": self.name,
            "status": "success", 
            "evidence": mock_evidence,
            "total_found": len(mock_evidence),
            "query": query,
            "execution_time": self.execution_time
        }