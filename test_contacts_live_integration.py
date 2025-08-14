#!/usr/bin/env python3
"""
Integration test script for live contacts data.

This script tests the complete flow:
1. Bridge contacts endpoints with live macOS data
2. Contacts Agent using bridge for real contact resolution
3. Performance and caching validation
4. End-to-end workflow testing

Usage:
    # Start bridge in live mode first:
    CONTACTS_BRIDGE_MODE=live python3 bridge/app.py
    
    # Start contacts agent:
    python3 -m uvicorn services/contacts-agent/src.main:app --port 8003
    
    # Run this test:
    python3 test_contacts_live_integration.py
"""

import asyncio
import httpx
import json
import time
from typing import List, Dict, Any


class ContactsIntegrationTester:
    """Test suite for live contacts integration."""
    
    def __init__(self):
        self.bridge_url = "http://localhost:5100"
        self.agent_url = "http://localhost:8003"
        self.test_results = []
    
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": time.time()
        })
    
    async def test_bridge_health(self) -> bool:
        """Test bridge health endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.bridge_url}/health", timeout=10)
                success = response.status_code == 200
                self.log_test("Bridge Health Check", success, f"Status: {response.status_code}")
                return success
        except Exception as e:
            self.log_test("Bridge Health Check", False, f"Error: {e}")
            return False
    
    async def test_bridge_contacts_demo(self) -> bool:
        """Test bridge contacts endpoint in demo mode."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.bridge_url}/v1/contacts",
                    params={"limit": 5},
                    timeout=10
                )
                
                if response.status_code != 200:
                    self.log_test("Bridge Demo Contacts", False, f"HTTP {response.status_code}")
                    return False
                
                contacts = response.json()
                success = isinstance(contacts, list) and len(contacts) > 0
                details = f"Got {len(contacts)} demo contacts"
                self.log_test("Bridge Demo Contacts", success, details)
                return success
                
        except Exception as e:
            self.log_test("Bridge Demo Contacts", False, f"Error: {e}")
            return False
    
    async def test_bridge_contacts_live(self) -> bool:
        """Test bridge contacts endpoint in live mode (requires CONTACTS_BRIDGE_MODE=live)."""
        try:
            start_time = time.time()
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.bridge_url}/v1/contacts",
                    params={"limit": 10},
                    timeout=70  # JXA can be slow
                )
                
                if response.status_code != 200:
                    self.log_test("Bridge Live Contacts", False, f"HTTP {response.status_code}")
                    return False
                
                contacts = response.json()
                duration = time.time() - start_time
                
                # Check if we got live data (should have different structure than demo)
                has_live_data = any(
                    contact.get("source") == "macos_contacts" 
                    for contact in contacts
                )
                
                success = isinstance(contacts, list) and len(contacts) > 0
                details = f"Got {len(contacts)} contacts in {duration:.1f}s, live_data={has_live_data}"
                self.log_test("Bridge Live Contacts", success, details)
                return success
                
        except Exception as e:
            self.log_test("Bridge Live Contacts", False, f"Error: {e}")
            return False
    
    async def test_bridge_contacts_search(self) -> bool:
        """Test bridge contacts search functionality."""
        try:
            # Test with a common name that should exist
            test_queries = ["John", "Smith", "@", ".com"]
            
            for query in test_queries:
                start_time = time.time()
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.bridge_url}/v1/contacts",
                        params={"query": query, "limit": 5},
                        timeout=70
                    )
                    
                    duration = time.time() - start_time
                    
                    if response.status_code != 200:
                        self.log_test(f"Bridge Search '{query}'", False, f"HTTP {response.status_code}")
                        continue
                    
                    contacts = response.json()
                    success = isinstance(contacts, list)
                    details = f"Query '{query}': {len(contacts)} results in {duration:.1f}s"
                    self.log_test(f"Bridge Search '{query}'", success, details)
                    
                    if not success:
                        return False
            
            return True
                
        except Exception as e:
            self.log_test("Bridge Contacts Search", False, f"Error: {e}")
            return False
    
    async def test_agent_health(self) -> bool:
        """Test contacts agent health endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.agent_url}/health", timeout=10)
                success = response.status_code == 200
                details = f"Status: {response.status_code}"
                if success:
                    health_data = response.json()
                    details += f", Status: {health_data.get('status', 'unknown')}"
                self.log_test("Agent Health Check", success, details)
                return success
        except Exception as e:
            self.log_test("Agent Health Check", False, f"Error: {e}")
            return False
    
    async def test_agent_resolve_capability(self) -> bool:
        """Test agent resolve capability with live data."""
        try:
            test_cases = [
                {"identifier": "John", "description": "Name search"},
                {"identifier": "smith", "description": "Partial name search"},
                {"identifier": "@gmail.com", "description": "Email domain search"},
                {"identifier": "+1", "description": "Phone search"}
            ]
            
            for test_case in test_cases:
                start_time = time.time()
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.agent_url}/capabilities/contacts.resolve",
                        json={"input": {"identifier": test_case["identifier"]}},
                        timeout=70
                    )
                    
                    duration = time.time() - start_time
                    
                    if response.status_code != 200:
                        self.log_test(f"Agent Resolve {test_case['description']}", False, f"HTTP {response.status_code}")
                        continue
                    
                    result = response.json()
                    contacts = result.get("output", {}).get("contacts", [])
                    count = result.get("output", {}).get("resolved_count", 0)
                    
                    success = isinstance(contacts, list) and count >= 0
                    details = f"{test_case['description']}: {count} contacts in {duration:.1f}s"
                    self.log_test(f"Agent Resolve {test_case['description']}", success, details)
                    
                    if not success:
                        return False
            
            return True
                
        except Exception as e:
            self.log_test("Agent Resolve Capability", False, f"Error: {e}")
            return False
    
    async def test_caching_performance(self) -> bool:
        """Test that caching improves performance on repeated requests."""
        try:
            # Make initial request to populate cache
            start_time = time.time()
            async with httpx.AsyncClient() as client:
                response1 = await client.get(
                    f"{self.bridge_url}/v1/contacts",
                    params={"limit": 5},
                    timeout=70
                )
                first_duration = time.time() - start_time
            
            if response1.status_code != 200:
                self.log_test("Cache Performance Test", False, "First request failed")
                return False
            
            # Wait a moment then make second request (should be cached)
            await asyncio.sleep(1)
            
            start_time = time.time()
            async with httpx.AsyncClient() as client:
                response2 = await client.get(
                    f"{self.bridge_url}/v1/contacts",
                    params={"limit": 5},
                    timeout=10  # Should be much faster
                )
                second_duration = time.time() - start_time
            
            if response2.status_code != 200:
                self.log_test("Cache Performance Test", False, "Second request failed")
                return False
            
            # Check that second request was significantly faster
            performance_improvement = first_duration > second_duration * 2
            details = f"First: {first_duration:.1f}s, Second: {second_duration:.1f}s, Improved: {performance_improvement}"
            self.log_test("Cache Performance Test", performance_improvement, details)
            return performance_improvement
            
        except Exception as e:
            self.log_test("Cache Performance Test", False, f"Error: {e}")
            return False
    
    async def test_end_to_end_workflow(self) -> bool:
        """Test complete end-to-end workflow."""
        try:
            # 1. Search for contacts via agent
            async with httpx.AsyncClient() as client:
                search_response = await client.post(
                    f"{self.agent_url}/capabilities/contacts.resolve",
                    json={"input": {"identifier": "test"}},
                    timeout=70
                )
            
            if search_response.status_code != 200:
                self.log_test("E2E Workflow", False, "Contact search failed")
                return False
            
            # 2. Verify response structure
            result = search_response.json()
            output = result.get("output", {})
            contacts = output.get("contacts", [])
            count = output.get("resolved_count", 0)
            
            structure_valid = (
                isinstance(contacts, list) and 
                isinstance(count, int) and 
                count >= 0
            )
            
            if not structure_valid:
                self.log_test("E2E Workflow", False, "Invalid response structure")
                return False
            
            # 3. Check metadata
            metadata = result.get("metadata", {})
            has_metadata = (
                "capability" in metadata and 
                "agent_id" in metadata and 
                "timestamp" in metadata
            )
            
            details = f"Found {count} contacts, metadata_present={has_metadata}"
            self.log_test("E2E Workflow", has_metadata, details)
            return has_metadata
            
        except Exception as e:
            self.log_test("E2E Workflow", False, f"Error: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests and return summary."""
        print("🚀 Starting Contacts Live Integration Tests\n")
        
        # Basic connectivity tests
        await self.test_bridge_health()
        await self.test_agent_health()
        
        # Bridge functionality tests
        await self.test_bridge_contacts_demo()
        await self.test_bridge_contacts_live()
        await self.test_bridge_contacts_search()
        
        # Agent functionality tests  
        await self.test_agent_resolve_capability()
        
        # Performance tests
        await self.test_caching_performance()
        
        # End-to-end tests
        await self.test_end_to_end_workflow()
        
        # Calculate summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"\n📊 Test Summary:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {passed_tests/total_tests*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   - {result['test']}: {result['details']}")
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": passed_tests / total_tests,
            "details": self.test_results
        }


async def main():
    """Main test runner."""
    tester = ContactsIntegrationTester()
    summary = await tester.run_all_tests()
    
    # Return appropriate exit code
    exit_code = 0 if summary["failed_tests"] == 0 else 1
    
    if exit_code == 0:
        print("\n🎉 All tests passed! Live contacts integration is working correctly.")
    else:
        print(f"\n💥 {summary['failed_tests']} test(s) failed. Check the output above for details.")
    
    return exit_code


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)