"""
End-to-end coordinator integration test for iMessage Agent.

This test validates that the iMessage Agent can properly integrate with
the Kenny v2 coordinator through the Agent Registry.
"""

import asyncio
import httpx
import json
from typing import Dict, Any


async def test_coordinator_integration():
    """Test the complete integration flow with coordinator."""
    
    print("=" * 60)
    print("iMessage Agent - Coordinator Integration Test")
    print("=" * 60)
    
    # Configuration
    agent_url = "http://localhost:8006"
    registry_url = "http://localhost:8001"
    
    results = {
        "health_check": False,
        "capabilities_list": False,
        "search_capability": False,
        "read_capability": False,
        "propose_reply_capability": False,
        "registry_registration": False
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        
        # 1. Test health endpoint
        print("\n1. Testing health endpoint...")
        try:
            response = await client.get(f"{agent_url}/health")
            if response.status_code == 200:
                health_data = response.json()
                print(f"   ✅ Health check passed: {health_data['status']}")
                results["health_check"] = True
            else:
                print(f"   ❌ Health check failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Health check error: {e}")
        
        # 2. Test capabilities listing
        print("\n2. Testing capabilities endpoint...")
        try:
            response = await client.get(f"{agent_url}/capabilities")
            if response.status_code == 200:
                capabilities_data = response.json()
                num_capabilities = len(capabilities_data["capabilities"])
                print(f"   ✅ Found {num_capabilities} capabilities")
                results["capabilities_list"] = True
            else:
                print(f"   ❌ Capabilities listing failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Capabilities listing error: {e}")
        
        # 3. Test messages.search capability
        print("\n3. Testing messages.search capability...")
        try:
            response = await client.post(
                f"{agent_url}/capabilities/messages.search",
                json={"input": {"query": "test", "limit": 3}}
            )
            if response.status_code == 200:
                search_data = response.json()
                num_results = search_data["output"]["count"]
                print(f"   ✅ Search returned {num_results} results")
                results["search_capability"] = True
            else:
                print(f"   ❌ Search capability failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Search capability error: {e}")
        
        # 4. Test messages.read capability
        print("\n4. Testing messages.read capability...")
        try:
            response = await client.post(
                f"{agent_url}/capabilities/messages.read",
                json={"input": {"message_id": "test_msg_1"}}
            )
            if response.status_code == 200:
                read_data = response.json()
                if "message" in read_data["output"]:
                    print(f"   ✅ Read capability executed successfully")
                    results["read_capability"] = True
            else:
                print(f"   ❌ Read capability failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Read capability error: {e}")
        
        # 5. Test messages.propose_reply capability
        print("\n5. Testing messages.propose_reply capability...")
        try:
            response = await client.post(
                f"{agent_url}/capabilities/messages.propose_reply",
                json={
                    "input": {
                        "message_content": "How are you?",
                        "thread_id": "test_thread",
                        "reply_style": "casual"
                    }
                }
            )
            if response.status_code == 200:
                reply_data = response.json()
                num_proposals = len(reply_data["output"]["proposals"])
                print(f"   ✅ Generated {num_proposals} reply proposals")
                results["propose_reply_capability"] = True
            else:
                print(f"   ❌ Propose reply capability failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Propose reply capability error: {e}")
        
        # 6. Test registry registration (if registry is running)
        print("\n6. Testing registry registration...")
        try:
            # Check if agent is registered
            response = await client.get(f"{registry_url}/agents")
            if response.status_code == 200:
                agents = response.json()
                imessage_agent = next(
                    (a for a in agents.get("agents", []) if a.get("agent_id") == "imessage-agent"),
                    None
                )
                if imessage_agent:
                    print(f"   ✅ Agent registered with registry")
                    results["registry_registration"] = True
                else:
                    print(f"   ⚠️  Agent not found in registry (may need manual registration)")
            else:
                print(f"   ⚠️  Registry not accessible (may not be running)")
        except Exception as e:
            print(f"   ⚠️  Registry check skipped: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:30} {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! iMessage Agent is ready for coordinator integration.")
    elif passed >= total - 1:  # Allow registry test to fail
        print("\n✅ Core tests passed! iMessage Agent is functional.")
    else:
        print("\n⚠️  Some tests failed. Please review the implementation.")
    
    return results


async def test_performance_metrics():
    """Test performance metrics for SLA compliance."""
    
    print("\n" + "=" * 60)
    print("PERFORMANCE METRICS TEST")
    print("=" * 60)
    
    agent_url = "http://localhost:8006"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Test response times
        import time
        
        # Health check performance
        start = time.time()
        response = await client.get(f"{agent_url}/health")
        health_time = (time.time() - start) * 1000
        print(f"Health check: {health_time:.1f}ms (SLA: <400ms)")
        
        # Search capability performance
        start = time.time()
        response = await client.post(
            f"{agent_url}/capabilities/messages.search",
            json={"input": {"query": "test", "limit": 5}}
        )
        search_time = (time.time() - start) * 1000
        print(f"Search capability: {search_time:.1f}ms (SLA: <2000ms)")
        
        # Read capability performance
        start = time.time()
        response = await client.post(
            f"{agent_url}/capabilities/messages.read",
            json={"input": {"message_id": "test_msg"}}
        )
        read_time = (time.time() - start) * 1000
        print(f"Read capability: {read_time:.1f}ms (SLA: <2000ms)")
        
        # Check SLA compliance
        sla_passed = (
            health_time < 400 and
            search_time < 2000 and
            read_time < 2000
        )
        
        if sla_passed:
            print("\n✅ All performance SLAs met!")
        else:
            print("\n⚠️  Some performance SLAs not met")


async def main():
    """Run all coordinator integration tests."""
    
    print("\n🚀 Starting iMessage Agent Coordinator Integration Tests\n")
    
    # Check if agent is running
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.get("http://localhost:8006/health")
    except:
        print("❌ iMessage Agent is not running on port 8006")
        print("Please start the agent with: python3 -m src.main")
        return
    
    # Run integration tests
    results = await test_coordinator_integration()
    
    # Run performance tests
    await test_performance_metrics()
    
    print("\n✅ Integration tests completed!\n")


if __name__ == "__main__":
    asyncio.run(main())