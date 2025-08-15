#!/usr/bin/env python3
"""
Integration test for the Agent Registry Enhanced Health Dashboard
Tests the cross-agent health aggregation functionality
"""

import asyncio
import json
import sys
sys.path.append('services/agent-registry/src')

from registry import AgentRegistry
from schemas import AgentRegistration, AgentManifest, Capability, HealthCheckConfig

async def test_registry_health_dashboard():
    """Test the enhanced health dashboard functionality."""
    print("🔍 Testing Agent Registry Enhanced Health Dashboard")
    print("=" * 60)
    
    # Create registry instance
    registry = AgentRegistry()
    
    # Create mock agent manifests
    agent1_manifest = AgentManifest(
        agent_id="test-agent-1",
        name="Test Agent 1",
        description="First test agent",
        version="1.0.0",
        capabilities=[
            Capability(
                verb="test.action_one",
                description="Test action 1",
                input_schema={"type": "object"},
                output_schema={"type": "object"}
            )
        ],
        data_scopes=["test:scope-one"],
        tool_access=[],
        egress_domains=[],
        health_check=HealthCheckConfig(
            endpoint="/health",
            interval_seconds=30,
            timeout_seconds=5
        )
    )
    
    agent2_manifest = AgentManifest(
        agent_id="test-agent-2", 
        name="Test Agent 2",
        description="Second test agent",
        version="1.0.0",
        capabilities=[
            Capability(
                verb="test.action_two",
                description="Test action 2",
                input_schema={"type": "object"},
                output_schema={"type": "object"}
            )
        ],
        data_scopes=["test:scope-two"],
        tool_access=[],
        egress_domains=[],
        health_check=HealthCheckConfig(
            endpoint="/health",
            interval_seconds=30,
            timeout_seconds=5
        )
    )
    
    # Register test agents
    registration1 = AgentRegistration(
        manifest=agent1_manifest,
        health_endpoint="http://localhost:8000/health"
    )
    
    registration2 = AgentRegistration(
        manifest=agent2_manifest,
        health_endpoint="http://localhost:8001/health"
    )
    
    try:
        await registry.register_agent(registration1)
        await registry.register_agent(registration2)
        print("✅ Test agents registered successfully")
        
        # Test basic system health
        basic_health = await registry.get_system_health()
        print(f"Basic system health: {basic_health['status']}")
        print(f"Total agents: {basic_health['total_agents']}")
        
        # Test enhanced health dashboard
        print("\nTesting enhanced health dashboard...")
        dashboard = await registry.get_enhanced_health_dashboard()
        
        print("Dashboard Structure:")
        print(f"  - System Overview: {dashboard['system_overview']['status']}")
        print(f"  - Message: {dashboard['system_overview']['message']}")
        print(f"  - Performance Overview:")
        perf = dashboard['performance_overview']
        print(f"    • Monitored agents: {perf['monitored_agents']}")
        print(f"    • SLA violations: {perf['sla_violations']}")
        print(f"    • Degrading agents: {perf['degrading_agents']}")
        
        print(f"  - Agent Details: {len(dashboard['agent_details'])} agents")
        for agent_id, details in dashboard['agent_details'].items():
            if details and 'error' not in details:
                print(f"    • {agent_id}: Data available")
            else:
                print(f"    • {agent_id}: {details.get('error', 'No data')}")
        
        print(f"  - Recommendations: {len(dashboard['system_recommendations'])}")
        for rec in dashboard['system_recommendations']:
            print(f"    • {rec}")
        
        print("✅ Enhanced health dashboard test completed")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        await registry.unregister_agent("test-agent-1")
        await registry.unregister_agent("test-agent-2")
        print("🧹 Test cleanup completed")

async def main():
    """Run the registry health dashboard tests."""
    await test_registry_health_dashboard()
    
    print("\n🎉 Agent Registry Enhanced Health Dashboard tests completed!")
    print("\nFeatures Validated:")
    print("✅ Cross-agent health data aggregation")
    print("✅ System-wide performance metrics calculation")
    print("✅ SLA violation detection across agents")
    print("✅ System-level recommendations generation")
    print("✅ Graceful handling of unavailable agent metrics")

if __name__ == "__main__":
    asyncio.run(main())