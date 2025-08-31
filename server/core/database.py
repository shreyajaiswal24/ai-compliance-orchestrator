from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import os
from models.schemas import SessionState, HumanInteraction, ComplianceResult

class DatabaseManager:
    def __init__(self):
        self.mongo_client: Optional[AsyncIOMotorClient] = None
        self.redis_client: Optional[redis.Redis] = None
        self.db = None
        
        # MongoDB connection string
        self.mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        self.db_name = os.getenv("DB_NAME", "compliance_orchestrator")
        
        # Redis connection
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        
    async def initialize(self):
        """Initialize database connections"""
        try:
            # Initialize MongoDB
            self.mongo_client = AsyncIOMotorClient(self.mongo_url)
            self.db = self.mongo_client[self.db_name]
            
            # Test MongoDB connection
            await self.mongo_client.admin.command('ismaster')
            print("Connected to MongoDB successfully")
            
            # Initialize collections
            await self._initialize_collections()
            
        except Exception as e:
            print(f"MongoDB connection failed, using in-memory fallback: {e}")
            # Use in-memory storage as fallback
            self._sessions = {}
            
        try:
            # Initialize Redis
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            print("Connected to Redis successfully")
            
        except Exception as e:
            print(f"Redis connection failed, using in-memory fallback: {e}")
            # Use in-memory cache as fallback
            self._cache = {}
    
    async def _initialize_collections(self):
        """Initialize MongoDB collections with indexes"""
        if self.db:
            # Create indexes for better performance
            await self.db.sessions.create_index("session_id", unique=True)
            await self.db.sessions.create_index("created_at")
            await self.db.agent_outputs.create_index([("session_id", 1), ("agent_name", 1)])
            await self.db.human_interactions.create_index([("session_id", 1), ("timestamp", 1)])
    
    async def create_session(self, session_id: str, query: str, attachments: List[str] = None) -> SessionState:
        """Create a new session"""
        session = SessionState(
            session_id=session_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            query=query,
            attachments=attachments or []
        )
        
        if self.db:
            await self.db.sessions.insert_one(session.dict())
        else:
            self._sessions[session_id] = session.dict()
            
        return session
    
    async def update_session(self, session_id: str, updates: Dict[str, Any]):
        """Update session with new data"""
        updates["updated_at"] = datetime.utcnow()
        
        if self.db:
            await self.db.sessions.update_one(
                {"session_id": session_id},
                {"$set": updates}
            )
        else:
            if session_id in self._sessions:
                self._sessions[session_id].update(updates)
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        if self.db:
            return await self.db.sessions.find_one({"session_id": session_id})
        else:
            return self._sessions.get(session_id)
    
    async def save_agent_output(self, session_id: str, agent_name: str, output: Dict[str, Any]):
        """Save agent execution output"""
        record = {
            "session_id": session_id,
            "agent_name": agent_name,
            "output": output,
            "timestamp": datetime.utcnow()
        }
        
        if self.db:
            await self.db.agent_outputs.insert_one(record)
        else:
            # Store in session for in-memory fallback
            if session_id in self._sessions:
                if "agent_outputs" not in self._sessions[session_id]:
                    self._sessions[session_id]["agent_outputs"] = {}
                self._sessions[session_id]["agent_outputs"][agent_name] = output
    
    async def save_human_interaction(self, session_id: str, interaction: HumanInteraction):
        """Save human interaction"""
        record = interaction.dict()
        record["session_id"] = session_id
        
        if self.db:
            await self.db.human_interactions.insert_one(record)
        else:
            # Store in session for in-memory fallback
            if session_id in self._sessions:
                if "human_interactions" not in self._sessions[session_id]:
                    self._sessions[session_id]["human_interactions"] = []
                self._sessions[session_id]["human_interactions"].append(record)
    
    async def save_final_result(self, session_id: str, result: ComplianceResult):
        """Save final compliance result"""
        await self.update_session(session_id, {"final_result": result.dict()})
    
    async def get_session_result(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get final result for session"""
        session = await self.get_session(session_id)
        if session:
            return session.get("final_result")
        return None
    
    async def get_session_history(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get complete session history"""
        session = await self.get_session(session_id)
        if not session:
            return None
            
        history = {
            "session": session,
            "agent_outputs": {},
            "human_interactions": []
        }
        
        if self.db:
            # Get agent outputs
            async for output in self.db.agent_outputs.find({"session_id": session_id}):
                history["agent_outputs"][output["agent_name"]] = output["output"]
            
            # Get human interactions
            async for interaction in self.db.human_interactions.find({"session_id": session_id}).sort("timestamp", 1):
                history["human_interactions"].append(interaction)
        else:
            # In-memory fallback
            history["agent_outputs"] = session.get("agent_outputs", {})
            history["human_interactions"] = session.get("human_interactions", [])
        
        return history
    
    # Redis caching methods
    async def cache_set(self, key: str, value: Any, ttl: int = 3600):
        """Set cache value with TTL"""
        if self.redis_client:
            await self.redis_client.setex(key, ttl, json.dumps(value))
        else:
            self._cache[key] = value
    
    async def cache_get(self, key: str) -> Optional[Any]:
        """Get cache value"""
        if self.redis_client:
            value = await self.redis_client.get(key)
            return json.loads(value) if value else None
        else:
            return self._cache.get(key)
    
    async def close(self):
        """Close database connections"""
        if self.mongo_client:
            self.mongo_client.close()
        if self.redis_client:
            await self.redis_client.close()