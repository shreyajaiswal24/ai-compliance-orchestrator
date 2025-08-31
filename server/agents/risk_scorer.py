from .base_agent import BaseAgent
from typing import Dict, Any, List
import asyncio

class RiskScorerAgent(BaseAgent):
    def __init__(self):
        super().__init__("RiskScorer", timeout=10)
        
    async def execute(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        await asyncio.sleep(1.0)
        
        # Get outputs from previous agents
        policy_data = context.get("policy_retriever", {})
        evidence_data = context.get("evidence_collector", {})
        vision_data = context.get("vision_ocr", {})
        code_data = context.get("code_scanner", {})
        
        # Mock risk scoring logic
        risk_factors = []
        base_score = 0.5
        
        # Check policy compliance
        if policy_data.get("policies"):
            policies_found = len(policy_data["policies"])
            if policies_found >= 2:
                risk_factors.append("Multiple relevant policies identified")
                base_score -= 0.1
            else:
                risk_factors.append("Limited policy coverage")
                base_score += 0.15
                
        # Check evidence quality
        if evidence_data.get("evidence"):
            evidence_confidence = sum(e.get("confidence", 0) for e in evidence_data["evidence"]) / len(evidence_data["evidence"])
            if evidence_confidence > 0.8:
                risk_factors.append("High-confidence evidence found")
                base_score -= 0.15
            else:
                risk_factors.append("Low-confidence evidence")
                base_score += 0.2
                
        # Check code findings
        if code_data.get("findings"):
            compliance_items = code_data.get("compliance_items", 0)
            if compliance_items >= 2:
                risk_factors.append("Multiple compliance controls detected in code")
                base_score -= 0.1
            else:
                risk_factors.append("Limited compliance controls in code")
                base_score += 0.15
        
        # Normalize score
        final_score = max(0.0, min(1.0, base_score))
        
        return {
            "agent": self.name,
            "status": "success",
            "risk_score": final_score,
            "confidence": 0.75,
            "risk_factors": risk_factors,
            "recommendation": "needs_review" if final_score > 0.6 else "acceptable",
            "execution_time": self.execution_time
        }