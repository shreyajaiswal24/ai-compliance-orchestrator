import asyncio
import websockets
import json
import uuid
from typing import Dict, Any
import sys

class HITLClient:
    def __init__(self, server_url: str = "ws://localhost:8000"):
        self.server_url = f"{server_url}/connect"
        self.session_id = str(uuid.uuid4())
        self.websocket = None
        
    async def connect(self):
        """Connect to the server"""
        try:
            self.websocket = await websockets.connect(f"{self.server_url}?session_id={self.session_id}")
            print(f"Connected to server with session ID: {self.session_id}")
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
    
    async def listen_for_requests(self):
        """Listen for HITL requests from server"""
        if not self.websocket:
            print("Not connected to server")
            return
            
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self.handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            print("Connection to server closed")
        except Exception as e:
            print(f"Error listening for requests: {e}")
    
    async def handle_message(self, message: Dict[str, Any]):
        """Handle incoming messages from server"""
        msg_type = message.get("type")
        
        if msg_type == "hitl_request":
            await self.handle_hitl_request(message["data"])
        elif msg_type == "progress_update":
            await self.handle_progress_update(message["data"])
        else:
            print(f"Unknown message type: {msg_type}")
    
    async def handle_hitl_request(self, request_data: Dict[str, Any]):
        """Handle HITL request from server"""
        request_type = request_data.get("type")
        prompt = request_data.get("prompt")
        request_id = request_data.get("request_id")
        required_artifact = request_data.get("required_artifact")
        
        print(f"\n🤖 HITL REQUEST ({request_type}):")
        print(f"📝 {prompt}")
        
        if required_artifact:
            print(f"📎 Required artifact: {required_artifact}")
        
        # Get user input
        if request_type == "clarification":
            response = await self.get_user_clarification()
            response_data = {
                "session_id": self.session_id,
                "request_id": request_id,
                "response_type": "text",
                "payload": {"answer": response}
            }
        elif request_type == "approval":
            approved = await self.get_user_approval()
            response_data = {
                "session_id": self.session_id, 
                "request_id": request_id,
                "response_type": "approval",
                "payload": {"approved": approved}
            }
        elif request_type == "upload_request":
            file_path = await self.get_user_upload()
            response_data = {
                "session_id": self.session_id,
                "request_id": request_id, 
                "response_type": "upload",
                "payload": {"file_path": file_path}
            }
        else:
            print(f"Unknown request type: {request_type}")
            return
        
        # Send response back to server
        await self.send_response(response_data)
    
    async def handle_progress_update(self, update_data: Dict[str, Any]):
        """Handle progress updates from server"""
        stage = update_data.get("stage", "unknown")
        status = update_data.get("status", "unknown")
        meta = update_data.get("meta", {})
        
        print(f"📊 Progress: {stage} - {status}")
        if meta:
            print(f"   Details: {meta}")
    
    async def get_user_clarification(self) -> str:
        """Get clarification from user"""
        print("💬 Please provide clarification:")
        
        # In a real implementation, you'd use input()
        # For demo purposes, return a mock response
        mock_responses = [
            "We use SMS-based OTP as primary MFA method",
            "Yes, we have backup codes available for emergency access",
            "MFA is mandatory for all users accessing the system"
        ]
        
        import random
        response = random.choice(mock_responses)
        print(f"👤 User response: {response}")
        return response
    
    async def get_user_approval(self) -> bool:
        """Get approval from user"""
        print("🔍 Please approve or deny:")
        print("Type 'yes' or 'no':")
        
        # Mock approval for demo
        approval = True
        print(f"👤 User approval: {'approved' if approval else 'denied'}")
        return approval
    
    async def get_user_upload(self) -> str:
        """Get file upload from user"""
        print("📁 Please provide file path for upload:")
        
        # Mock file path for demo
        file_path = "/mock/screenshot.png"
        print(f"👤 User upload: {file_path}")
        return file_path
    
    async def send_response(self, response_data: Dict[str, Any]):
        """Send response back to server"""
        if self.websocket:
            message = {
                "type": "hitl_response",
                "data": response_data
            }
            await self.websocket.send(json.dumps(message))
            print("✅ Response sent to server")
    
    async def disconnect(self):
        """Disconnect from server"""
        if self.websocket:
            await self.websocket.close()
            print("Disconnected from server")

async def main():
    client = HITLClient()
    
    if await client.connect():
        print("🎯 HITL Client started. Waiting for requests...")
        await client.listen_for_requests()
    
    await client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nClient stopped by user")