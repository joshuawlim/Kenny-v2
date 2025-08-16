"""
Contacts Agent for the Kenny v2 multi-agent system.

This agent provides contact management and enrichment capabilities including:
- Contact resolution and disambiguation
- Contact enrichment from various sources
- Contact deduplication and merging
"""

import sys
import os
from pathlib import Path

# Add the agent-sdk to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "agent-sdk"))

from kenny_agent.base_agent import BaseAgent
from kenny_agent.registry import AgentRegistryClient
from kenny_agent.health import HealthMonitor

from .handlers.resolve import ResolveContactsHandler
from .handlers.enrich import EnrichContactsHandler
from .handlers.merge import MergeContactsHandler
from .tools.contacts_bridge import ContactsBridgeTool
from .tools.message_analyzer import MessageAnalyzer
from .tools.memory_client import MemoryClient


class ContactsAgent(BaseAgent):
    """
    Contacts Agent for contact management and enrichment.
    
    Capabilities:
    - contacts.resolve: Find and disambiguate contacts
    - contacts.enrich: Add additional contact information
    - contacts.merge: Merge duplicate contacts
    """
    
    def __init__(self):
        """Initialize the contacts agent with all capabilities and tools."""
        super().__init__(
            agent_id="contacts-agent",
            name="Contacts Agent",
            description="Contact management and enrichment with deduplication",
            version="1.0.0",
            data_scopes=["contacts:all", "mail:inbox", "mail:sent", "whatsapp:chats", "imessage:chats", "calendar:events"],
            tool_access=["macos-bridge", "sqlite-db", "ollama"],
            egress_domains=[],
            health_check={
                "endpoint": "/health",
                "interval_seconds": 60,
                "timeout_seconds": 10
            }
        )
        
        # Initialize tools
        self.message_analyzer = MessageAnalyzer()
        self.memory_client = MemoryClient()
        self.contacts_bridge_tool = ContactsBridgeTool()
        
        # Register tools
        self.register_tool(self.contacts_bridge_tool)
        self.register_tool(self.message_analyzer)
        self.register_tool(self.memory_client)
        
        # Register capability handlers (pass tools for integration)
        self.register_capability(ResolveContactsHandler(agent=self))
        self.register_capability(EnrichContactsHandler(
            agent=self,
            message_analyzer=self.message_analyzer,
            memory_client=self.memory_client
        ))
        self.register_capability(MergeContactsHandler(agent=self))
        
        # Initialize health monitor
        self.health_monitor = HealthMonitor(self)
        
        # Initialize registry client
        self.registry_client = AgentRegistryClient(
            base_url=os.getenv("AGENT_REGISTRY_URL", "http://localhost:8001")
        )
    
    async def start(self):
        """Start the agent and register with the registry."""
        try:
            # Try to register with agent registry using manifest
            try:
                manifest = self.generate_manifest()
                registration_data = {
                    "manifest": manifest,
                    "health_endpoint": "http://localhost:8003/health"
                }
                await self.registry_client.register_agent(registration_data)
                print(f"[contacts-agent] Successfully registered with registry")
            except Exception as registry_error:
                print(f"[contacts-agent] Warning: Could not register with registry: {registry_error}")
                print(f"[contacts-agent] Continuing without registry registration")
            
            # Health monitoring is passive - no start/stop needed
            print(f"[contacts-agent] Health monitoring ready")
            
            return True
        except Exception as e:
            print(f"[contacts-agent] Failed to start: {e}")
            return False
    
    async def stop(self):
        """Stop the agent and cleanup."""
        try:
            # Health monitoring is passive - no cleanup needed
            print(f"[contacts-agent] Health monitoring stopped")
            
            return True
        except Exception as e:
            print(f"[contacts-agent] Error during shutdown: {e}")
            return False
