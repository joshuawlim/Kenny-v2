#!/usr/bin/env python3
"""
Phase 5.2 Integration Tests: Coordinator Integration
Tests Gateway-Coordinator integration for multi-agent workflows
"""

import asyncio
import httpx
import time
import json
import websockets
from typing import Dict, Any, List

class Phase52IntegrationTester:
    def __init__(self):
        self.gateway_url = "http://localhost:9000"
        self.coordinator_url = "http://localhost:8002"
        
    async def test_coordinator_availability(self) -> Dict[str, Any]:
        """Test if coordinator service is available"""
        print("🔍 Testing coordinator availability...")
        
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            
            try:
                response = await client.get(f"{self.coordinator_url}/health")
                duration_ms = int((time.time() - start_time) * 1000)
                
                if response.status_code == 200:
                    health_data = response.json()
                    print(f"✅ Coordinator health check passed ({duration_ms}ms)")
                    print(f"   Service: {health_data.get('service', 'unknown')}")
                    print(f"   Version: {health_data.get('version', 'unknown')}")
                    return {"success": True, "duration_ms": duration_ms, "data": health_data}
                else:
                    print(f"❌ Coordinator health check failed: {response.status_code}")
                    return {"success": False, "status_code": response.status_code}
                    
            except Exception as e:
                print(f"❌ Coordinator health check error: {e}")
                return {"success": False, "error": str(e)}
    
    async def test_coordinator_routing(self) -> Dict[str, Any]:
        """Test Gateway routing to Coordinator for complex queries"""
        print("🔍 Testing coordinator routing...")
        
        # Test queries that should route to coordinator
        coordinator_queries = [
            "schedule a meeting with Sarah and send her a message",
            "find contact John and also search my emails",
            "check my calendar and then create an event",
            "search emails and remember the important details",
            "coordinate between multiple agents for workflow"
        ]
        
        results = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for query in coordinator_queries:
                print(f"   Testing: '{query}'")
                start_time = time.time()
                
                try:
                    response = await client.post(
                        f"{self.gateway_url}/query",
                        json={"query": query, "context": {}},
                        timeout=25.0
                    )
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    if response.status_code == 200:
                        result = response.json()
                        intent = result.get("intent", "unknown")
                        routing = result.get("routing", "unknown")
                        execution_path = result.get("execution_path", [])
                        
                        coordinator_routed = routing == "coordinator"
                        has_execution_path = len(execution_path) > 0
                        
                        print(f"     ✅ Intent: {intent}, Route: {routing}, Execution: {len(execution_path)} steps ({duration_ms}ms)")
                        
                        if coordinator_routed:
                            print(f"        📋 Execution path: {' → '.join(execution_path)}")
                        
                        results.append({
                            "query": query,
                            "success": True,
                            "coordinator_routed": coordinator_routed,
                            "intent": intent,
                            "routing": routing,
                            "execution_path": execution_path,
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
        coordinator_routed = sum(1 for r in results if r.get("coordinator_routed"))
        avg_duration = sum(r.get("duration_ms", 0) for r in results if r.get("success")) / max(successful_tests, 1)
        
        print(f"   📊 {successful_tests}/{len(coordinator_queries)} tests passed")
        print(f"   📊 {coordinator_routed}/{len(coordinator_queries)} queries routed to coordinator")
        print(f"   📊 Average response time: {avg_duration:.1f}ms")
        
        return {
            "success": successful_tests == len(coordinator_queries) and coordinator_routed >= len(coordinator_queries) * 0.8,
            "passed": successful_tests,
            "total": len(coordinator_queries),
            "coordinator_routed": coordinator_routed,
            "avg_duration_ms": avg_duration,
            "results": results
        }
    
    async def test_coordinator_streaming(self) -> Dict[str, Any]:
        """Test WebSocket streaming with coordinator workflows"""
        print("🔍 Testing coordinator streaming...")
        
        streaming_results = []
        
        try:
            # Test streaming query that should route to coordinator
            test_query = "find contact Sarah and schedule a meeting with her"
            
            # Connect to WebSocket
            uri = f"ws://localhost:9000/stream"
            
            async with websockets.connect(uri, timeout=30) as websocket:
                start_time = time.time()
                print(f"   Testing streaming: '{test_query}'")
                
                # Send query
                await websocket.send(json.dumps({
                    "query": test_query,
                    "context": {}
                }))
                
                messages_received = 0
                coordinator_messages = 0
                
                # Receive streaming responses
                while True:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                        data = json.loads(message)
                        messages_received += 1
                        
                        msg_type = data.get("type", "unknown")
                        print(f"     📨 Received: {msg_type}")
                        
                        # Count coordinator-specific messages
                        if msg_type in ["node_start", "node_complete", "agent_start", "agent_complete", "final_result"]:
                            coordinator_messages += 1
                        
                        streaming_results.append(data)
                        
                        # Break on completion
                        if msg_type in ["complete", "final_result", "error"]:
                            break
                            
                    except asyncio.TimeoutError:
                        print("     ⚠️ Streaming timeout")
                        break
                
                duration_ms = int((time.time() - start_time) * 1000)
                
                print(f"     ✅ Received {messages_received} messages ({coordinator_messages} coordinator-specific) in {duration_ms}ms")
                
                return {
                    "success": messages_received > 0 and coordinator_messages > 0,
                    "messages_received": messages_received,
                    "coordinator_messages": coordinator_messages,
                    "duration_ms": duration_ms,
                    "streaming_data": streaming_results
                }
                
        except Exception as e:
            print(f"     ❌ Streaming error: {e}")
            return {
                "success": False,
                "error": str(e),
                "streaming_data": streaming_results
            }
    
    async def test_performance_requirements(self) -> Dict[str, Any]:
        """Test performance requirements for coordinator integration"""
        print("🔍 Testing performance requirements...")
        
        # Test multiple coordinator queries concurrently
        concurrent_requests = 5
        test_query = "search emails and also find contacts"
        
        async def make_coordinator_request():
            async with httpx.AsyncClient(timeout=30.0) as client:
                start_time = time.time()
                response = await client.post(
                    f"{self.gateway_url}/query",
                    json={"query": test_query, "context": {}},
                    timeout=25.0
                )
                duration_ms = int((time.time() - start_time) * 1000)
                return {
                    "success": response.status_code == 200,
                    "duration_ms": duration_ms,
                    "coordinator_routed": response.json().get("routing") == "coordinator" if response.status_code == 200 else False
                }
        
        print(f"   Making {concurrent_requests} concurrent coordinator requests...")
        start_time = time.time()
        
        results = await asyncio.gather(*[make_coordinator_request() for _ in range(concurrent_requests)])
        
        total_duration = int((time.time() - start_time) * 1000)
        successful_requests = sum(1 for r in results if r.get("success"))
        coordinator_routed = sum(1 for r in results if r.get("coordinator_routed"))
        durations = [r.get("duration_ms", 0) for r in results if r.get("success")]
        
        if durations:
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            min_duration = min(durations)
        else:
            avg_duration = max_duration = min_duration = 0
        
        print(f"   ✅ {successful_requests}/{concurrent_requests} requests successful")
        print(f"   ✅ {coordinator_routed}/{concurrent_requests} routed to coordinator")
        print(f"   📊 Total time: {total_duration}ms")
        print(f"   📊 Avg request time: {avg_duration:.1f}ms")
        print(f"   📊 Min/Max: {min_duration}ms / {max_duration}ms")
        
        performance_good = avg_duration < 200  # <200ms target per requirements
        coordinator_routing_good = coordinator_routed >= concurrent_requests * 0.8
        
        return {
            "success": performance_good and successful_requests == concurrent_requests and coordinator_routing_good,
            "total_duration_ms": total_duration,
            "avg_request_duration_ms": avg_duration,
            "min_duration_ms": min_duration,
            "max_duration_ms": max_duration,
            "successful_requests": successful_requests,
            "coordinator_routed": coordinator_routed,
            "total_requests": concurrent_requests,
            "performance_target_met": performance_good
        }
    
    async def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling and fallback mechanisms"""
        print("🔍 Testing error handling...")
        
        error_tests = []
        
        # Test 1: Invalid query format
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.gateway_url}/query",
                    json={"invalid": "format"},
                    timeout=10.0
                )
                error_tests.append({
                    "test": "invalid_query_format",
                    "success": response.status_code == 422 or response.status_code == 400,
                    "status_code": response.status_code
                })
            except Exception as e:
                error_tests.append({
                    "test": "invalid_query_format",
                    "success": False,
                    "error": str(e)
                })
        
        # Test 2: Empty query
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.gateway_url}/query",
                    json={"query": "", "context": {}},
                    timeout=10.0
                )
                # Should either succeed with empty handling or return appropriate error
                error_tests.append({
                    "test": "empty_query",
                    "success": True,  # Any response is acceptable for empty query
                    "status_code": response.status_code
                })
            except Exception as e:
                error_tests.append({
                    "test": "empty_query",
                    "success": False,
                    "error": str(e)
                })
        
        successful_error_tests = sum(1 for test in error_tests if test.get("success"))
        
        for test in error_tests:
            status = "✅" if test.get("success") else "❌"
            print(f"   {status} {test['test']}: {test.get('status_code', 'error')}")
        
        return {
            "success": successful_error_tests == len(error_tests),
            "passed": successful_error_tests,
            "total": len(error_tests),
            "tests": error_tests
        }
    
    async def run_all_tests(self):
        """Run all Phase 5.2 integration tests"""
        print("🚀 Starting Phase 5.2 Coordinator Integration Tests\n")
        
        test_results = {}
        
        # Test 1: Coordinator Availability
        test_results["coordinator_availability"] = await self.test_coordinator_availability()
        print()
        
        # Test 2: Coordinator Routing
        test_results["coordinator_routing"] = await self.test_coordinator_routing()
        print()
        
        # Test 3: Coordinator Streaming
        test_results["coordinator_streaming"] = await self.test_coordinator_streaming()
        print()
        
        # Test 4: Performance Requirements
        test_results["performance"] = await self.test_performance_requirements()
        print()
        
        # Test 5: Error Handling
        test_results["error_handling"] = await self.test_error_handling()
        print()
        
        # Summary
        passed_tests = sum(1 for test_name, result in test_results.items() if result.get("success"))
        total_tests = len(test_results)
        
        print("📋 Phase 5.2 Test Summary:")
        print(f"   ✅ {passed_tests}/{total_tests} test suites passed")
        
        for test_name, result in test_results.items():
            status = "✅" if result.get("success") else "❌"
            print(f"   {status} {test_name}")
        
        if passed_tests == total_tests:
            print("\n🎉 All Phase 5.2 tests passed! Coordinator integration is ready.")
            print("✨ Multi-agent workflows operational through unified Gateway interface")
        else:
            print(f"\n⚠️  {total_tests - passed_tests} test suite(s) failed. Review logs above.")
        
        return test_results

async def main():
    """Main test runner"""
    tester = Phase52IntegrationTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())