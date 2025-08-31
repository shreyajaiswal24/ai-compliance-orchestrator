#!/usr/bin/env python3
"""
Demo scenarios for AI Compliance & Risk Orchestrator
Shows three key use cases as required by the assignment
"""

import asyncio
import httpx
import json
import websockets
import time
from typing import Dict, Any

class ComplianceDemo:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
        
    async def demo_1_compliant_decision(self):
        """Demo 1: A normal compliant decision (no HITL needed)"""
        print("🎯 DEMO 1: Compliant Decision (No HITL)")
        print("="*50)
        
        query = "Does our login system meet MFA requirements under our security policy?"
        
        async with httpx.AsyncClient() as client:
            # Start the analysis
            response = await client.post(f"{self.base_url}/ask", params={"query": query})
            data = response.json()
            
            if data["status"] == "started":
                session_id = data["session_id"]
                print(f"📊 Session started: {session_id}")
                print(f"🔍 Query: {query}")
                
                # Poll for results
                await self._wait_for_result(client, session_id)
                
    async def demo_2_hitl_workflow(self):
        """Demo 2: Workflow with 2 HITL interruptions"""
        print("\n🎯 DEMO 2: HITL Workflow (2 Interruptions)")
        print("="*50)
        
        query = "Assess compliance of our new mobile authentication system with enterprise security policies"
        
        # This will be a mock client that responds to HITL requests
        await self._run_hitl_demo(query)
        
    async def demo_3_insufficient_evidence(self):
        """Demo 3: Insufficient evidence after timeout + fallback"""
        print("\n🎯 DEMO 3: Insufficient Evidence (Timeout + Fallback)")
        print("="*50)
        
        query = "Review compliance of our legacy mainframe system with modern data protection regulations"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/ask", params={"query": query})
            data = response.json()
            
            if data["status"] == "started":
                session_id = data["session_id"]
                print(f"📊 Session started: {session_id}")
                print(f"🔍 Query: {query}")
                
                await self._wait_for_result(client, session_id)
    
    async def _wait_for_result(self, client: httpx.AsyncClient, session_id: str):
        """Wait for and display final result"""
        print("⏳ Waiting for analysis to complete...")
        
        # Wait a bit for processing
        await asyncio.sleep(8)
        
        try:
            response = await client.get(f"{self.base_url}/result/{session_id}")
            if response.status_code == 200:
                result = response.json()
                self._display_result(result)
            else:
                print(f"❌ Error getting result: {response.status_code}")
                
            # Get full history
            response = await client.get(f"{self.base_url}/history/{session_id}")
            if response.status_code == 200:
                history = response.json()
                self._display_execution_summary(history)
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    async def _run_hitl_demo(self, query: str):
        """Run a demo with simulated HITL interactions"""
        session_id = None
        
        # Start the workflow
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/ask", params={"query": query})
            data = response.json()
            session_id = data["session_id"]
            print(f"📊 Session started: {session_id}")
            print(f"🔍 Query: {query}")
        
        # Connect via WebSocket to handle HITL
        ws_url = f"{self.ws_url}/connect?session_id={session_id}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                print("🔗 Connected to WebSocket for HITL")
                
                hitl_count = 0
                timeout_count = 0
                max_wait = 30  # Maximum wait time
                
                while hitl_count < 2 and timeout_count < max_wait:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)
                        
                        if data["type"] == "progress_update":
                            progress = data["data"]
                            print(f"📈 Progress: {progress['stage']} - {progress['status']}")
                            
                        elif data["type"] == "hitl_request":
                            hitl_count += 1
                            await self._handle_mock_hitl_request(websocket, data["data"], hitl_count)
                            
                    except asyncio.TimeoutError:
                        timeout_count += 1
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        print("🔌 WebSocket connection closed")
                        break
                
                print(f"✅ Processed {hitl_count} HITL requests")
                
                # Wait a bit more for final processing
                await asyncio.sleep(3)
                
        except Exception as e:
            print(f"❌ WebSocket error: {e}")
        
        # Get final result
        if session_id:
            async with httpx.AsyncClient() as client:
                await self._wait_for_result(client, session_id)
    
    async def _handle_mock_hitl_request(self, websocket, request_data: Dict[str, Any], request_num: int):
        """Handle a HITL request with mock responses"""
        request_type = request_data.get("type")
        prompt = request_data.get("prompt")
        request_id = request_data.get("request_id")
        
        print(f"\n🤖 HITL REQUEST #{request_num} ({request_type}):")
        print(f"❓ {prompt}")
        
        # Mock responses based on request number
        if request_num == 1:
            mock_response = {
                "session_id": request_data["session_id"],
                "request_id": request_id,
                "response_type": "text",
                "payload": {"answer": "We use SMS-based OTP as primary MFA method with backup codes available"}
            }
            print("👤 User Response: SMS-based OTP with backup codes")
            
        elif request_num == 2:
            mock_response = {
                "session_id": request_data["session_id"],
                "request_id": request_id, 
                "response_type": "approval",
                "payload": {"approved": True}
            }
            print("👤 User Response: Approved")
        
        # Send response
        response_message = {
            "type": "hitl_response",
            "data": mock_response
        }
        
        await websocket.send(json.dumps(response_message))
        print("✅ Response sent to server")
    
    def _display_result(self, result: Dict[str, Any]):
        """Display compliance result in formatted way"""
        print("\n🎯 FINAL COMPLIANCE RESULT:")
        print("=" * 40)
        print(f"📋 Decision: {result['decision'].upper()}")
        print(f"🎯 Confidence: {result['confidence']:.2%}")
        print(f"⚠️  Risk Score: {result['risk_score']:.2%}")
        print(f"📝 Rationale: {result['rationale']}")
        
        if result['citations']:
            print(f"\n📚 Citations ({len(result['citations'])}):")
            for i, citation in enumerate(result['citations'][:3], 1):
                print(f"  {i}. {citation['doc_id']} - {citation['snippet'][:100]}...")
        
        if result['open_questions']:
            print(f"\n❓ Open Questions ({len(result['open_questions'])}):")
            for question in result['open_questions'][:3]:
                print(f"  • {question}")
        
        if result['human_interactions']:
            print(f"\n👥 Human Interactions ({len(result['human_interactions'])}):")
            for interaction in result['human_interactions']:
                print(f"  • {interaction['type']}: {interaction['status']}")
    
    def _display_execution_summary(self, history: Dict[str, Any]):
        """Display execution summary with timing"""
        print(f"\n⏱️  EXECUTION SUMMARY:")
        print("=" * 40)
        
        session = history['session']
        agent_outputs = history['agent_outputs']
        
        print(f"📅 Started: {session['created_at']}")
        print(f"🔄 Updated: {session['updated_at']}")
        
        print(f"\n🤖 Agent Execution:")
        for agent_name, output in agent_outputs.items():
            status = output.get('status', 'unknown')
            exec_time = output.get('execution_time', 0)
            print(f"  • {agent_name}: {status} ({exec_time:.2f}s)")
        
        total_interactions = len(history.get('human_interactions', []))
        print(f"\n👥 Human Interactions: {total_interactions}")

async def main():
    """Run all demo scenarios"""
    print("🚀 AI Compliance & Risk Orchestrator - Demo Suite")
    print("=" * 60)
    print("This demo shows three key scenarios from the assignment:")
    print("1. Normal compliant decision (no HITL)")
    print("2. Workflow with 2 HITL interruptions")  
    print("3. Insufficient evidence after timeout + fallback")
    print()
    
    demo = ComplianceDemo()
    
    try:
        await demo.demo_1_compliant_decision()
        await demo.demo_2_hitl_workflow()
        await demo.demo_3_insufficient_evidence()
        
        print("\n✅ All demos completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("Make sure the server is running: python server/main.py")

if __name__ == "__main__":
    asyncio.run(main())