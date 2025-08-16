"""
Memory Agent for the Kenny v2 multi-agent system.

This agent provides memory and retrieval capabilities including:
- Semantic search across stored memories
- Text embedding generation using local models
- Memory storage with metadata and retention policies
"""

import sys
import os
import logging
from pathlib import Path

# Add the agent-sdk to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "agent-sdk"))

from kenny_agent.base_agent import BaseAgent
from kenny_agent.registry import AgentRegistryClient
from kenny_agent.health import HealthMonitor
from typing import Dict, Any, List, Optional

from .handlers.retrieve import MemoryRetrieveHandler
from .handlers.embed import MemoryEmbedHandler
from .handlers.store import MemoryStoreHandler
from .tools.ollama_client import OllamaClientTool
from .tools.chroma_client import ChromaClientTool


class MemoryAgent(BaseAgent):
    """
    Memory Agent for memory storage, retrieval, and semantic search.
    
    Capabilities:
    - memory.retrieve: Semantic search across stored data
    - memory.embed: Generate embeddings for text
    - memory.store: Store new memories with metadata
    """
    
    def __init__(self):
        """Initialize the memory agent with all capabilities and tools."""
        super().__init__(
            agent_id="memory-agent",
            name="Memory Agent",
            description="Memory storage, retrieval, and semantic search with local embedding generation",
            version="1.0.0",
            data_scopes=["memory:all", "mail:content", "contacts:interactions", "calendar:events", "messages:content"],
            tool_access=["ollama", "chromadb", "sqlite-db"],
            egress_domains=[],
            health_check={
                "endpoint": "/health",
                "interval_seconds": 60,
                "timeout_seconds": 10
            }
        )
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        
        # Register tools first
        ollama_tool = OllamaClientTool()
        chroma_tool = ChromaClientTool()
        self.register_tool(ollama_tool)
        self.register_tool(chroma_tool)
        
        # Register capability handlers with tool references
        self.register_capability(MemoryRetrieveHandler(ollama_tool, chroma_tool))
        self.register_capability(MemoryEmbedHandler(ollama_tool))
        self.register_capability(MemoryStoreHandler(ollama_tool, chroma_tool))
    
    async def start(self):
        """Start the memory agent and initialize services."""
        try:
            # Initialize health monitor
            self.health_monitor = HealthMonitor()
            
            # Initialize tools
            for tool in self.tools.values():
                if hasattr(tool, 'initialize'):
                    await tool.initialize()
            
            # Register with agent registry
            registry_client = AgentRegistryClient()
            try:
                manifest = self.generate_manifest()
                registration_data = {
                    "manifest": manifest,
                    "health_endpoint": "http://localhost:8004"
                }
                await registry_client.register_agent(registration_data)
                self.logger.info("Successfully registered with agent registry")
            except Exception as e:
                self.logger.warning(f"Failed to register with agent registry: {e}")
                # Continue anyway - agent can function without registry
            
            self.logger.info(f"Memory Agent started successfully")
            self.is_running = True
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start Memory Agent: {e}")
            return False
    
    async def stop(self):
        """Stop the memory agent and cleanup resources."""
        try:
            # Cleanup tools
            for tool in self.tools.values():
                if hasattr(tool, 'cleanup'):
                    await tool.cleanup()
            
            self.is_running = False
            self.logger.info("Memory Agent stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping Memory Agent: {e}")
            return False
    
    def get_capabilities(self) -> List[str]:
        """Get list of all available capabilities."""
        return list(self.capabilities.keys())
    
    def get_capability_info(self, capability_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific capability."""
        if capability_name not in self.capabilities:
            return None
        
        handler = self.capabilities[capability_name]
        return handler.get_manifest() if hasattr(handler, 'get_manifest') else {
            'capability': capability_name,
            'description': getattr(handler, 'description', 'No description available')
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status."""
        return {
            'agent_id': self.agent_id,
            'status': 'healthy' if self.is_running else 'stopped',
            'tools_status': {
                name: tool.execute({'operation': 'health_check'}) if hasattr(tool, 'execute') else 'unknown'
                for name, tool in self.tools.items()
            },
            'capabilities_count': len(self.capabilities),
            'tools_count': len(self.tools)
        }