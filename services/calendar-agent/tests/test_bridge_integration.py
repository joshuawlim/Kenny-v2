"""
Bridge integration tests for Calendar Agent.

Tests the Calendar Agent's integration with the macOS Bridge service.
"""

import pytest
import asyncio
import httpx
import os
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

# Add parent directory to Python path to import agent modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tools.calendar_bridge import CalendarBridgeTool


@pytest.mark.integration 
class TestCalendarBridgeIntegration:
    """Test Calendar Bridge Tool integration with live bridge service."""
    
    @pytest.fixture
    def bridge_url(self):
        """Get bridge URL from environment or use default."""
        return os.getenv("MAC_BRIDGE_URL", "http://localhost:5100")
    
    @pytest.fixture
    def bridge_tool(self, bridge_url):
        """Create Calendar Bridge Tool with configured URL."""
        return CalendarBridgeTool(bridge_url)
    
    @pytest.fixture
    async def bridge_health_check(self, bridge_url):
        """Check if bridge service is available before running tests."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{bridge_url}/health")
                if response.status_code == 200:
                    return True
        except Exception as e:
            pytest.skip(f"Bridge service not available: {e}")
        return False
    
    @pytest.mark.asyncio
    async def test_bridge_health_check(self, bridge_tool, bridge_health_check):
        """Test bridge health check connectivity."""
        result = bridge_tool.execute({"operation": "health"})
        
        assert "operation" in result
        assert result["operation"] == "health"
        assert "status" in result
        # Status should be "ok" if bridge is healthy, "error" if there are issues
        assert result["status"] in ["ok", "error"]
    
    @pytest.mark.asyncio
    async def test_list_calendars_live(self, bridge_tool, bridge_health_check):
        """Test listing calendars from live bridge."""
        result = bridge_tool.execute({"operation": "list_calendars"})
        
        assert result["operation"] == "list_calendars"
        assert "calendars" in result
        assert isinstance(result["calendars"], list)
        assert "count" in result
        
        # If live mode and Calendar.app is accessible, should have calendars
        if not result.get("error"):
            assert result["count"] >= 0  # Could be 0 if no calendars
            if result["count"] > 0:
                calendar = result["calendars"][0]
                assert "id" in calendar
                assert "name" in calendar
                assert "writable" in calendar
    
    @pytest.mark.asyncio
    async def test_list_events_live(self, bridge_tool, bridge_health_check):
        """Test listing events from live bridge."""
        # Get events from the next week to avoid too much data
        start_date = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        end_date = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat().replace("+00:00", "Z")
        
        result = bridge_tool.execute({
            "operation": "list_events",
            "start_date": start_date,
            "end_date": end_date,
            "limit": 10
        })
        
        assert result["operation"] == "list_events"
        assert "events" in result
        assert isinstance(result["events"], list)
        assert "count" in result
        
        # Validate event structure if any events exist
        if result["count"] > 0 and not result.get("error"):
            event = result["events"][0]
            assert "id" in event
            assert "title" in event
            assert "start" in event
            assert "end" in event
            assert "calendar" in event
    
    @pytest.mark.asyncio
    async def test_list_events_with_calendar_filter(self, bridge_tool, bridge_health_check):
        """Test listing events with calendar name filter."""
        # First get available calendars
        calendars_result = bridge_tool.execute({"operation": "list_calendars"})
        
        if calendars_result.get("count", 0) > 0 and not calendars_result.get("error"):
            calendar_name = calendars_result["calendars"][0]["name"]
            
            # Get events from specific calendar
            start_date = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            end_date = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat().replace("+00:00", "Z")
            
            result = bridge_tool.execute({
                "operation": "list_events",
                "calendar_name": calendar_name,
                "start_date": start_date,
                "end_date": end_date,
                "limit": 5
            })
            
            assert result["operation"] == "list_events"
            assert "events" in result
            if result["count"] > 0 and not result.get("error"):
                # All events should be from the specified calendar
                for event in result["events"]:
                    assert event["calendar"] == calendar_name
    
    @pytest.mark.asyncio
    async def test_get_specific_event(self, bridge_tool, bridge_health_check):
        """Test getting a specific event by ID."""
        # First list events to get a valid event ID
        start_date = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat().replace("+00:00", "Z")
        end_date = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat().replace("+00:00", "Z")
        
        list_result = bridge_tool.execute({
            "operation": "list_events",
            "start_date": start_date,
            "end_date": end_date,
            "limit": 1
        })
        
        if list_result.get("count", 0) > 0 and not list_result.get("error"):
            event_id = list_result["events"][0]["id"]
            
            # Get the specific event
            result = bridge_tool.execute({
                "operation": "get_event",
                "event_id": event_id
            })
            
            assert result["operation"] == "get_event"
            assert result["event_id"] == event_id
            
            if not result.get("error"):
                assert "event" in result
                event = result["event"]
                assert event["id"] == event_id
                assert "title" in event
                assert "start" in event
                assert "end" in event
    
    @pytest.mark.asyncio
    async def test_create_event_demo_mode(self, bridge_tool, bridge_health_check):
        """Test event creation in demo mode (safe for testing)."""
        # Create test event data
        start_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
        end_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat().replace("+00:00", "Z")
        
        event_data = {
            "title": "Test Calendar Integration Event",
            "start": start_time,
            "end": end_time,
            "all_day": False,
            "calendar": "Calendar",
            "location": "Test Location",
            "description": "This is a test event created by integration tests"
        }
        
        result = bridge_tool.execute({
            "operation": "create_event",
            "event_data": event_data
        })
        
        assert result["operation"] == "create_event"
        
        # In demo mode, should always succeed
        # In live mode, success depends on Calendar.app permissions
        if result.get("created"):
            assert "event" in result
            assert result["event"]["title"] == event_data["title"]
            assert result["event"]["start"] == event_data["start"]
            assert result["event"]["end"] == event_data["end"]
        else:
            # If creation failed, should have error message
            assert "error" in result
    
    @pytest.mark.asyncio
    async def test_bridge_error_handling(self, bridge_tool):
        """Test bridge error handling with invalid requests."""
        # Test unknown operation
        result = bridge_tool.execute({"operation": "unknown_operation"})
        assert "error" in result or result.get("operation") == "unknown_operation"
        
        # Test get_event without event_id
        with pytest.raises(ValueError, match="event_id is required"):
            bridge_tool.execute({"operation": "get_event"})
        
        # Test create_event without event_data
        with pytest.raises(ValueError, match="event_data is required"):
            bridge_tool.execute({"operation": "create_event"})
    
    @pytest.mark.asyncio
    async def test_bridge_timeout_handling(self, bridge_tool):
        """Test that bridge operations handle timeouts gracefully."""
        # This test uses the real bridge tool timeout configuration
        # If bridge is slow or unresponsive, should handle gracefully
        
        result = bridge_tool.execute({"operation": "health"})
        
        # Should return a result within reasonable time
        assert "operation" in result
        assert result["operation"] == "health"
        
        # Status should indicate success or failure, not timeout
        assert "status" in result
    
    @pytest.mark.parametrize("bridge_mode", ["demo", "live"])
    @pytest.mark.asyncio
    async def test_bridge_mode_compatibility(self, bridge_tool, bridge_mode):
        """Test bridge compatibility in different modes."""
        # This test verifies the bridge works in both demo and live modes
        # In practice, mode is controlled by environment variables on bridge side
        
        result = bridge_tool.execute({"operation": "list_calendars"})
        
        assert result["operation"] == "list_calendars"
        assert "calendars" in result
        assert isinstance(result["calendars"], list)
        
        # Demo mode should always return data
        # Live mode depends on Calendar.app availability
        if bridge_mode == "demo":
            assert result["count"] >= 0
        else:  # live mode
            # Either succeeds or fails gracefully
            assert "count" in result or "error" in result
    
    @pytest.mark.asyncio
    async def test_concurrent_bridge_requests(self, bridge_tool, bridge_health_check):
        """Test that bridge handles concurrent requests properly."""
        # Make multiple concurrent requests
        tasks = []
        for i in range(3):
            task = asyncio.create_task(
                asyncio.to_thread(
                    bridge_tool.execute,
                    {"operation": "list_calendars"}
                )
            )
            tasks.append(task)
        
        # Wait for all requests to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All requests should complete successfully
        assert len(results) == 3
        for result in results:
            assert not isinstance(result, Exception)
            assert result["operation"] == "list_calendars"
            assert "calendars" in result


@pytest.mark.performance
class TestCalendarBridgePerformance:
    """Performance tests for Calendar Bridge integration."""
    
    @pytest.fixture
    def bridge_tool(self):
        """Create Calendar Bridge Tool for performance testing."""
        return CalendarBridgeTool("http://localhost:5100")
    
    @pytest.mark.asyncio
    async def test_calendar_list_performance(self, bridge_tool):
        """Test calendar list operation performance."""
        import time
        
        start_time = time.time()
        result = bridge_tool.execute({"operation": "list_calendars"})
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Should complete within reasonable time (bridge has 30s timeout)
        assert duration < 30.0
        assert result["operation"] == "list_calendars"
        
        # Log performance for monitoring
        print(f"Calendar list took {duration:.2f}s")
    
    @pytest.mark.asyncio
    async def test_event_list_performance(self, bridge_tool):
        """Test event list operation performance."""
        import time
        
        start_date = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        end_date = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat().replace("+00:00", "Z")
        
        start_time = time.time()
        result = bridge_tool.execute({
            "operation": "list_events",
            "start_date": start_date,
            "end_date": end_date,
            "limit": 50
        })
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Should complete within reasonable time (bridge has 45s timeout) 
        assert duration < 45.0
        assert result["operation"] == "list_events"
        
        # Log performance for monitoring
        print(f"Event list took {duration:.2f}s")
    
    @pytest.mark.asyncio
    async def test_bridge_health_performance(self, bridge_tool):
        """Test bridge health check performance."""
        import time
        
        start_time = time.time()
        result = bridge_tool.execute({"operation": "health"})
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Health check should be fast
        assert duration < 10.0
        assert result["operation"] == "health"
        
        # Log performance for monitoring
        print(f"Health check took {duration:.2f}s")


if __name__ == "__main__":
    # Run integration tests when executed directly
    pytest.main([__file__, "-v", "--tb=short", "-m", "integration"])