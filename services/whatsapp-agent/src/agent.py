"""
WhatsApp Agent for the Kenny v2 multi-agent system.

This agent provides WhatsApp functionality including message search and basic operations.
"""

import os
from typing import Dict, Any
from kenny_agent.base_agent import BaseAgent
from kenny_agent.health import HealthMonitor, HealthCheck, HealthStatus

from .handlers.search import SearchCapabilityHandler
from .tools.whatsapp_bridge import WhatsAppBridgeTool


class WhatsAppAgent(BaseAgent):
    """WhatsApp Agent providing WhatsApp-related capabilities."""
    
    def __init__(self):
        """Initialize the WhatsApp Agent."""
        super().__init__(
            agent_id="whatsapp-agent",
            name="WhatsApp Agent",
            description="Read-only WhatsApp message search and basic operations",
            data_scopes=["whatsapp:messages", "whatsapp:media"],
            tool_access=["macos-bridge", "sqlite-db"],
            egress_domains=[],
            health_check={"endpoint": "/health", "interval_seconds": 60, "timeout_seconds": 10}
        )
        
        print(f"Initializing WhatsApp Agent with ID: {self.agent_id}")
        
        # Register tools first so handlers can access them
        bridge_url = os.getenv("MAC_BRIDGE_URL", "http://localhost:5100")
        print(f"Registering WhatsApp bridge tool with URL: {bridge_url}")
        self.register_tool(WhatsAppBridgeTool(bridge_url))
        
        print(f"Registered tools: {list(self.tools.keys())}")
        
        # Register capabilities with agent reference
        print("Registering capabilities...")
        search_handler = SearchCapabilityHandler()
        search_handler._agent = self
        self.register_capability(search_handler)
        
        print(f"Registered capabilities: {list(self.capabilities.keys())}")
        
        # Set up health monitoring
        self.setup_health_monitoring()
        
        print("WhatsApp Agent initialization complete!")
    
    def setup_health_monitoring(self):
        """Set up health checks for the agent."""
        self.health_monitor = HealthMonitor("whatsapp_agent_monitor")
        
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
            message="WhatsApp Agent is operational",
            details={"agent_id": self.agent_id, "capabilities": len(self.capabilities)}
        )
    
    def check_capability_count(self):
        """Health check for capability count."""
        expected_capabilities = 1  # search (basic implementation)
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
        if "whatsapp_bridge" in self.tools:
            return HealthStatus(
                status="healthy",
                message="WhatsApp bridge tool is accessible",
                details={"tool_count": len(self.tools)}
            )
        else:
            return HealthStatus(
                status="unhealthy",
                message="WhatsApp bridge tool not accessible",
                details={"tool_count": len(self.tools)}
            )
    
    async def start(self):
        """Start the WhatsApp Agent."""
        print(f"Starting {self.name}...")
        print(f"Agent ID: {self.agent_id}")
        print(f"Capabilities: {list(self.capabilities.keys())}")
        print(f"Tools: {list(self.tools.keys())}")
        
        # Update health status
        self.update_health_status("healthy", "WhatsApp Agent started successfully")
        print("WhatsApp Agent started successfully!")
    
    async def stop(self):
        """Stop the WhatsApp Agent."""
        print(f"Stopping {self.name}...")
        self.update_health_status("degraded", "WhatsApp Agent stopping")
        print("WhatsApp Agent stopped.")