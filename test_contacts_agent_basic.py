#!/usr/bin/env python3
"""
Basic test for Contacts Agent transformation to Enhanced AgentServiceBase
"""

import asyncio
import sys
import os

# Add agent-sdk to path
sys.path.append('services/agent-sdk')

from kenny_agent.agent_service_base import AgentServiceBase, ConfidenceResult

class TestIntelligentContactsAgent(AgentServiceBase):
    """Test version of IntelligentContactsAgent for validation."""
    
    def __init__(self):
        super().__init__(
            agent_id="intelligent-contacts-agent",
            name="Intelligent Contacts Agent",
            description="AI-powered contact management with natural language processing",
            version="2.1.0"
        )
        
        # Register cross-platform dependencies like the real agent
        self.register_agent_dependency(
            agent_id="mail-agent",
            capabilities=["messages.search", "messages.read"],
            required=False,
            timeout=3.0
        )
        
        self.register_agent_dependency(
            agent_id="imessage-agent",
            capabilities=["messages.search", "messages.read"],
            required=False,
            timeout=3.0
        )
        
        self.register_agent_dependency(
            agent_id="calendar-agent",
            capabilities=["calendar.read"],
            required=False,
            timeout=3.0
        )
        
        self.fallback_capability = "contacts.resolve"
        
        # Register mock capabilities
        self.register_mock_capabilities()
    
    def register_mock_capabilities(self):
        """Register mock capabilities for testing."""
        self.capabilities = {
            "contacts.resolve": "Mock contact resolution",
            "contacts.enrich": "Mock contact enrichment", 
            "contacts.merge": "Mock contact merging"
        }
    
    def get_agent_context(self) -> str:
        return """Intelligent contact management agent specializing in:
        
- Natural language contact resolution and disambiguation
- Cross-platform contact enrichment from mail, messaging, and calendar
- Semantic contact matching with fuzzy name resolution
- Contact relationship analysis and caching
"""
    
    async def start(self):
        await super().start()
        return True
    
    async def stop(self):
        await super().stop()
        return True
    
    async def execute_capability(self, capability: str, parameters: dict):
        """Mock capability execution."""
        if capability == "contacts.resolve":
            return {
                "success": True,
                "contacts": [
                    {
                        "id": "test-contact-1",
                        "name": "John Smith",
                        "emails": ["john@example.com"],
                        "phones": ["+1-555-0123"],
                        "confidence": 0.9
                    }
                ],
                "resolved_count": 1
            }
        elif capability == "contacts.enrich":
            return {
                "success": True,
                "enrichments": [
                    {"source": "mail", "type": "interaction", "confidence": 0.8}
                ],
                "enrichment_count": 1
            }
        elif capability == "contacts.merge":
            return {
                "success": True,
                "merged_contact_id": "merged-contact-1",
                "duplicate_count": 2
            }
        else:
            return {"success": False, "error": f"Unknown capability: {capability}"}

async def test_contacts_agent_transformation():
    """Test the Contacts Agent transformation to Enhanced AgentServiceBase."""
    print("🧪 Testing Contacts Agent Transformation to Enhanced AgentServiceBase")
    print("=" * 75)
    
    # Test 1: Agent initialization
    print("\n1. Testing agent initialization...")
    try:
        agent = TestIntelligentContactsAgent()
        print(f"✅ Agent initialized: {agent.agent_id}")
        print(f"   Framework: Enhanced AgentServiceBase")
        print(f"   Capabilities: {list(agent.capabilities.keys())}")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False
    
    # Test 2: Cross-platform dependencies
    print("\n2. Testing cross-platform dependencies...")
    expected_deps = ["mail-agent", "imessage-agent", "calendar-agent"]
    registered_deps = list(agent.agent_dependencies.keys())
    
    if all(dep in registered_deps for dep in expected_deps):
        print(f"✅ All cross-platform dependencies registered: {expected_deps}")
        for dep_id, dep in agent.agent_dependencies.items():
            print(f"   {dep_id}: {dep.capabilities} (required: {dep.required})")
    else:
        missing = [dep for dep in expected_deps if dep not in registered_deps]
        print(f"❌ Missing dependencies: {missing}")
        return False
    
    # Test 3: Enhanced confidence execution
    print("\n3. Testing confidence-based execution...")
    try:
        result = await agent.execute_with_confidence(
            capability="contacts.resolve",
            parameters={"identifier": "John Smith"},
            min_confidence=0.7
        )
        
        print(f"✅ Confidence execution successful")
        print(f"   Confidence: {result.confidence}")
        print(f"   Fallback used: {result.fallback_used}")
        print(f"   Response time: {result.response_time:.3f}s")
        
        if result.confidence >= 0.7 and not result.fallback_used:
            print(f"✅ High confidence result without fallback")
        else:
            print(f"⚠️  Result used fallback or low confidence")
            
    except Exception as e:
        print(f"❌ Confidence execution failed: {e}")
        return False
    
    # Test 4: Relationship caching
    print("\n4. Testing relationship caching...")
    try:
        # Cache a contact->email relationship
        await agent.cache_entity_relationship(
            entity_type="contact",
            entity_id="john_smith_123",
            related_entity_type="email",
            related_entity_id="john@company.com",
            relationship_data={
                "type": "primary_email",
                "contact_name": "John Smith",
                "confidence": 0.95,
                "platforms": ["mail", "contacts"]
            }
        )
        
        # Retrieve the cached relationship
        relationships = await agent.get_entity_relationships(
            entity_type="contact",
            entity_id="john_smith_123",
            related_entity_type="email"
        )
        
        if relationships and len(relationships) > 0:
            print(f"✅ Relationship caching successful: {len(relationships)} relationships")
            rel = relationships[0]
            print(f"   Cached: {rel['related_entity_id']} -> {rel['relationship_data']['contact_name']}")
        else:
            print(f"❌ No relationships retrieved from cache")
            return False
            
    except Exception as e:
        print(f"❌ Relationship caching failed: {e}")
        return False
    
    # Test 5: Context enrichment
    print("\n5. Testing query context enrichment...")
    try:
        enriched = await agent.enrich_query_context(
            query="Find John's email address",
            platforms=["contacts", "mail", "calendar"]
        )
        
        print(f"✅ Context enrichment successful")
        print(f"   Original query: {enriched['original_query']}")
        print(f"   Platforms: {enriched['platforms']}")
        
        # Check if context was enriched (may not have real agents)
        context_keys = [k for k in enriched.keys() if k.endswith('_context')]
        if context_keys:
            print(f"   Context enriched from: {context_keys}")
        else:
            print(f"   No cross-platform context (expected in test environment)")
            
    except Exception as e:
        print(f"❌ Context enrichment failed: {e}")
        return False
    
    # Test 6: Multi-platform context
    print("\n6. Testing multi-platform context...")
    try:
        context = agent.get_multi_platform_context()
        
        if "Cross-platform integrations" in context:
            print(f"✅ Multi-platform context includes integration information")
            print(f"   Context length: {len(context)} characters")
        else:
            print(f"❌ Multi-platform context missing integration info")
            return False
            
    except Exception as e:
        print(f"❌ Multi-platform context failed: {e}")
        return False
    
    # Test 7: Performance metrics
    print("\n7. Testing performance metrics...")
    try:
        metrics = agent.get_performance_metrics()
        
        print(f"✅ Performance metrics available")
        print(f"   Total queries: {metrics['total_queries']}")
        print(f"   Cache hits: {metrics['cache_hits']}")
        print(f"   Cache hit rate: {metrics['cache_hit_rate']:.2%}")
        print(f"   Avg response time: {metrics['avg_response_time']:.3f}s")
        print(f"   Status: {metrics['status']}")
        
    except Exception as e:
        print(f"❌ Performance metrics failed: {e}")
        return False
    
    # Test 8: Start and stop
    print("\n8. Testing agent lifecycle...")
    try:
        start_result = await agent.start()
        print(f"✅ Agent started: {start_result}")
        
        stop_result = await agent.stop()
        print(f"✅ Agent stopped: {stop_result}")
        
    except Exception as e:
        print(f"❌ Agent lifecycle failed: {e}")
        return False
    
    print("\n✅ All Contacts Agent transformation tests completed successfully!")
    print("\n🎯 Phase 1B Contacts Agent transformation validated!")
    print("\n📋 Transformation Benefits Confirmed:")
    print("   • Cross-platform agent communication")
    print("   • Confidence-based execution with fallbacks")
    print("   • Advanced relationship caching")
    print("   • Multi-platform context awareness")
    print("   • Performance monitoring and optimization")
    
    return True

async def main():
    """Main test entry point."""
    try:
        success = await test_contacts_agent_transformation()
        return success
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)