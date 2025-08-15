"""
iMessage Agent for the Kenny v2 multi-agent system.

This agent provides iMessage functionality including message search, read, and reply proposals
using macOS Bridge integration following established Agent SDK patterns.
"""

import os
from typing import Dict, Any
from kenny_agent.base_agent import BaseAgent
from kenny_agent.health import HealthMonitor, HealthCheck, HealthStatus

from .handlers.search import SearchCapabilityHandler
from .handlers.read import ReadCapabilityHandler
from .handlers.propose_reply import ProposeReplyCapabilityHandler
from .tools.imessage_bridge import iMessageBridgeTool


class iMessageAgent(BaseAgent):
    """iMessage Agent providing iMessage-related capabilities."""
    
    def __init__(self):
        """Initialize the iMessage Agent."""
        super().__init__(
            agent_id="imessage-agent",
            name="iMessage Agent",
            description="Read-only iMessage search, read, and reply proposal capabilities",
            data_scopes=["imessage:messages", "imessage:threads"],
            tool_access=["macos-bridge", "sqlite-db"],
            egress_domains=[],
            health_check={"endpoint": "/health", "interval_seconds": 60, "timeout_seconds": 10}
        )
        
        print(f"Initializing iMessage Agent with ID: {self.agent_id}")
        
        # Register tools first so handlers can access them
        bridge_url = os.getenv("MAC_BRIDGE_URL", "http://localhost:5100")
        print(f"Registering iMessage bridge tool with URL: {bridge_url}")
        self.register_tool(iMessageBridgeTool(bridge_url))
        
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
        
        print("iMessage Agent initialization complete!")
    
    def setup_health_monitoring(self):
        """Set up health checks for the agent."""
        self.health_monitor = HealthMonitor("imessage_agent_monitor")
        
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
        
        self.health_monitor.add_health_check(
            HealthCheck(
                name="bridge_connectivity",
                check_function=self.check_bridge_connectivity,
                description="Check macOS Bridge connectivity"
            )
        )
    
    def check_agent_status(self):
        """Health check for agent status."""
        return HealthStatus(
            status="healthy",
            message="iMessage Agent is operational",
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
        required_tools = ["imessage_bridge"]
        missing_tools = [tool for tool in required_tools if tool not in self.tools]
        
        if not missing_tools:
            return HealthStatus(
                status="healthy",
                message="All required tools are accessible",
                details={"tool_count": len(self.tools), "tools": list(self.tools.keys())}
            )
        else:
            return HealthStatus(
                status="degraded",
                message=f"Missing tools: {missing_tools}",
                details={"tool_count": len(self.tools), "missing": missing_tools}
            )
    
    def check_bridge_connectivity(self):
        """Health check for macOS Bridge connectivity."""
        try:
            bridge_tool = self.tools.get("imessage_bridge")
            if bridge_tool:
                # Test basic connectivity with a simple health check
                result = bridge_tool.execute({"operation": "health"})
                if result.get("status") == "ok" or not result.get("error"):
                    return HealthStatus(
                        status="healthy",
                        message="macOS Bridge is accessible",
                        details={"bridge_url": bridge_tool.bridge_url}
                    )
                else:
                    return HealthStatus(
                        status="degraded",
                        message="macOS Bridge connectivity issues",
                        details={"error": result.get("error", "Unknown error")}
                    )
            else:
                return HealthStatus(
                    status="unhealthy",
                    message="iMessage bridge tool not available",
                    details={}
                )
        except Exception as e:
            return HealthStatus(
                status="degraded",
                message="Bridge connectivity check failed",
                details={"error": str(e)}
            )
    
    async def start(self):
        """Start the iMessage Agent."""
        print(f"Starting {self.name}...")
        print(f"Agent ID: {self.agent_id}")
        print(f"Capabilities: {list(self.capabilities.keys())}")
        print(f"Tools: {list(self.tools.keys())}")
        
        # Update health status
        self.update_health_status("healthy", "iMessage Agent started successfully")
        print("iMessage Agent started successfully!")
    
    async def stop(self):
        """Stop the iMessage Agent."""
        print(f"Stopping {self.name}...")
        self.update_health_status("degraded", "iMessage Agent stopping")
        print("iMessage Agent stopped.")