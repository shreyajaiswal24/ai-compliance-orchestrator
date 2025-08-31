# AI Compliance & Risk Orchestrator

A multi-agent system for automated compliance checking with Human-in-the-Loop (HITL) capabilities. Built for the AI Software Developer Intern assignment.

## 🏗️ Architecture

### Core Components
- **FastAPI Server**: REST API + WebSocket endpoints
- **6 Specialized Agents**: Policy Retrieval, Evidence Collection, Vision/OCR, Code Scanning, Risk Scoring, Red Team Critic
- **DAG Orchestrator**: Parallel execution with `asyncio.gather()`
- **HITL System**: Server-initiated WebSocket requests to human client
- **Database Layer**: MongoDB (sessions/state) + Redis (caching)
- **RAG System**: FAISS vector store for policy/evidence retrieval

### Agent Workflow (DAG)
[Policy Retriever] ──┐
[Evidence Collector] ─┼
[Vision/OCR Agent] ───┤ ↑
[Code Scanner] ───────┘ │
[HITL Interruption Points]

**1.Running the System**
Start the Server
cd server
python main.py'
Server runs on http://localhost:8000

**2.Run HITL Client**
cd client
python hitl_client.py

**3.Run Demo Scenarios**
cd demo
python demo_scenarios.py

**Agent Timeouts**
Policy Retriever: 20s
Evidence Collector: 25s
Vision/OCR: 15s
Code Scanner: 20s
Risk Scorer: 10s
Red Team Critic: 15s

📈 **Reliability Features**
Timeouts with configurable limits
Retries using exponential backoff
Circuit Breaker for failed agents
Graceful Degradation with mock responses
Parallel Execution via asyncio.gather()
State Management with MongoDB, Redis, and in-memory fallback

🧪 **Multimodal Support**
OCR with pytesseract and preprocessing
Fallback mock responses for demo
Supported formats: PNG, JPG, JPEG, TIFF, BMP
Image analysis integrated into compliance reasoning
