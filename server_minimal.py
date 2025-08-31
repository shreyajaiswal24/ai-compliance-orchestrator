#!/usr/bin/env python3
"""
Minimal FastAPI server without complex dependencies
"""

from fastapi import FastAPI
import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any

# Use the same mock agents from simple_demo
class MockAgent:
    def __init__(self, name: str):
        self.name = name
        self.execution_time = 1.0
    
    async def run_with_timeout(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        await asyncio.sleep(0.5)
        
        if self.name == "PolicyRetriever":
            return {"agent": self.name, "status": "success", "policies": [
                {"doc_id": "POLICY-001", "snippet": "MFA required for all logins"}]}
        elif self.name == "EvidenceCollector":
            return {"agent": self.name, "status": "success", "evidence": [
                {"doc_id": "SPEC-001", "snippet": "SMS OTP implementation active"}]}
        elif self.name == "VisionOCR":
            return {"agent": self.name, "status": "success", "ocr_results": [
                {"extracted_text": "MFA Settings: SMS enabled"}]}
        elif self.name == "CodeScanner":
            return {"agent": self.name, "status": "success", "findings": [
                {"description": "MFA verification found in code"}]}
        elif self.name == "RiskScorer":
            return {"agent": self.name, "status": "success", "risk_score": 0.2, "confidence": 0.85}
        else:  # RedTeamCritic
            return {"agent": self.name, "status": "success", "needs_hitl": False,
                   "gaps_identified": ["Minor: Version reference needed"]}

app = FastAPI(title="AI Compliance & Risk Orchestrator - Minimal")

# In-memory storage
sessions = {}

async def run_workflow(session_id: str, query: str):
    """Run the full multi-agent workflow"""
    
    # Create agents
    agents = [
        MockAgent("PolicyRetriever"),
        MockAgent("EvidenceCollector"), 
        MockAgent("VisionOCR"),
        MockAgent("CodeScanner")
    ]
    
    # Step 1: Parallel execution of collection agents
    print(f"🔄 Session {session_id}: Running parallel collection...")
    collection_tasks = [agent.run_with_timeout(query, {}) for agent in agents]
    results = await asyncio.gather(*collection_tasks)
    
    # Step 2: Sequential risk scoring
    context = {result["agent"].lower(): result for result in results}
    
    risk_agent = MockAgent("RiskScorer")
    risk_result = await risk_agent.run_with_timeout(query, context)
    context["risk_scorer"] = risk_result
    
    critic_agent = MockAgent("RedTeamCritic")
    critic_result = await critic_agent.run_with_timeout(query, context)
    
    # Step 3: Generate final result
    final_result = {
        "decision": "compliant" if risk_result["risk_score"] < 0.3 else "non_compliant",
        "confidence": risk_result["confidence"],
        "risk_score": risk_result["risk_score"],
        "rationale": f"Analysis completed with {len(results)} agents. MFA compliance verified through policy and evidence review.",
        "citations": [
            {"doc_id": "POLICY-001", "chunk_id": "MFA-001", "snippet": "MFA required for all logins"},
            {"doc_id": "SPEC-001", "chunk_id": "AUTH-001", "snippet": "SMS OTP implementation active"}
        ],
        "open_questions": critic_result.get("gaps_identified", []),
        "human_interactions": []
    }
    
    # Store result
    sessions[session_id] = {
        "session_id": session_id,
        "query": query,
        "created_at": datetime.utcnow().isoformat(),
        "agent_results": results,
        "final_result": final_result,
        "status": "completed"
    }
    
    print(f"✅ Session {session_id}: Workflow completed!")
    return final_result

@app.post("/ask")
async def ask_question(query: str):
    """Start a compliance analysis"""
    session_id = str(uuid.uuid4())
    
    # Start workflow in background
    asyncio.create_task(run_workflow(session_id, query))
    
    return {"session_id": session_id, "status": "started", "query": query}

@app.get("/result/{session_id}")
async def get_result(session_id: str):
    """Get final result for a session"""
    if session_id not in sessions:
        return {"error": "Session not found or still processing"}
    
    session = sessions[session_id]
    if "final_result" in session:
        return session["final_result"]
    else:
        return {"status": "processing", "message": "Analysis still running..."}

@app.get("/history/{session_id}")  
async def get_history(session_id: str):
    """Get full session history"""
    if session_id not in sessions:
        return {"error": "Session not found"}
    
    return sessions[session_id]

@app.get("/")
async def root():
    return {
        "message": "AI Compliance & Risk Orchestrator",
        "version": "minimal",
        "features": [
            "Multi-agent orchestration",
            "Parallel execution", 
            "Structured JSON output",
            "REST API endpoints"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting AI Compliance & Risk Orchestrator - Minimal Server")
    print("📍 Server will be available at: http://localhost:8000")
    print("📖 API docs at: http://localhost:8000/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)