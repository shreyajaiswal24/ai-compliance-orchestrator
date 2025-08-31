import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import uuid
import json
from enum import Enum

from models.schemas import ComplianceResult, Citation, HumanInteraction, HITLRequest, HITLResponse, ProgressUpdate
from agents.policy_retriever import PolicyRetrieverAgent
from agents.evidence_collector import EvidenceCollectorAgent  
from agents.vision_ocr_agent import VisionOCRAgent
from agents.code_scanner import CodeScannerAgent
from agents.risk_scorer import RiskScorerAgent
from agents.red_team_critic import RedTeamCriticAgent
from core.database import DatabaseManager
from core.vector_store import RAGSystem

class WorkflowStage(Enum):
    PLANNING = "planner_started"
    PARALLEL_COLLECTION = "parallel_collection"
    RAG_COMPLETE = "rag_done" 
    PARALLEL_MERGE = "parallel_merge"
    RISK_SCORING = "risk_scoring"
    CRITIC_REVIEW = "critic_flags"
    HITL_AWAITING = "awaiting_human"
    FINALIZED = "finalized"
    ERROR = "error"

class WorkflowOrchestrator:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.rag_system = RAGSystem()
        
        # Initialize agents
        self.agents = {
            "policy_retriever": PolicyRetrieverAgent(),
            "evidence_collector": EvidenceCollectorAgent(),
            "vision_ocr": VisionOCRAgent(),
            "code_scanner": CodeScannerAgent(),
            "risk_scorer": RiskScorerAgent(),
            "red_team_critic": RedTeamCriticAgent()
        }
        
        # HITL response handlers
        self.pending_hitl_requests: Dict[str, asyncio.Event] = {}
        self.hitl_responses: Dict[str, Any] = {}
    
    async def run_workflow(self, session_id: str, query: str, connection_manager, attachments: List[str] = None):
        """Main workflow execution with DAG-style parallel processing"""
        
        # Create session
        await self.db_manager.create_session(session_id, query, attachments)
        
        try:
            # Stage 1: Planning
            await self._send_progress(connection_manager, session_id, WorkflowStage.PLANNING, "started")
            context = {
                "query": query,
                "attachments": attachments or [],
                "session_id": session_id
            }
            
            # Stage 2: Parallel Collection (Policy, Evidence, Vision, Code)
            await self._send_progress(connection_manager, session_id, WorkflowStage.PARALLEL_COLLECTION, "started")
            
            # Execute collection agents in parallel
            collection_tasks = [
                self._run_agent_with_context("policy_retriever", query, context),
                self._run_agent_with_context("evidence_collector", query, context), 
                self._run_agent_with_context("vision_ocr", query, context),
                self._run_agent_with_context("code_scanner", query, context)
            ]
            
            collection_results = await asyncio.gather(*collection_tasks, return_exceptions=True)
            
            # Process collection results
            for i, result in enumerate(collection_results):
                agent_name = ["policy_retriever", "evidence_collector", "vision_ocr", "code_scanner"][i]
                if isinstance(result, Exception):
                    print(f"Agent {agent_name} failed: {result}")
                    result = {"agent": agent_name, "status": "failed", "error": str(result)}
                
                context[agent_name] = result
                await self.db_manager.save_agent_output(session_id, agent_name, result)
            
            await self._send_progress(connection_manager, session_id, WorkflowStage.RAG_COMPLETE, "completed")
            
            # Stage 3: Risk Scoring (depends on collection results)
            await self._send_progress(connection_manager, session_id, WorkflowStage.RISK_SCORING, "started")
            
            risk_result = await self._run_agent_with_context("risk_scorer", query, context)
            context["risk_scorer"] = risk_result
            await self.db_manager.save_agent_output(session_id, "risk_scorer", risk_result)
            
            # Stage 4: Red Team Critic (depends on risk scoring)
            await self._send_progress(connection_manager, session_id, WorkflowStage.CRITIC_REVIEW, "started") 
            
            critic_result = await self._run_agent_with_context("red_team_critic", query, context)
            context["red_team_critic"] = critic_result
            await self.db_manager.save_agent_output(session_id, "red_team_critic", critic_result)
            
            # Stage 5: Check if HITL is needed
            needs_hitl = critic_result.get("needs_hitl", False)
            
            if needs_hitl:
                await self._send_progress(connection_manager, session_id, WorkflowStage.HITL_AWAITING, "started")
                
                # Send HITL requests based on critic findings
                follow_up_questions = critic_result.get("follow_up_questions", [])
                
                for question in follow_up_questions[:2]:  # Limit to 2 questions for demo
                    hitl_response = await self._request_human_input(
                        connection_manager, 
                        session_id, 
                        "clarification",
                        question
                    )
                    
                    if hitl_response:
                        context["hitl_responses"] = context.get("hitl_responses", [])
                        context["hitl_responses"].append(hitl_response)
            
            # Stage 6: Final Decision
            await self._send_progress(connection_manager, session_id, WorkflowStage.FINALIZED, "started")
            
            final_result = await self._generate_final_result(context)
            await self.db_manager.save_final_result(session_id, final_result)
            
            await self._send_progress(connection_manager, session_id, WorkflowStage.FINALIZED, "completed", 
                                    {"decision": final_result.decision, "confidence": final_result.confidence})
            
            return final_result
            
        except Exception as e:
            await self._send_progress(connection_manager, session_id, WorkflowStage.ERROR, "failed", {"error": str(e)})
            raise
    
    async def _run_agent_with_context(self, agent_name: str, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Run an agent with current context"""
        agent = self.agents[agent_name]
        
        # Add RAG context for retrieval agents
        if agent_name == "policy_retriever":
            policies = await self.rag_system.retrieve_policies(query)
            context["available_policies"] = policies
        elif agent_name == "evidence_collector":
            evidence = await self.rag_system.retrieve_evidence(query) 
            context["available_evidence"] = evidence
        elif agent_name == "vision_ocr":
            # Provide RAG system to Vision/OCR agent for indexing
            context["rag_system"] = self.rag_system
            # Also retrieve existing vision/OCR content relevant to query
            vision_content = await self.rag_system.retrieve_vision_ocr(query)
            context["available_vision_content"] = vision_content
            
        return await agent.run_with_timeout(query, context)
    
    async def _request_human_input(self, connection_manager, session_id: str, request_type: str, prompt: str) -> Optional[Dict[str, Any]]:
        """Request input from human via HITL"""
        request_id = str(uuid.uuid4())
        
        hitl_request = HITLRequest(
            session_id=session_id,
            request_id=request_id,
            type=request_type,
            prompt=prompt
        )
        
        # Create event to wait for response
        self.pending_hitl_requests[request_id] = asyncio.Event()
        
        # Send request to client
        await connection_manager.send_hitl_request(session_id, hitl_request)
        
        # Wait for response with timeout
        try:
            await asyncio.wait_for(self.pending_hitl_requests[request_id].wait(), timeout=60.0)
            response = self.hitl_responses.get(request_id)
            
            # Save interaction
            interaction = HumanInteraction(
                timestamp=datetime.utcnow(),
                type=request_type,
                prompt=prompt,
                response=str(response.get("payload", {})) if response else "timeout",
                status="provided" if response else "timeout"
            )
            await self.db_manager.save_human_interaction(session_id, interaction)
            
            return response
            
        except asyncio.TimeoutError:
            # Handle timeout
            interaction = HumanInteraction(
                timestamp=datetime.utcnow(),
                type=request_type,
                prompt=prompt, 
                response="",
                status="timeout"
            )
            await self.db_manager.save_human_interaction(session_id, interaction)
            return None
        finally:
            # Cleanup
            self.pending_hitl_requests.pop(request_id, None)
            self.hitl_responses.pop(request_id, None)
    
    async def handle_hitl_response(self, response: HITLResponse):
        """Handle HITL response from client"""
        request_id = response.request_id
        
        if request_id in self.pending_hitl_requests:
            self.hitl_responses[request_id] = response.dict()
            self.pending_hitl_requests[request_id].set()
    
    async def _generate_final_result(self, context: Dict[str, Any]) -> ComplianceResult:
        """Generate final compliance result based on all agent outputs"""
        
        # Extract data from agent outputs
        policy_data = context.get("policy_retriever", {})
        evidence_data = context.get("evidence_collector", {})
        vision_data = context.get("vision_ocr", {})
        code_data = context.get("code_scanner", {})
        risk_data = context.get("risk_scorer", {})
        critic_data = context.get("red_team_critic", {})
        
        # Generate citations
        citations = []
        
        # Add policy citations
        if policy_data.get("policies"):
            for policy in policy_data["policies"]:
                citations.append(Citation(
                    doc_id=policy.get("doc_id", "unknown"),
                    chunk_id=policy.get("chunk_id", "unknown"), 
                    snippet=policy.get("snippet", "")
                ))
        
        # Add evidence citations
        if evidence_data.get("evidence"):
            for evidence in evidence_data["evidence"]:
                citations.append(Citation(
                    doc_id=evidence.get("doc_id", "unknown"),
                    chunk_id=evidence.get("chunk_id", "unknown"),
                    snippet=evidence.get("snippet", "")
                ))
        
        # Add vision/OCR citations
        if vision_data.get("vision_evidence"):
            for vision_doc in vision_data["vision_evidence"]:
                citations.append(Citation(
                    doc_id=vision_doc.get("doc_id", "unknown"),
                    chunk_id=vision_doc.get("chunk_id", "unknown"),
                    snippet=vision_doc.get("content", "")
                ))
        
        # Determine decision logic
        risk_score = risk_data.get("risk_score", 0.5)
        confidence = risk_data.get("confidence", 0.5)
        
        if risk_score < 0.3 and confidence > 0.8:
            decision = "compliant"
        elif risk_score > 0.7 or confidence < 0.6:
            decision = "insufficient_evidence" 
        else:
            decision = "non_compliant"
        
        # Generate rationale
        rationale_parts = [
            f"Risk assessment score: {risk_score:.2f}",
            f"Analysis confidence: {confidence:.2f}",
        ]
        
        if policy_data.get("policies"):
            rationale_parts.append(f"Found {len(policy_data['policies'])} relevant policy references")
        
        if evidence_data.get("evidence"):
            rationale_parts.append(f"Identified {len(evidence_data['evidence'])} pieces of supporting evidence")
        
        if vision_data.get("vision_evidence"):
            rationale_parts.append(f"Processed {len(vision_data['vision_evidence'])} visual/OCR evidence items")
        
        if code_data.get("compliance_items", 0) > 0:
            rationale_parts.append(f"Code analysis found {code_data['compliance_items']} compliance-relevant implementations")
        
        if critic_data.get("gaps_identified"):
            rationale_parts.append(f"Critic identified {len(critic_data['gaps_identified'])} potential gaps")
        
        rationale = ". ".join(rationale_parts) + "."
        
        # Collect human interactions
        human_interactions = []
        hitl_responses = context.get("hitl_responses", [])
        for resp in hitl_responses:
            human_interactions.append(HumanInteraction(
                timestamp=datetime.utcnow(),
                type="clarification",
                prompt=resp.get("prompt", ""),
                response=str(resp.get("payload", {})),
                status="provided"
            ))
        
        return ComplianceResult(
            decision=decision,
            confidence=confidence,
            risk_score=risk_score,
            rationale=rationale,
            citations=citations,
            open_questions=critic_data.get("follow_up_questions", []),
            human_interactions=human_interactions
        )
    
    async def _send_progress(self, connection_manager, session_id: str, stage: WorkflowStage, status: str, meta: Dict[str, Any] = None):
        """Send progress update to client"""
        update = ProgressUpdate(
            stage=stage.value,
            status=status,
            meta=meta
        )
        await connection_manager.send_progress_update(session_id, update)