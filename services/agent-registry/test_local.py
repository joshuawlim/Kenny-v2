#!/usr/bin/env python3
"""
Simple test script to verify the Agent Registry Service works locally
"""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from registry import AgentRegistry
from schemas import AgentManifest, Capability, AgentRegistration, HealthCheckConfig


async def test_registry():
    """Test the registry functionality"""
    print("🧪 Testing Agent Registry Service...")
    
    # Create registry
    registry = AgentRegistry()
    print("✅ Registry created successfully")
    
    # Create a test manifest
    manifest = AgentManifest(
        agent_id="test-mail-agent",
        version="1.0.0",
        display_name="Test Mail Agent",
        description="A test mail agent",
        capabilities=[
            Capability(
                verb="messages.search",
                input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"results": {"type": "array"}}},
                description="Search mail messages"
            )
        ],
        data_scopes=["mail:inbox", "mail:sent"],
        tool_access=["macos-bridge"],
        egress_domains=[],
        health_check=HealthCheckConfig(
            endpoint="/health",
            interval_seconds=60,
            timeout_seconds=10
        )
    )
    
    # Create registration
    registration = AgentRegistration(
        manifest=manifest,
        health_endpoint="http://localhost:8001"
    )
    
    # Register agent
    agent_status = await registry.register_agent(registration)
    print(f"✅ Agent registered: {agent_status.agent_id}")
    
    # List agents
    agents = await registry.list_agents()
    print(f"✅ Found {len(agents)} agents")
    
    # Get capabilities
    capabilities = await registry.get_capabilities()
    print(f"✅ Found {len(capabilities)} capability types")
    
    # Find agents for capability
    matching_agents = await registry.find_agents_for_capability("messages.search")
    print(f"✅ Found {len(matching_agents)} agents for 'messages.search'")
    
    # Get system health
    health = await registry.get_system_health()
    print(f"✅ System health: {health['status']}")
    
    # Unregister agent
    success = await registry.unregister_agent("test-mail-agent")
    print(f"✅ Agent unregistered: {success}")
    
    print("🎉 All tests passed! Agent Registry Service is working correctly.")


if __name__ == "__main__":
    asyncio.run(test_registry())
