"""
Base Agent class for the Kenny v2 multi-agent system.

This class provides the foundation for all agents, including capability
registration, execution, and manifest generation.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime, timezone


class BaseAgent(ABC):
    """
    Base class for all agents in the Kenny v2 system.
    
    Agents inherit from this class to get common functionality including:
    - Capability registration and execution
    - Tool registration and management
    - Health monitoring
    - Manifest generation
    """
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        version: str = "1.0.0",
        data_scopes: Optional[List[str]] = None,
        tool_access: Optional[List[str]] = None,
        egress_domains: Optional[List[str]] = None,
        health_check: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the base agent.
        
        Args:
            agent_id: Unique identifier for the agent
            name: Human-readable name for the agent
            description: Description of what the agent does
            version: Version string for the agent
            data_scopes: Data domains this agent can access
            tool_access: Local tools/endpoints this agent needs access to
            egress_domains: External domains this agent may need to access
            health_check: Health check configuration for the agent
        """
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.version = version
        self.data_scopes = data_scopes or []
        self.tool_access = tool_access or []
        self.egress_domains = egress_domains or []
        self.health_check = health_check or {"endpoint": "/health", "interval_seconds": 60, "timeout_seconds": 10}
        self.created_at = datetime.now(timezone.utc)
        self.last_updated = datetime.now(timezone.utc)
        
        # Capability and tool storage
        self.capabilities: Dict[str, Any] = {}
        self.tools: Dict[str, Any] = {}
        
        # Health status
        self.health_status = "healthy"
        self.health_message = "Agent operational"
        self.health_details: Dict[str, Any] = {}
    
    def register_capability(self, capability_handler: Any) -> None:
        """
        Register a capability handler with the agent.
        
        Args:
            capability_handler: Handler that implements the capability
        """
        if not hasattr(capability_handler, 'capability'):
            raise ValueError("Capability handler must have a 'capability' attribute")
        
        self.capabilities[capability_handler.capability] = capability_handler
        self.last_updated = datetime.now(timezone.utc)
    
    def register_tool(self, tool: Any) -> None:
        """
        Register a tool with the agent.
        
        Args:
            tool: Tool that can be used by the agent
        """
        if not hasattr(tool, 'name'):
            raise ValueError("Tool must have a 'name' attribute")
        
        self.tools[tool.name] = tool
        self.last_updated = datetime.now(timezone.utc)
    
    async def execute_capability(
        self, 
        capability: str, 
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a registered capability.
        
        Args:
            capability: Name of the capability to execute
            parameters: Parameters to pass to the capability
            
        Returns:
            Result of the capability execution
            
        Raises:
            ValueError: If the capability is not registered
        """
        if capability not in self.capabilities:
            raise ValueError(f"Unknown capability: {capability}")
        
        handler = self.capabilities[capability]
        
        if hasattr(handler, 'execute'):
            if asyncio.iscoroutinefunction(handler.execute):
                result = await handler.execute(parameters)
            else:
                result = handler.execute(parameters)
        else:
            raise ValueError(f"Capability handler {capability} has no execute method")
        
        return result
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """
        Execute a registered tool.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters to pass to the tool
            
        Returns:
            Result of the tool execution
            
        Raises:
            ValueError: If the tool is not registered
        """
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        tool = self.tools[tool_name]
        
        if hasattr(tool, 'execute'):
            result = tool.execute(parameters)
        else:
            raise ValueError(f"Tool {tool_name} has no execute method")
        
        return result
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get the current health status of the agent.
        
        Returns:
            Dictionary containing health information
        """
        return {
            "agent_id": self.agent_id,
            "status": self.health_status,
            "message": self.health_message,
            "details": self.health_details,
            "last_updated": self.last_updated.isoformat()
        }
    
    def update_health_status(
        self, 
        status: str, 
        message: str, 
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update the health status of the agent.
        
        Args:
            status: Health status (e.g., 'healthy', 'degraded', 'unhealthy')
            message: Human-readable health message
            details: Optional additional health details
        """
        self.health_status = status
        self.health_message = message
        if details:
            self.health_details.update(details)
        self.last_updated = datetime.now(timezone.utc)
    
    def generate_manifest(self) -> Dict[str, Any]:
        """
        Generate the agent manifest for registration.
        
        Returns:
            Dictionary containing agent manifest information
        """
        manifest = {
            "agent_id": self.agent_id,
            "version": self.version,
            "display_name": self.name,
            "description": self.description,
            "capabilities": [],
            "data_scopes": self.data_scopes,
            "tool_access": self.tool_access,
            "egress_domains": self.egress_domains,
            "health_check": self.health_check
        }
        
        # Add capability manifests
        for capability_name, handler in self.capabilities.items():
            if hasattr(handler, 'get_manifest'):
                capability_manifest = handler.get_manifest()
                manifest["capabilities"].append(capability_manifest)
            else:
                # Fallback capability manifest
                manifest["capabilities"].append({
                    "verb": capability_name,
                    "input_schema": {"type": "object"},
                    "output_schema": {"type": "object"},
                    "safety_annotations": ["read-only"],
                    "description": getattr(handler, 'description', 'No description available')
                })
        
        return manifest
    
    @abstractmethod
    async def start(self) -> None:
        """
        Start the agent. Must be implemented by subclasses.
        """
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """
        Stop the agent. Must be implemented by subclasses.
        """
        pass
    
    def __str__(self) -> str:
        """String representation of the agent."""
        return f"{self.name} ({self.agent_id}) - {self.description}"
    
    def __repr__(self) -> str:
        """Detailed string representation of the agent."""
        return (f"BaseAgent(agent_id='{self.agent_id}', name='{self.name}', "
                f"description='{self.description}', version='{self.version}')")
