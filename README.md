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
[Evidence Collector] ─┼─→ [Risk Scorer] ─→ [Red Team Critic] ─→ [Final Decision]
[Vision/OCR Agent] ───┤ ↑
[Code Scanner] ───────┘ │
[HITL Interruption Points]
