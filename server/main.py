from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import json
import asyncio
import uuid
from typing import Dict, Set
from datetime import datetime

from models.schemas import HITLRequest, HITLResponse, ProgressUpdate, ComplianceResult
from core.database import DatabaseManager
from core.orchestrator import WorkflowOrchestrator
from core.guardrails import guardrails

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            
    async def send_hitl_request(self, session_id: str, request: HITLRequest):
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_text(json.dumps({
                "type": "hitl_request",
                "data": request.dict()
            }))
            
    async def send_progress_update(self, session_id: str, update: ProgressUpdate):
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_text(json.dumps({
                "type": "progress_update", 
                "data": update.dict()
            }))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database connections
    app.state.db_manager = DatabaseManager()
    await app.state.db_manager.initialize()
    
    # Initialize orchestrator
    app.state.orchestrator = WorkflowOrchestrator(app.state.db_manager)
    
    yield
    
    # Cleanup
    await app.state.db_manager.close()

app = FastAPI(
    title="AI Compliance & Risk Orchestrator",
    description="Multi-agent system for compliance checking with HITL",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = ConnectionManager()

@app.websocket("/connect")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "hitl_response":
                response = HITLResponse(**message["data"])
                # Process HITL response
                await app.state.orchestrator.handle_hitl_response(response)
                
    except WebSocketDisconnect:
        manager.disconnect(session_id)

@app.post("/ask")
async def ask_question(query: str, session_id: str = None):
    if not session_id:
        session_id = str(uuid.uuid4())
    
    # Validate query safety
    validation = guardrails.validate_query_safety(query)
    
    if not validation["is_safe"] or not validation["is_compliance_related"]:
        # Return safe refusal
        refusal = guardrails.create_safe_refusal(validation["reason"])
        
        # Log security event
        guardrails.log_security_event("unsafe_query", {
            "session_id": session_id,
            "query": query,
            "validation": validation
        })
        
        return {
            "session_id": session_id,
            "status": "refused",
            "result": refusal.dict(),
            "reason": validation["reason"]
        }
    
    # Check rate limits
    if not guardrails.check_rate_limit(session_id):
        return {
            "session_id": session_id,
            "status": "rate_limited",
            "error": "Too many requests. Please try again later."
        }
    
    # Start workflow in background
    task = asyncio.create_task(
        app.state.orchestrator.run_workflow(
            session_id=session_id,
            query=query,
            connection_manager=manager
        )
    )
    
    return {"session_id": session_id, "status": "started"}

@app.get("/result/{session_id}")
async def get_result(session_id: str):
    result = await app.state.db_manager.get_session_result(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    return result

@app.get("/history/{session_id}")
async def get_history(session_id: str):
    history = await app.state.db_manager.get_session_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found")
    return history

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)