"""
Mail Agent for the Kenny v2 multi-agent system.

This agent provides mail functionality including search, read, and reply proposals.
"""

import os
from typing import Dict, Any
from kenny_agent.base_agent import BaseAgent
from kenny_agent.registry import AgentRegistryClient
from kenny_agent.health import HealthMonitor, HealthCheck, HealthStatus

from .handlers.search import SearchCapabilityHandler
from .handlers.read import ReadCapabilityHandler
from .handlers.propose_reply import ProposeReplyCapabilityHandler
from .tools.mail_bridge import MailBridgeTool


class MailAgent(BaseAgent):
    """Mail Agent providing mail-related capabilities."""
    
    def __init__(self):
        """Initialize the Mail Agent."""
        super().__init__(
            agent_id="mail-agent",
            name="Mail Agent",
            description="Read-only mail search/read and reply proposals",
            data_scopes=["mail:inbox", "mail:sent"],
            tool_access=["macos-bridge", "sqlite-db", "ollama"],
            egress_domains=[],
            health_check={"endpoint": "/health", "interval_seconds": 60, "timeout_seconds": 10}
        )
        
        print(f"Initializing Mail Agent with ID: {self.agent_id}")
        
        # Register tools first so handlers can access them
        bridge_url = os.getenv("MAC_BRIDGE_URL", "http://localhost:5100")
        print(f"Registering mail bridge tool with URL: {bridge_url}")
        self.register_tool(MailBridgeTool(bridge_url))
        
        print(f"Registered tools: {list(self.tools.keys())}")
        
        # Register capabilities with agent reference
        print("Registering capabilities...")
        search_handler = SearchCapabilityHandler()
        search_handler._agent = self
        self.register_capability(search_handler)
        
        read_handler = ReadCapabilityHandler()
        read_handler._agent = self
        self.register_capability(read_handler)
        
        reply_handler = ProposeReplyCapabilityHandler()
        reply_handler._agent = self
        self.register_capability(reply_handler)
        
        print(f"Registered capabilities: {list(self.capabilities.keys())}")
        
        # Set up health monitoring
        self.setup_health_monitoring()
        
        # Initialize registry client
        self.registry_client = AgentRegistryClient(
            base_url=os.getenv("AGENT_REGISTRY_URL", "http://localhost:8001")
        )
        
        print("Mail Agent initialization complete!")
    
    def setup_health_monitoring(self):
        """Set up health checks for the agent."""
        self.health_monitor = HealthMonitor("mail_agent_monitor")
        
        # Add health checks
        self.health_monitor.add_health_check(
            HealthCheck(
                name="agent_status",
                check_function=self.check_agent_status,
                description="Check agent operational status",
                critical=True
            )
        )
        
        self.health_monitor.add_health_check(
            HealthCheck(
                name="capability_count",
                check_function=self.check_capability_count,
                description="Check number of registered capabilities"
            )
        )
        
        self.health_monitor.add_health_check(
            HealthCheck(
                name="tool_access",
                check_function=self.check_tool_access,
                description="Check tool accessibility"
            )
        )
    
    def check_agent_status(self):
        """Health check for agent status."""
        return HealthStatus(
            status="healthy",
            message="Mail Agent is operational",
            details={"agent_id": self.agent_id, "capabilities": len(self.capabilities)}
        )
    
    def check_capability_count(self):
        """Health check for capability count."""
        expected_capabilities = 3  # search, read, propose_reply
        if len(self.capabilities) >= expected_capabilities:
            return HealthStatus(
                status="healthy",
                message="All expected capabilities are registered",
                details={"capability_count": len(self.capabilities), "expected": expected_capabilities}
            )
        else:
            return HealthStatus(
                status="unhealthy",
                message="Missing expected capabilities",
                details={"capability_count": len(self.capabilities), "expected": expected_capabilities}
            )
    
    def check_tool_access(self):
        """Health check for tool accessibility."""
        if "mail_bridge" in self.tools:
            return HealthStatus(
                status="healthy",
                message="Mail bridge tool is accessible",
                details={"tool_count": len(self.tools)}
            )
        else:
            return HealthStatus(
                status="unhealthy",
                message="Mail bridge tool not accessible",
                details={"tool_count": len(self.tools)}
            )
    
    async def start(self):
        """Start the Mail Agent and register with the registry."""
        print(f"Starting {self.name}...")
        print(f"Agent ID: {self.agent_id}")
        print(f"Capabilities: {list(self.capabilities.keys())}")
        print(f"Tools: {list(self.tools.keys())}")
        
        # Try to register with agent registry
        try:
            manifest = self.generate_manifest()
            registration_data = {
                "manifest": manifest,
                "health_endpoint": "http://localhost:8000"
            }
            await self.registry_client.register_agent(registration_data)
            print(f"[mail-agent] Successfully registered with registry")
        except Exception as registry_error:
            print(f"[mail-agent] Warning: Could not register with registry: {registry_error}")
            print(f"[mail-agent] Continuing without registry registration")
        
        # Update health status
        self.update_health_status("healthy", "Mail Agent started successfully")
        print("Mail Agent started successfully!")
    
    async def stop(self):
        """Stop the Mail Agent."""
        print(f"Stopping {self.name}...")
        self.update_health_status("degraded", "Mail Agent stopping")
        print("Mail Agent stopped.")
