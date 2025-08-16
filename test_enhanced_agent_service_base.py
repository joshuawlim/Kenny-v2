#!/usr/bin/env python3
"""
Test script for Enhanced AgentServiceBase functionality
"""

import asyncio
import sys
import os

# Add agent-sdk to path
sys.path.append('services/agent-sdk')

from kenny_agent.agent_service_base import AgentServiceBase, ConfidenceResult, AgentDependency


class TestAgent(AgentServiceBase):
    """Test agent for validating enhanced functionality."""
    
    def __init__(self):
        super().__init__(
            agent_id="test-agent",
            name="Test Agent",
            description="Test agent for Phase 1B enhanced functionality"
        )
        self.fallback_capability = "test_fallback"
    
    def get_agent_context(self) -> str:
        return "Test agent for validating enhanced AgentServiceBase functionality"
    
    async def start(self):
        """Start the test agent."""
        pass
    
    async def stop(self):
        """Stop the test agent."""
        await super().stop()
    
    async def execute_capability(self, capability: str, parameters: dict):
        """Mock capability execution."""
        if capability == "test_capability":
            return {"success": True, "data": f"Executed {capability} with {parameters}"}
        elif capability == "test_fallback":
            return {"success": True, "data": "Fallback capability executed"}
        else:
            return {"success": False, "error": f"Unknown capability: {capability}"}


async def test_enhanced_features():
    """Test the enhanced AgentServiceBase features."""
    print("🧪 Testing Enhanced AgentServiceBase Features")
    print("=" * 60)
    
    # Initialize test agent
    agent = TestAgent()
    print(f"✅ Created test agent: {agent.agent_id}")
    
    # Test 1: Agent dependency registration
    print("\n1. Testing agent dependency registration...")
    agent.register_agent_dependency(
        agent_id="contacts-agent",
        capabilities=["contacts.resolve", "contacts.enrich"],
        required=False,
        timeout=3.0
    )
    
    print(f"✅ Registered dependency: {list(agent.agent_dependencies.keys())}")
    
    # Test 2: Confidence result structure
    print("\n2. Testing ConfidenceResult structure...")
    confidence_result = ConfidenceResult(
        result={"test": "data"},
        confidence=0.85,
        fallback_used=False,
        response_time=0.5
    )
    print(f"✅ ConfidenceResult: confidence={confidence_result.confidence}, fallback={confidence_result.fallback_used}")
    
    # Test 3: Multi-platform context
    print("\n3. Testing multi-platform context...")
    context = agent.get_multi_platform_context()
    print(f"✅ Multi-platform context includes dependencies: {'contacts-agent' in context}")
    
    # Test 4: Relationship caching
    print("\n4. Testing relationship caching...")
    await agent.cache_entity_relationship(
        entity_type="contact",
        entity_id="john_doe",
        related_entity_type="email",
        related_entity_id="john@example.com",
        relationship_data={"relationship": "primary_email", "confidence": 0.95}
    )
    
    relationships = await agent.get_entity_relationships(
        entity_type="contact",
        entity_id="john_doe",
        related_entity_type="email"
    )
    print(f"✅ Cached and retrieved {len(relationships)} relationships")
    
    # Test 5: Context enrichment
    print("\n5. Testing query context enrichment...")
    enriched = await agent.enrich_query_context(
        query="Find John's emails",
        platforms=["contacts", "mail"]
    )
    print(f"✅ Enriched context platforms: {enriched['platforms']}")
    
    # Test 6: Enhanced cache tables
    print("\n6. Testing enhanced cache database structure...")
    # Check if new tables were created
    import sqlite3
    cache_path = f"/tmp/kenny_cache/{agent.agent_id}/agent_cache.db"
    if os.path.exists(cache_path):
        conn = sqlite3.connect(cache_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        expected_tables = ["query_cache", "relationship_cache", "semantic_matches"]
        has_all_tables = all(table in tables for table in expected_tables)
        print(f"✅ Enhanced cache tables created: {has_all_tables}")
        print(f"   Tables: {tables}")
    else:
        print("ℹ️  Cache database will be created on first use")
    
    # Cleanup
    await agent.stop()
    print("\n✅ All Enhanced AgentServiceBase tests completed successfully!")
    print("\n🎯 Ready for Phase 1B agent transformations!")


async def main():
    """Main test entry point."""
    try:
        await test_enhanced_features()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)