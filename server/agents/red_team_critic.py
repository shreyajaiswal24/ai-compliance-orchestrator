from .base_agent import BaseAgent
from typing import Dict, Any, List
import asyncio

class RedTeamCriticAgent(BaseAgent):
    def __init__(self):
        super().__init__("RedTeamCritic", timeout=15)
        
    async def execute(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        await asyncio.sleep(2.2)
        
        # Get risk scorer output
        risk_data = context.get("risk_scorer", {})
        risk_score = risk_data.get("risk_score", 0.5)
        
        # Mock critical analysis
        gaps_found = []
        follow_up_questions = []
        challenges = []
        
        # Critical analysis based on risk score
        if risk_score > 0.6:
            gaps_found.extend([
                "Insufficient evidence for backup authentication methods",
                "No verification of policy enforcement in production",
                "Missing details about user enrollment process"
            ])
            
            follow_up_questions.extend([
                "What happens if SMS is unavailable? Is there a backup MFA method?",
                "How are users enrolled in MFA? Is it mandatory?", 
                "Are there any exceptions or bypass mechanisms?"
            ])
            
            challenges.extend([
                "Evidence suggests MFA is implemented but lacks depth verification",
                "Policy compliance appears partial based on available information",
                "Need human verification of actual system behavior"
            ])
        else:
            gaps_found.append("Minor: Could benefit from explicit policy version references")
            follow_up_questions.append("Which specific version of the MFA policy applies?")
            challenges.append("Overall implementation appears compliant but needs final verification")
        
        # Determine if HITL is needed
        needs_hitl = risk_score > 0.5 or len(gaps_found) > 2
        
        return {
            "agent": self.name,
            "status": "success",
            "gaps_identified": gaps_found,
            "follow_up_questions": follow_up_questions, 
            "challenges": challenges,
            "needs_hitl": needs_hitl,
            "criticality": "high" if risk_score > 0.7 else "medium" if risk_score > 0.4 else "low",
            "execution_time": self.execution_time
        }