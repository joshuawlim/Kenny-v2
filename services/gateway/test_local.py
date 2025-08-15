#!/usr/bin/env python3
"""
Local test script for Kenny v2 Gateway
Tests direct agent routing and performance
"""

import asyncio
import httpx
import time
import json
from typing import Dict, Any

class GatewayTester:
    def __init__(self):
        self.gateway_url = "http://localhost:9000"
        self.agent_registry_url = "http://localhost:8001"
        
    async def test_health(self) -> Dict[str, Any]:
        """Test gateway health endpoint"""
        print("🔍 Testing gateway health...")
        
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            
            try:
                response = await client.get(f"{self.gateway_url}/health")
                duration_ms = int((time.time() - start_time) * 1000)
                
                if response.status_code == 200:
                    health_data = response.json()
                    print(f"✅ Health check passed ({duration_ms}ms)")
                    print(f"   System status: {health_data.get('system', {}).get('status', 'unknown')}")
                    print(f"   Total agents: {health_data.get('system', {}).get('total_agents', 0)}")
                    return {"success": True, "duration_ms": duration_ms, "data": health_data}
                else:
                    print(f"❌ Health check failed: {response.status_code}")
                    return {"success": False, "status_code": response.status_code}
                    
            except Exception as e:
                print(f"❌ Health check error: {e}")
                return {"success": False, "error": str(e)}
    
    async def test_agents_endpoint(self) -> Dict[str, Any]:
        """Test agents discovery endpoint"""
        print("🔍 Testing agents discovery...")
        
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            
            try:
                response = await client.get(f"{self.gateway_url}/agents")
                duration_ms = int((time.time() - start_time) * 1000)
                
                if response.status_code == 200:
                    agents_data = response.json()
                    agent_count = len(agents_data.get("agents", []))
                    print(f"✅ Agents discovery passed ({duration_ms}ms)")
                    print(f"   Found {agent_count} agents")
                    
                    for agent in agents_data.get("agents", []):
                        status = "🟢" if agent.get("is_healthy") else "🔴"
                        print(f"   {status} {agent.get('agent_id')}: {len(agent.get('capabilities', []))} capabilities")
                    
                    return {"success": True, "duration_ms": duration_ms, "agent_count": agent_count}
                else:
                    print(f"❌ Agents discovery failed: {response.status_code}")
                    return {"success": False, "status_code": response.status_code}
                    
            except Exception as e:
                print(f"❌ Agents discovery error: {e}")
                return {"success": False, "error": str(e)}
    
    async def test_capabilities_endpoint(self) -> Dict[str, Any]:
        """Test capabilities discovery endpoint"""
        print("🔍 Testing capabilities discovery...")
        
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            
            try:
                response = await client.get(f"{self.gateway_url}/capabilities")
                duration_ms = int((time.time() - start_time) * 1000)
                
                if response.status_code == 200:
                    capabilities_data = response.json()
                    capability_count = len(capabilities_data.get("capabilities", []))
                    print(f"✅ Capabilities discovery passed ({duration_ms}ms)")
                    print(f"   Found {capability_count} capabilities")
                    
                    # Group by agent
                    by_agent = {}
                    for cap in capabilities_data.get("capabilities", []):
                        agent_id = cap.get("agent_id")
                        if agent_id not in by_agent:
                            by_agent[agent_id] = []
                        by_agent[agent_id].append(cap.get("verb"))
                    
                    for agent_id, capabilities in by_agent.items():
                        print(f"   📋 {agent_id}: {', '.join(capabilities)}")
                    
                    return {"success": True, "duration_ms": duration_ms, "capability_count": capability_count}
                else:
                    print(f"❌ Capabilities discovery failed: {response.status_code}")
                    return {"success": False, "status_code": response.status_code}
                    
            except Exception as e:
                print(f"❌ Capabilities discovery error: {e}")
                return {"success": False, "error": str(e)}
    
    async def test_intent_classification(self) -> Dict[str, Any]:
        """Test intent classification and routing"""
        print("🔍 Testing intent classification...")
        
        test_queries = [
            "search mail for meeting",
            "find contact john",
            "when is my next meeting",
            "show recent messages", 
            "remember that I like coffee",
            "schedule a meeting with Sarah and propose a time"
        ]
        
        results = []
        
        async with httpx.AsyncClient() as client:
            for query in test_queries:
                print(f"   Testing: '{query}'")
                start_time = time.time()
                
                try:
                    response = await client.post(
                        f"{self.gateway_url}/query",
                        json={"query": query, "context": {}},
                        timeout=10.0
                    )
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    if response.status_code == 200:
                        result = response.json()
                        intent = result.get("intent", "unknown")
                        routing = result.get("routing", "unknown")
                        agent_id = result.get("agent_id", "N/A")
                        
                        print(f"     ✅ Intent: {intent}, Route: {routing}, Agent: {agent_id} ({duration_ms}ms)")
                        results.append({
                            "query": query,
                            "success": True,
                            "intent": intent,
                            "routing": routing,
                            "agent_id": agent_id,
                            "duration_ms": duration_ms
                        })
                    else:
                        print(f"     ❌ Failed: {response.status_code}")
                        results.append({
                            "query": query,
                            "success": False,
                            "status_code": response.status_code
                        })
                        
                except Exception as e:
                    print(f"     ❌ Error: {e}")
                    results.append({
                        "query": query,
                        "success": False,
                        "error": str(e)
                    })
        
        successful_tests = sum(1 for r in results if r.get("success"))
        avg_duration = sum(r.get("duration_ms", 0) for r in results if r.get("success")) / max(successful_tests, 1)
        
        print(f"   📊 {successful_tests}/{len(test_queries)} tests passed")
        print(f"   📊 Average response time: {avg_duration:.1f}ms")
        
        return {
            "success": successful_tests == len(test_queries),
            "passed": successful_tests,
            "total": len(test_queries),
            "avg_duration_ms": avg_duration,
            "results": results
        }
    
    async def test_performance(self) -> Dict[str, Any]:
        """Test gateway performance under load"""
        print("🔍 Testing gateway performance...")
        
        # Simple concurrent health checks
        concurrent_requests = 10
        
        async def make_request():
            async with httpx.AsyncClient() as client:
                start_time = time.time()
                response = await client.get(f"{self.gateway_url}/health")
                duration_ms = int((time.time() - start_time) * 1000)
                return {"success": response.status_code == 200, "duration_ms": duration_ms}
        
        print(f"   Making {concurrent_requests} concurrent health checks...")
        start_time = time.time()
        
        results = await asyncio.gather(*[make_request() for _ in range(concurrent_requests)])
        
        total_duration = int((time.time() - start_time) * 1000)
        successful_requests = sum(1 for r in results if r.get("success"))
        durations = [r.get("duration_ms", 0) for r in results if r.get("success")]
        
        if durations:
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            min_duration = min(durations)
        else:
            avg_duration = max_duration = min_duration = 0
        
        print(f"   ✅ {successful_requests}/{concurrent_requests} requests successful")
        print(f"   📊 Total time: {total_duration}ms")
        print(f"   📊 Avg request time: {avg_duration:.1f}ms")
        print(f"   📊 Min/Max: {min_duration}ms / {max_duration}ms")
        
        performance_good = avg_duration < 200  # <200ms target
        
        return {
            "success": performance_good and successful_requests == concurrent_requests,
            "total_duration_ms": total_duration,
            "avg_request_duration_ms": avg_duration,
            "min_duration_ms": min_duration,
            "max_duration_ms": max_duration,
            "successful_requests": successful_requests,
            "total_requests": concurrent_requests
        }
    
    async def run_all_tests(self):
        """Run all gateway tests"""
        print("🚀 Starting Kenny v2 Gateway Tests\n")
        
        test_results = {}
        
        # Test 1: Health Check
        test_results["health"] = await self.test_health()
        print()
        
        # Test 2: Agents Discovery
        test_results["agents"] = await self.test_agents_endpoint()
        print()
        
        # Test 3: Capabilities Discovery  
        test_results["capabilities"] = await self.test_capabilities_endpoint()
        print()
        
        # Test 4: Intent Classification
        test_results["intent_classification"] = await self.test_intent_classification()
        print()
        
        # Test 5: Performance
        test_results["performance"] = await self.test_performance()
        print()
        
        # Summary
        passed_tests = sum(1 for test_name, result in test_results.items() if result.get("success"))
        total_tests = len(test_results)
        
        print("📋 Test Summary:")
        print(f"   ✅ {passed_tests}/{total_tests} test suites passed")
        
        for test_name, result in test_results.items():
            status = "✅" if result.get("success") else "❌"
            print(f"   {status} {test_name}")
        
        if passed_tests == total_tests:
            print("\n🎉 All tests passed! Gateway is ready for Phase 2.")
        else:
            print(f"\n⚠️  {total_tests - passed_tests} test suite(s) failed. Review logs above.")
        
        return test_results

async def main():
    """Main test runner"""
    tester = GatewayTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())