#!/usr/bin/env python3
"""
Test script for IntelligentContactsAgent with Enhanced AgentServiceBase
"""

import asyncio
import sys
import os
from pathlib import Path

# Get absolute path to root directory
ROOT_DIR = Path(__file__).parent
CONTACTS_SRC = ROOT_DIR / "services" / "contacts-agent" / "src"
AGENT_SDK = ROOT_DIR / "services" / "agent-sdk"

# Add paths for proper imports
sys.path.insert(0, str(AGENT_SDK))
sys.path.insert(0, str(CONTACTS_SRC))

# Import with module path resolution
os.chdir(str(CONTACTS_SRC))
sys.path.insert(0, str(CONTACTS_SRC))

from kenny_agent.intelligent_contacts_agent import IntelligentContactsAgent

async def test_intelligent_contacts_agent():
    """Test the IntelligentContactsAgent functionality."""
    print("🧪 Testing IntelligentContactsAgent with Enhanced AgentServiceBase")
    print("=" * 70)
    
    # Initialize intelligent contacts agent
    print("\n1. Initializing IntelligentContactsAgent...")
    try:
        agent = IntelligentContactsAgent(llm_model="llama3.2:3b")
        print(f"✅ Created intelligent agent: {agent.agent_id}")
        print(f"   Agent type: {type(agent).__name__}")
        print(f"   Capabilities: {list(agent.capabilities.keys())}")
        print(f"   Dependencies: {list(agent.agent_dependencies.keys())}")
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Enhanced capability registration
    print("\n2. Testing enhanced capability registration...")
    expected_capabilities = ["contacts.resolve", "contacts.enrich", "contacts.merge"]
    missing_capabilities = [cap for cap in expected_capabilities if cap not in agent.capabilities]
    if missing_capabilities:
        print(f"❌ Missing capabilities: {missing_capabilities}")
        return False
    else:
        print(f"✅ All enhanced capabilities registered: {expected_capabilities}")
    
    # Test 3: Cross-platform dependencies
    print("\n3. Testing cross-platform dependencies...")
    expected_deps = ["mail-agent", "imessage-agent", "calendar-agent"]
    missing_deps = [dep for dep in expected_deps if dep not in agent.agent_dependencies]
    if missing_deps:
        print(f"⚠️  Missing dependencies (expected for isolated test): {missing_deps}")
    else:
        print(f"✅ All dependencies registered: {expected_deps}")
    
    # Test 4: Agent context for LLM
    print("\n4. Testing agent context for LLM...")
    context = agent.get_agent_context()
    if "natural language" in context.lower() and "contact" in context.lower():
        print(f"✅ Agent context contains expected keywords")
        print(f"   Context preview: {context[:100]}...")
    else:
        print(f"❌ Agent context missing expected content")
        print(f"   Context: {context}")
        return False
    
    # Test 5: Multi-platform context
    print("\n5. Testing multi-platform context...")
    multi_context = agent.get_multi_platform_context()
    if "Cross-platform integrations" in multi_context:
        print(f"✅ Multi-platform context includes integration info")
    else:
        print(f"❌ Multi-platform context missing integration info")
        return False
    
    # Test 6: Enhanced resolution method
    print("\n6. Testing enhanced contact resolution method...")
    try:
        # Test the resolve_contact_with_context method
        result = await agent.resolve_contact_with_context(
            query="Find John Smith",
            platforms=["contacts", "mail"]
        )
        print(f"✅ Enhanced resolution method executed successfully")
        print(f"   Result type: {type(result).__name__}")
        print(f"   Has confidence: {hasattr(result, 'confidence')}")
        print(f"   Has fallback info: {hasattr(result, 'fallback_used')}")
    except Exception as e:
        print(f"❌ Enhanced resolution failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 7: Relationship caching
    print("\n7. Testing relationship caching...")
    try:
        await agent.cache_entity_relationship(
            entity_type="contact",
            entity_id="test_contact_123",
            related_entity_type="email",
            related_entity_id="test@example.com",
            relationship_data={
                "type": "primary_email",
                "contact_name": "Test Contact",
                "confidence": 0.95
            }
        )
        
        relationships = await agent.get_entity_relationships(
            entity_type="contact",
            entity_id="test_contact_123",
            related_entity_type="email"
        )
        
        if relationships and len(relationships) > 0:
            print(f"✅ Relationship caching works: {len(relationships)} relationships found")
        else:
            print(f"❌ Relationship caching failed: no relationships retrieved")
            return False
    except Exception as e:
        print(f"❌ Relationship caching error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 8: Cross-platform enrichment method
    print("\n8. Testing cross-platform enrichment...")
    try:
        enrichment_result = await agent.enrich_contact_cross_platform("test_contact_123")
        print(f"✅ Cross-platform enrichment executed successfully")
        print(f"   Result keys: {list(enrichment_result.keys())}")
        print(f"   Has enrichments: {'enrichments' in enrichment_result}")
    except Exception as e:
        print(f"❌ Cross-platform enrichment failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 9: Start/stop functionality
    print("\n9. Testing agent start/stop functionality...")
    try:
        start_result = await agent.start()
        print(f"✅ Agent started successfully: {start_result}")
        
        stop_result = await agent.stop()
        print(f"✅ Agent stopped successfully: {stop_result}")
    except Exception as e:
        print(f"❌ Start/stop failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✅ All IntelligentContactsAgent tests completed successfully!")
    print("\n🎯 Contacts Agent transformation ready for Phase 1B!")
    return True

async def main():
    """Main test entry point."""
    try:
        success = await test_intelligent_contacts_agent()
        return success
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Restore original working directory
        os.chdir(str(ROOT_DIR))

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)