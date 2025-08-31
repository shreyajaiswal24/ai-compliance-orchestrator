from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import asyncio
import time
from tenacity import retry, stop_after_attempt, wait_exponential

class BaseAgent(ABC):
    def __init__(self, name: str, timeout: int = 30):
        self.name = name
        self.timeout = timeout
        self.execution_time = 0
        self.status = "idle"
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    @abstractmethod
    async def execute(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    async def run_with_timeout(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        self.status = "running"
        start_time = time.time()
        
        try:
            result = await asyncio.wait_for(
                self.execute(query, context),
                timeout=self.timeout
            )
            self.status = "completed"
            return result
        except asyncio.TimeoutError:
            self.status = "timeout"
            return {
                "agent": self.name,
                "status": "timeout",
                "error": f"Agent timed out after {self.timeout}s"
            }
        except Exception as e:
            self.status = "failed"
            return {
                "agent": self.name, 
                "status": "failed",
                "error": str(e)
            }
        finally:
            self.execution_time = time.time() - start_time