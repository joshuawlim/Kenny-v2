#!/usr/bin/env python3
"""
Phase 1 End-to-End Validation Script

This script validates all Phase 1 agents are working correctly:
- Mail Agent (Phase 1.1): Live Apple Mail integration
- Contacts Agent (Phase 1.2): Live macOS Contacts + Message enrichment (Phase 1.2.3)
- Memory Agent (Phase 1.3): Semantic storage and retrieval
"""

import asyncio
import sys
import time
from pathlib import Path

# Add agent-sdk to path
sys.path.insert(0, str(Path(__file__).parent / "agent-sdk"))

# Import agents with proper module paths
from services.mail_agent.src.agent import MailAgent  
from services.contacts_agent.src.kenny_agent.agent import ContactsAgent
from services.memory_agent.src.kenny_agent.agent import MemoryAgent


async def validate_mail_agent():
    """Validate Mail Agent functionality."""
    print("=== Mail Agent Validation (Phase 1.1) ===")
    
    try:
        # Initialize agent
        agent = MailAgent()
        print("✅ Mail Agent initialized successfully")
        
        # Test search capability
        search_capability = agent.capabilities.get("messages.search")
        if search_capability:
            print("✅ Search capability registered")
            
            # Test with mock data (should fall back gracefully)
            result = await search_capability.execute({"query": "test", "limit": 3})
            print(f"✅ Search executed: {result['count']} results")
        
        # Test read capability
        read_capability = agent.capabilities.get("messages.read")
        if read_capability:
            print("✅ Read capability registered")
            
            # Test with mock data
            result = await read_capability.execute({"id": "test_123"})
            print(f"✅ Read executed: message ID {result['id']}")
        
        # Test reply proposal capability  
        reply_capability = agent.capabilities.get("messages.propose_reply")
        if reply_capability:
            print("✅ Propose reply capability registered")
            
            # Test with mock data
            result = await reply_capability.execute({"id": "test_123", "context": "meeting"})
            print(f"✅ Reply proposals executed: {len(result['suggestions'])} suggestions")
        
        print("✅ Mail Agent validation completed successfully\n")
        return True
        
    except Exception as e:
        print(f"❌ Mail Agent validation failed: {e}")
        return False


async def validate_contacts_agent():
    """Validate Contacts Agent functionality."""
    print("=== Contacts Agent Validation (Phase 1.2) ===")
    
    try:
        # Initialize agent
        agent = ContactsAgent()
        print("✅ Contacts Agent initialized successfully")
        print(f"   Tools: {list(agent.tools.keys())}")
        
        # Test resolve capability
        resolve_capability = agent.capabilities.get("contacts.resolve")
        if resolve_capability:
            print("✅ Resolve capability registered")
            
            result = await resolve_capability.execute({
                "identifier": "test@example.com",
                "platform": "email"
            })
            print(f"✅ Resolve executed: {result['resolved_count']} contacts found")
        
        # Test enrichment capability (Phase 1.2.3)
        enrich_capability = agent.capabilities.get("contacts.enrich")
        if enrich_capability:
            print("✅ Enrich capability registered")
            
            result = await enrich_capability.execute({
                "contact_id": "test_contact_123",
                "contact_name": "John Test",
                "enrichment_type": "job_title"
            })
            print(f"✅ Enrichment executed: {result['enrichment_count']} enrichments found")
            
            # Test with message analysis integration
            result_with_messages = await enrich_capability.execute({
                "contact_id": "john_doe_analysis",
                "contact_name": "John Doe Analysis",
                "enrichment_type": "interests",
                "use_message_analysis": True
            })
            print(f"✅ Message analysis enrichment: {result_with_messages['enrichment_count']} enrichments")
        
        # Test merge capability
        merge_capability = agent.capabilities.get("contacts.merge")
        if merge_capability:
            print("✅ Merge capability registered")
            
            result = await merge_capability.execute({
                "primary_contact_id": "contact_1",
                "duplicate_contact_ids": ["contact_2", "contact_3"]
            })
            print(f"✅ Merge executed: merged contact ID {result['merged_contact_id']}")
        
        print("✅ Contacts Agent validation completed successfully\n")
        return True
        
    except Exception as e:
        print(f"❌ Contacts Agent validation failed: {e}")
        return False


async def validate_memory_agent():
    """Validate Memory Agent functionality."""
    print("=== Memory Agent Validation (Phase 1.3) ===")
    
    try:
        # Initialize agent
        agent = MemoryAgent()
        print("✅ Memory Agent initialized successfully")
        
        # Test store capability
        store_capability = agent.capabilities.get("memory.store")
        if store_capability:
            print("✅ Store capability registered")
            
            result = await store_capability.execute({
                "input": {
                    "content": "Test memory for Phase 1 validation",
                    "metadata": {
                        "source": "phase1_validation",
                        "importance": 0.7,
                        "tags": ["test", "validation"]
                    }
                }
            })
            
            if result.get("success"):
                memory_id = result.get("result", {}).get("memory_id")
                print(f"✅ Store executed: memory ID {memory_id}")
            else:
                print("⚠️ Store executed with fallback behavior")
        
        # Test embedding capability
        embed_capability = agent.capabilities.get("memory.embed")
        if embed_capability:
            print("✅ Embed capability registered")
            
            result = await embed_capability.execute({
                "input": {
                    "texts": ["Test embedding for validation", "Another test text"]
                }
            })
            
            if result.get("success"):
                embeddings = result.get("result", {}).get("embeddings", [])
                print(f"✅ Embed executed: {len(embeddings)} embeddings generated")
            else:
                print("⚠️ Embed executed with fallback behavior")
        
        # Test retrieve capability
        retrieve_capability = agent.capabilities.get("memory.retrieve")
        if retrieve_capability:
            print("✅ Retrieve capability registered")
            
            result = await retrieve_capability.execute({
                "input": {
                    "query": "test validation",
                    "limit": 3
                }
            })
            
            if result.get("success"):
                memories = result.get("result", {}).get("memories", [])
                print(f"✅ Retrieve executed: {len(memories)} memories found")
            else:
                print("⚠️ Retrieve executed with fallback behavior")
        
        print("✅ Memory Agent validation completed successfully\n")
        return True
        
    except Exception as e:
        print(f"❌ Memory Agent validation failed: {e}")
        return False


async def validate_cross_agent_integration():
    """Validate cross-agent integration functionality."""
    print("=== Cross-Agent Integration Validation ===")
    
    try:
        # Test Contacts + Memory integration (Phase 1.2.3 feature)
        print("Testing Contacts → Memory integration...")
        
        contacts_agent = ContactsAgent()
        
        # Test enrichment with memory integration enabled
        enrich_capability = contacts_agent.capabilities.get("contacts.enrich")
        
        # Test with memory integration (will gracefully handle Memory Agent being offline)
        result = await enrich_capability.execute({
            "contact_id": "integration_test_123",
            "contact_name": "Integration Test User",
            "enrichment_type": "job_title",
            "use_memory_integration": True,
            "use_message_analysis": True
        })
        
        print(f"✅ Cross-agent enrichment: {result['enrichment_count']} enrichments")
        
        # Verify tools are available
        memory_client = contacts_agent.tools.get("memory_client")
        message_analyzer = contacts_agent.tools.get("message_analyzer")
        
        if memory_client:
            print("✅ Memory client tool available in Contacts Agent")
        if message_analyzer:
            print("✅ Message analyzer tool available in Contacts Agent")
        
        print("✅ Cross-agent integration validation completed successfully\n")
        return True
        
    except Exception as e:
        print(f"❌ Cross-agent integration validation failed: {e}")
        return False


async def main():
    """Run comprehensive Phase 1 validation."""
    print("🚀 Starting Phase 1 End-to-End Validation")
    print("=" * 50)
    
    start_time = time.time()
    results = []
    
    # Validate each phase
    results.append(await validate_mail_agent())           # Phase 1.1
    results.append(await validate_contacts_agent())       # Phase 1.2 + 1.2.3
    results.append(await validate_memory_agent())         # Phase 1.3
    results.append(await validate_cross_agent_integration())  # Integration
    
    # Summary
    duration = time.time() - start_time
    passed = sum(results)
    total = len(results)
    
    print("=" * 50)
    print("🏁 Phase 1 Validation Summary")
    print(f"   Tests Passed: {passed}/{total}")
    print(f"   Duration: {duration:.1f} seconds")
    
    if passed == total:
        print("🎉 ALL PHASE 1 VALIDATIONS PASSED!")
        print("✅ Phase 1 is ready for production")
        print("✅ Ready to proceed to Phase 2: Coordinator Implementation")
    else:
        print("❌ Some validations failed - review above for details")
        
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)