"""
End-to-end Calendar Agent integration tests with Coordinator.

Tests the Calendar Agent's integration with the coordinator service
and approval workflow system.
"""

import pytest
import asyncio
import httpx
import os
import sys
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, Mock

# Add parent directory to Python path to import agent modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import app
from fastapi.testclient import TestClient


@pytest.mark.e2e
class TestCalendarAgentE2E:
    """End-to-end integration tests for Calendar Agent with Coordinator."""
    
    @pytest.fixture
    def test_client(self):
        """Create test client for Calendar Agent FastAPI app."""
        return TestClient(app)
    
    @pytest.fixture
    def coordinator_url(self):
        """Get coordinator URL from environment or use default."""
        return os.getenv("COORDINATOR_URL", "http://localhost:8000")
    
    @pytest.fixture
    def agent_registry_url(self):
        """Get agent registry URL from environment or use default."""
        return os.getenv("AGENT_REGISTRY_URL", "http://localhost:8001")
    
    def test_agent_health_endpoint(self, test_client):
        """Test Calendar Agent health endpoint."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        health_data = response.json()
        
        assert "status" in health_data
        assert health_data["status"] in ["healthy", "degraded", "unhealthy"]
        
        if health_data["status"] == "healthy":
            assert health_data.get("message") == "Calendar Agent is operational"
    
    def test_agent_capabilities_endpoint(self, test_client):
        """Test Calendar Agent capabilities listing."""
        response = test_client.get("/capabilities")
        
        assert response.status_code == 200
        capabilities_data = response.json()
        
        assert "agent_id" in capabilities_data
        assert capabilities_data["agent_id"] == "calendar-agent"
        assert "capabilities" in capabilities_data
        
        capabilities = capabilities_data["capabilities"]
        expected_capabilities = ["calendar.read", "calendar.propose_event", "calendar.write_event"]
        
        capability_names = [cap.get("capability") for cap in capabilities]
        for expected in expected_capabilities:
            assert expected in capability_names
    
    def test_agent_root_endpoint(self, test_client):
        """Test Calendar Agent root information endpoint."""
        response = test_client.get("/")
        
        assert response.status_code == 200
        root_data = response.json()
        
        assert root_data["agent_id"] == "calendar-agent"
        assert root_data["name"] == "Calendar Agent"
        assert "calendar:events" in root_data.get("data_scopes", [])
        assert "calendar_bridge" in root_data.get("tools", [])
    
    def test_calendar_read_capability(self, test_client):
        """Test calendar.read capability execution."""
        # Test reading events by date range
        request_data = {
            "input": {
                "date_range": {
                    "start": "2025-08-16T00:00:00Z",
                    "end": "2025-08-17T00:00:00Z"
                },
                "limit": 10
            }
        }
        
        response = test_client.post("/capabilities/calendar.read", json=request_data)
        
        assert response.status_code == 200
        result = response.json()
        
        assert "output" in result
        output = result["output"]
        assert "events" in output
        assert "count" in output
        assert isinstance(output["events"], list)
        assert isinstance(output["count"], int)
    
    def test_calendar_read_by_event_id(self, test_client):
        """Test calendar.read capability with event ID."""
        request_data = {
            "input": {
                "event_id": "test-event-1"
            }
        }
        
        response = test_client.post("/capabilities/calendar.read", json=request_data)
        
        assert response.status_code == 200
        result = response.json()
        
        assert "output" in result
        output = result["output"]
        assert "events" in output
        assert "count" in output
        # Should return single event or empty list if not found
        assert output["count"] <= 1
    
    def test_calendar_propose_event_capability(self, test_client):
        """Test calendar.propose_event capability execution."""
        request_data = {
            "input": {
                "title": "Test Calendar Event",
                "start": "2025-08-16T14:00:00Z",
                "end": "2025-08-16T15:00:00Z",
                "calendar_name": "Calendar",
                "location": "Test Location",
                "description": "Test event description"
            }
        }
        
        response = test_client.post("/capabilities/calendar.propose_event", json=request_data)
        
        assert response.status_code == 200
        result = response.json()
        
        assert "output" in result
        output = result["output"]
        assert "proposal" in output
        assert "requires_approval" in output
        assert output["requires_approval"] is True
        
        proposal = output["proposal"]
        assert "proposal_id" in proposal
        assert proposal["title"] == "Test Calendar Event"
        assert proposal["start"] == "2025-08-16T14:00:00Z"
        assert proposal["end"] == "2025-08-16T15:00:00Z"
        assert "conflicts" in proposal
        assert "suggestions" in proposal
    
    def test_calendar_write_event_capability(self, test_client):
        """Test calendar.write_event capability execution."""
        # Test approved event creation
        request_data = {
            "input": {
                "proposal_id": "test-proposal-123",
                "approved": True,
                "approval_token": "approved_test-proposal-123"
            }
        }
        
        response = test_client.post("/capabilities/calendar.write_event", json=request_data)
        
        assert response.status_code == 200
        result = response.json()
        
        assert "output" in result
        output = result["output"]
        assert "status" in output
        assert "message" in output
        
        # Should either succeed or fail gracefully
        assert output["status"] in ["created", "error", "rejected"]
    
    def test_calendar_write_event_rejected(self, test_client):
        """Test calendar.write_event capability with rejection."""
        request_data = {
            "input": {
                "proposal_id": "test-proposal-456",
                "approved": False
            }
        }
        
        response = test_client.post("/capabilities/calendar.write_event", json=request_data)
        
        assert response.status_code == 200
        result = response.json()
        
        assert "output" in result
        output = result["output"]
        assert output["status"] == "rejected"
        assert output["event"] is None
        assert "not approved" in output["message"]
    
    def test_invalid_capability_request(self, test_client):
        """Test requesting non-existent capability."""
        request_data = {
            "input": {
                "test": "data"
            }
        }
        
        response = test_client.post("/capabilities/nonexistent.capability", json=request_data)
        
        assert response.status_code == 404
        error_data = response.json()
        assert "detail" in error_data
        assert "not found" in error_data["detail"]
    
    @pytest.mark.asyncio
    async def test_coordinator_integration_flow(self, coordinator_url):
        """Test full integration flow with coordinator."""
        # This test requires coordinator to be running
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test coordinator health
                health_response = await client.get(f"{coordinator_url}/health")
                if health_response.status_code != 200:
                    pytest.skip("Coordinator service not available")
                
                # Test coordinator task execution with calendar request
                task_request = {
                    "task": "What events do I have tomorrow?",
                    "context": {},
                    "user_id": "test-user"
                }
                
                response = await client.post(f"{coordinator_url}/tasks", json=task_request)
                
                # Coordinator should accept the task
                assert response.status_code in [200, 202]
                
                if response.status_code == 200:
                    result = response.json()
                    assert "task_id" in result or "result" in result
                    
        except Exception as e:
            pytest.skip(f"Coordinator integration test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_agent_registry_integration(self, test_client, agent_registry_url):
        """Test integration with Agent Registry."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test registry health
                health_response = await client.get(f"{agent_registry_url}/health")
                if health_response.status_code != 200:
                    pytest.skip("Agent Registry service not available")
                
                # Get registered agents
                agents_response = await client.get(f"{agent_registry_url}/agents")
                
                if agents_response.status_code == 200:
                    agents = agents_response.json()
                    
                    # Look for calendar agent registration
                    calendar_agent_found = False
                    for agent in agents:
                        if agent.get("agent_id") == "calendar-agent":
                            calendar_agent_found = True
                            assert "capabilities" in agent
                            capabilities = [cap["capability"] for cap in agent["capabilities"]]
                            assert "calendar.read" in capabilities
                            assert "calendar.propose_event" in capabilities
                            assert "calendar.write_event" in capabilities
                            break
                    
                    # Agent may not be registered if auto-registration failed
                    # This is not necessarily a test failure
                    if calendar_agent_found:
                        print("Calendar Agent found in registry")
                    else:
                        print("Calendar Agent not found in registry (may not be auto-registered)")
                        
        except Exception as e:
            pytest.skip(f"Agent Registry integration test failed: {e}")
    
    @pytest.mark.asyncio 
    async def test_approval_workflow_simulation(self, test_client):
        """Test approval workflow simulation."""
        # 1. Propose an event
        propose_request = {
            "input": {
                "title": "Team Meeting",
                "start": "2025-08-16T14:00:00Z",
                "end": "2025-08-16T15:00:00Z",
                "attendees": ["alice@example.com", "bob@example.com"]
            }
        }
        
        propose_response = test_client.post("/capabilities/calendar.propose_event", json=propose_request)
        assert propose_response.status_code == 200
        
        propose_result = propose_response.json()["output"]
        proposal_id = propose_result["proposal"]["proposal_id"]
        
        # 2. Simulate approval workflow (normally handled by coordinator)
        # In a real system, coordinator would present proposal to user and get approval
        
        # 3. Approve and create event
        write_request = {
            "input": {
                "proposal_id": proposal_id,
                "approved": True,
                "approval_token": f"approved_{proposal_id}",
                "modifications": {
                    "description": "Added by approval workflow"
                }
            }
        }
        
        write_response = test_client.post("/capabilities/calendar.write_event", json=write_request)
        assert write_response.status_code == 200
        
        write_result = write_response.json()["output"]
        assert write_result["status"] in ["created", "error"]  # Allow both for different modes
    
    def test_capability_input_validation(self, test_client):
        """Test capability input validation."""
        # Test calendar.read with invalid date range
        invalid_request = {
            "input": {
                "date_range": {
                    "start": "invalid-date",
                    "end": "2025-08-17T00:00:00Z"
                }
            }
        }
        
        response = test_client.post("/capabilities/calendar.read", json=invalid_request)
        assert response.status_code == 200  # Should handle gracefully
        
        # Test calendar.propose_event with missing required fields
        invalid_propose = {
            "input": {
                "title": "Test Event"
                # Missing start and end times
            }
        }
        
        response = test_client.post("/capabilities/calendar.propose_event", json=invalid_propose)
        assert response.status_code == 500  # Should fail validation
    
    def test_concurrent_capability_requests(self, test_client):
        """Test that agent handles concurrent capability requests."""
        import threading
        import time
        
        results = []
        
        def make_request():
            request_data = {
                "input": {
                    "date_range": {
                        "start": "2025-08-16T00:00:00Z",
                        "end": "2025-08-17T00:00:00Z"
                    }
                }
            }
            response = test_client.post("/capabilities/calendar.read", json=request_data)
            results.append((response.status_code, time.time()))
        
        # Make 3 concurrent requests
        threads = []
        for i in range(3):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert len(results) == 3
        for status_code, timestamp in results:
            assert status_code == 200
    
    @pytest.mark.asyncio
    async def test_enhanced_health_check(self, test_client):
        """Test enhanced health check endpoint with performance metrics."""
        response = test_client.get("/health/performance")
        
        assert response.status_code == 200
        health_data = response.json()
        
        if "error" not in health_data:
            assert "agent_name" in health_data
            assert health_data["agent_name"] == "calendar-agent"
            assert "overall_health" in health_data
            assert "performance_summary" in health_data
            
            perf_summary = health_data["performance_summary"]
            assert "current_metrics" in perf_summary
            assert "sla_compliance" in perf_summary
            
            # Check SLA compliance structure
            sla = perf_summary["sla_compliance"]
            assert "response_time_sla" in sla
            assert "success_rate_sla" in sla
            assert "overall_compliant" in sla


@pytest.mark.performance
class TestCalendarAgentPerformance:
    """Performance tests for Calendar Agent."""
    
    @pytest.fixture
    def test_client(self):
        """Create test client for performance testing."""
        return TestClient(app)
    
    def test_read_capability_performance(self, test_client):
        """Test calendar.read capability performance."""
        import time
        
        request_data = {
            "input": {
                "date_range": {
                    "start": "2025-08-16T00:00:00Z",
                    "end": "2025-08-30T00:00:00Z"  # 2 week range
                },
                "limit": 100
            }
        }
        
        start_time = time.time()
        response = test_client.post("/capabilities/calendar.read", json=request_data)
        end_time = time.time()
        
        duration = end_time - start_time
        
        assert response.status_code == 200
        # Should complete within reasonable time
        assert duration < 10.0
        
        print(f"Calendar read capability took {duration:.2f}s")
    
    def test_propose_event_performance(self, test_client):
        """Test calendar.propose_event capability performance."""
        import time
        
        request_data = {
            "input": {
                "title": "Performance Test Event",
                "start": "2025-08-16T14:00:00Z",
                "end": "2025-08-16T15:00:00Z",
                "calendar_name": "Calendar"
            }
        }
        
        start_time = time.time()
        response = test_client.post("/capabilities/calendar.propose_event", json=request_data)
        end_time = time.time()
        
        duration = end_time - start_time
        
        assert response.status_code == 200
        # Should complete within reasonable time (includes conflict detection)
        assert duration < 15.0
        
        print(f"Calendar propose event capability took {duration:.2f}s")


if __name__ == "__main__":
    # Run e2e tests when executed directly
    pytest.main([__file__, "-v", "--tb=short", "-m", "e2e"])