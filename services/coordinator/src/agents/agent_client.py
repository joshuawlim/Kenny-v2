import httpx
import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AgentMessage:
    """Message structure for agent communication"""
    sender: str
    recipient: str
    content: Dict[str, Any]
    message_id: str
    timestamp: float

class AgentClient:
    """Client for communicating with agents via the agent registry"""
    
    def __init__(self, registry_url: str = "http://localhost:8000"):
        self.registry_url = registry_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.agent_id = "coordinator"
    
    async def get_available_agents(self) -> List[Dict[str, Any]]:
        """Get list of available agents from registry"""
        try:
            response = await self.client.get(f"{self.registry_url}/agents")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get available agents: {e}")
            return []
    
    async def get_agent_capabilities(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get capabilities for a specific agent"""
        try:
            response = await self.client.get(f"{self.registry_url}/capabilities")
            response.raise_for_status()
            capabilities = response.json()
            # Filter capabilities for the specific agent
            agent_caps = [cap for cap in capabilities if cap.get("agent_id") == agent_id]
            return agent_caps
        except Exception as e:
            logger.error(f"Failed to get capabilities for agent {agent_id}: {e}")
            return []
    
    async def send_message_to_agent(self, agent_id: str, message: AgentMessage) -> bool:
        """Send a message to a specific agent"""
        try:
            # This would typically go through the agent registry or direct to the agent
            # For now, we'll simulate successful message sending
            logger.info(f"Sending message to agent {agent_id}: {message.content}")
            return True
        except Exception as e:
            logger.error(f"Failed to send message to agent {agent_id}: {e}")
            return False
    
    async def receive_message_from_agent(self, agent_id: str) -> Optional[AgentMessage]:
        """Receive a message from a specific agent"""
        try:
            # This would typically poll or receive from a message queue
            # For now, we'll simulate receiving a message
            logger.info(f"Receiving message from agent {agent_id}")
            return None  # No messages for now
        except Exception as e:
            logger.error(f"Failed to receive message from agent {agent_id}: {e}")
            return None
    
    async def execute_agent_capability(self, agent_id: str, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a capability on a specific agent"""
        try:
            # This would typically make an HTTP call to the agent's capability endpoint
            # For now, we'll simulate successful execution
            logger.info(f"Executing capability {capability} on agent {agent_id} with params {params}")
            
            # Simulate different capability responses
            if capability == "search_mail":
                return {"status": "success", "results": ["email1", "email2"], "count": 2}
            elif capability == "check_calendar":
                return {"status": "success", "events": ["meeting1", "meeting2"], "count": 2}
            else:
                return {"status": "success", "message": f"Executed {capability}"}
                
        except Exception as e:
            logger.error(f"Failed to execute capability {capability} on agent {agent_id}: {e}")
            return {"status": "error", "error": str(e)}
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        asyncio.create_task(self.close())
