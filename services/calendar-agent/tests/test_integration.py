"""
Integration tests for Calendar Agent.

Tests the Calendar Agent's capabilities, tools, and bridge integration.
"""

import pytest
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock

# Add parent directory to Python path to import agent modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent import CalendarAgent
from tools.calendar_bridge import CalendarBridgeTool
from handlers.read import ReadCapabilityHandler
from handlers.propose_event import ProposeEventCapabilityHandler 
from handlers.write_event import WriteEventCapabilityHandler


class TestCalendarAgent:
    """Test Calendar Agent initialization and basic functionality."""
    
    @pytest.fixture
    def calendar_agent(self):
        """Create a Calendar Agent instance for testing."""
        return CalendarAgent()
    
    def test_agent_initialization(self, calendar_agent):
        """Test that the Calendar Agent initializes correctly."""
        assert calendar_agent.agent_id == "calendar-agent"
        assert calendar_agent.name == "Calendar Agent"
        assert "calendar:events" in calendar_agent.data_scopes
        assert "calendar:calendars" in calendar_agent.data_scopes
        assert "macos-bridge" in calendar_agent.tool_access
        assert "approval-workflow" in calendar_agent.tool_access
        assert calendar_agent.egress_domains == []
    
    def test_capabilities_registered(self, calendar_agent):
        """Test that all expected capabilities are registered."""
        expected_capabilities = ["calendar.read", "calendar.propose_event", "calendar.write_event"]
        
        assert len(calendar_agent.capabilities) == 3
        for capability in expected_capabilities:
            assert capability in calendar_agent.capabilities
    
    def test_tools_registered(self, calendar_agent):
        """Test that required tools are registered."""
        assert "calendar_bridge" in calendar_agent.tools
        assert isinstance(calendar_agent.tools["calendar_bridge"], CalendarBridgeTool)
    
    def test_health_monitoring_setup(self, calendar_agent):
        """Test that health monitoring is properly configured."""
        assert hasattr(calendar_agent, 'health_monitor')
        assert calendar_agent.health_monitor is not None
        
        # Check that required health checks are added
        health_checks = [check.name for check in calendar_agent.health_monitor.health_checks]
        expected_checks = [
            "agent_status", "capability_count", "tool_access", 
            "bridge_connectivity", "calendar_access"
        ]
        
        for check in expected_checks:
            assert check in health_checks
    
    @pytest.mark.asyncio
    async def test_agent_lifecycle(self, calendar_agent):
        """Test agent start and stop lifecycle."""
        # Test start
        await calendar_agent.start()
        assert calendar_agent.health_status.get("status") == "healthy"
        
        # Test stop 
        await calendar_agent.stop()
        assert calendar_agent.health_status.get("status") == "degraded"


class TestCalendarBridgeTool:
    """Test Calendar Bridge Tool functionality."""
    
    @pytest.fixture
    def bridge_tool(self):
        """Create a Calendar Bridge Tool instance."""
        return CalendarBridgeTool("http://localhost:5100")
    
    def test_bridge_tool_initialization(self, bridge_tool):
        """Test bridge tool initialization."""
        assert bridge_tool.name == "calendar_bridge"
        assert bridge_tool.description == "Access Apple Calendar functionality through macOS Bridge"
        assert bridge_tool.category == "calendar"
        assert bridge_tool.bridge_url == "http://localhost:5100"
    
    def test_bridge_tool_input_schema(self, bridge_tool):
        """Test bridge tool input schema validation."""
        schema = bridge_tool.input_schema
        assert "operation" in schema["properties"]
        assert schema["properties"]["operation"]["enum"] == [
            "list_calendars", "list_events", "get_event", "create_event", "health"
        ]
        assert "operation" in schema["required"]
    
    @patch('httpx.Client')
    def test_list_calendars_success(self, mock_client, bridge_tool):
        """Test successful calendar list operation."""
        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = [
            {"id": "cal-1", "name": "Calendar", "writable": True}
        ]
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response
        
        result = bridge_tool.execute({"operation": "list_calendars"})
        
        assert result["operation"] == "list_calendars"
        assert len(result["calendars"]) == 1
        assert result["calendars"][0]["name"] == "Calendar"
        assert result["count"] == 1
    
    @patch('httpx.Client')
    def test_list_events_success(self, mock_client, bridge_tool):
        """Test successful events list operation."""
        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "events": [
                {
                    "id": "event-1",
                    "title": "Test Event", 
                    "start": "2025-08-16T10:00:00Z",
                    "end": "2025-08-16T11:00:00Z",
                    "calendar": "Calendar"
                }
            ],
            "total": 1
        }
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response
        
        result = bridge_tool.execute({
            "operation": "list_events",
            "calendar_name": "Calendar",
            "limit": 10
        })
        
        assert result["operation"] == "list_events"
        assert len(result["events"]) == 1
        assert result["events"][0]["title"] == "Test Event"
        assert result["count"] == 1
        assert result["total"] == 1
    
    @patch('httpx.Client')
    def test_get_event_success(self, mock_client, bridge_tool):
        """Test successful event get operation."""
        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "id": "event-1",
            "title": "Test Event",
            "start": "2025-08-16T10:00:00Z",
            "end": "2025-08-16T11:00:00Z"
        }
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response
        
        result = bridge_tool.execute({
            "operation": "get_event",
            "event_id": "event-1"
        })
        
        assert result["operation"] == "get_event"
        assert result["event_id"] == "event-1"
        assert result["event"]["title"] == "Test Event"
    
    @patch('httpx.Client')
    def test_create_event_success(self, mock_client, bridge_tool):
        """Test successful event creation."""
        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "id": "new-event-1",
            "title": "New Event",
            "start": "2025-08-16T14:00:00Z",
            "end": "2025-08-16T15:00:00Z",
            "created": True
        }
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response
        
        event_data = {
            "title": "New Event",
            "start": "2025-08-16T14:00:00Z",
            "end": "2025-08-16T15:00:00Z",
            "calendar": "Calendar"
        }
        
        result = bridge_tool.execute({
            "operation": "create_event",
            "event_data": event_data
        })
        
        assert result["operation"] == "create_event"
        assert result["created"] is True
        assert result["event"]["title"] == "New Event"
    
    @patch('httpx.Client')
    def test_bridge_error_handling(self, mock_client, bridge_tool):
        """Test bridge error handling."""
        # Mock HTTP error
        mock_client.return_value.__enter__.return_value.get.side_effect = Exception("Connection error")
        
        result = bridge_tool.execute({"operation": "list_calendars"})
        
        assert "error" in result
        assert "Connection error" in result["error"]


class TestReadCapabilityHandler:
    """Test Calendar Read capability handler."""
    
    @pytest.fixture
    def read_handler(self):
        """Create a Read capability handler."""
        handler = ReadCapabilityHandler()
        # Mock agent with bridge tool
        handler._agent = Mock()
        handler._agent.tools = {"calendar_bridge": Mock()}
        return handler
    
    def test_read_handler_initialization(self, read_handler):
        """Test read handler initialization."""
        assert read_handler.capability == "calendar.read"
        assert read_handler.description == "Read calendar events from Apple Calendar with date filtering"
        assert "read-only" in read_handler.safety_annotations
        assert "local-only" in read_handler.safety_annotations
        assert "no-egress" in read_handler.safety_annotations
    
    @pytest.mark.asyncio
    async def test_read_by_event_id(self, read_handler):
        """Test reading a specific event by ID."""
        # Mock bridge tool response
        read_handler._agent.tools["calendar_bridge"].execute.return_value = {
            "event": {
                "id": "event-1",
                "title": "Test Event",
                "start": "2025-08-16T10:00:00Z",
                "end": "2025-08-16T11:00:00Z"
            }
        }
        
        result = await read_handler.execute({"event_id": "event-1"})
        
        assert result["count"] == 1
        assert len(result["events"]) == 1
        assert result["events"][0]["id"] == "event-1"
        assert result["events"][0]["title"] == "Test Event"
    
    @pytest.mark.asyncio
    async def test_read_by_date_range(self, read_handler):
        """Test reading events by date range."""
        # Mock bridge tool response
        read_handler._agent.tools["calendar_bridge"].execute.return_value = {
            "events": [
                {
                    "id": "event-1",
                    "title": "Event 1",
                    "start": "2025-08-16T10:00:00Z",
                    "end": "2025-08-16T11:00:00Z",
                    "all_day": False
                },
                {
                    "id": "event-2", 
                    "title": "All Day Event",
                    "start": "2025-08-17T00:00:00Z",
                    "end": "2025-08-18T00:00:00Z",
                    "all_day": True
                }
            ]
        }
        
        result = await read_handler.execute({
            "date_range": {
                "start": "2025-08-16T00:00:00Z",
                "end": "2025-08-18T00:00:00Z"
            }
        })
        
        assert result["count"] == 2
        assert len(result["events"]) == 2
    
    @pytest.mark.asyncio
    async def test_read_filter_all_day_events(self, read_handler):
        """Test filtering out all-day events."""
        # Mock bridge tool response
        read_handler._agent.tools["calendar_bridge"].execute.return_value = {
            "events": [
                {
                    "id": "event-1",
                    "title": "Regular Event",
                    "all_day": False
                },
                {
                    "id": "event-2",
                    "title": "All Day Event", 
                    "all_day": True
                }
            ]
        }
        
        result = await read_handler.execute({
            "date_range": {
                "start": "2025-08-16T00:00:00Z",
                "end": "2025-08-18T00:00:00Z"
            },
            "include_all_day": False
        })
        
        assert result["count"] == 1
        assert result["events"][0]["title"] == "Regular Event"
    
    @pytest.mark.asyncio
    async def test_read_fallback_to_mock(self, read_handler):
        """Test fallback to mock data when bridge fails."""
        # Remove agent reference to trigger fallback
        read_handler._agent = None
        
        result = await read_handler.execute({
            "date_range": {
                "start": "2025-08-16T00:00:00Z",
                "end": "2025-08-18T00:00:00Z"
            }
        })
        
        assert result["count"] > 0
        assert len(result["events"]) > 0
        # Mock events should have predictable structure
        assert all("id" in event and "title" in event for event in result["events"])


class TestProposeEventCapabilityHandler:
    """Test Calendar Propose Event capability handler."""
    
    @pytest.fixture
    def propose_handler(self):
        """Create a Propose Event capability handler."""
        handler = ProposeEventCapabilityHandler()
        # Mock agent with bridge tool
        handler._agent = Mock()
        handler._agent.tools = {"calendar_bridge": Mock()}
        return handler
    
    def test_propose_handler_initialization(self, propose_handler):
        """Test propose event handler initialization."""
        assert propose_handler.capability == "calendar.propose_event"
        assert "requires-approval" in propose_handler.safety_annotations
        assert "local-only" in propose_handler.safety_annotations
        assert "no-egress" in propose_handler.safety_annotations
    
    @pytest.mark.asyncio
    async def test_propose_event_no_conflicts(self, propose_handler):
        """Test proposing an event with no conflicts."""
        # Mock bridge tool to return no conflicting events
        propose_handler._agent.tools["calendar_bridge"].execute.return_value = {
            "events": []
        }
        
        result = await propose_handler.execute({
            "title": "Test Meeting",
            "start": "2025-08-16T14:00:00Z",
            "end": "2025-08-16T15:00:00Z"
        })
        
        assert result["requires_approval"] is True
        assert result["proposal"]["title"] == "Test Meeting"
        assert len(result["proposal"]["conflicts"]) == 0
        assert len(result["proposal"]["suggestions"]) == 0
    
    @pytest.mark.asyncio
    async def test_propose_event_with_conflicts(self, propose_handler):
        """Test proposing an event with conflicts."""
        # Mock bridge tool to return conflicting event
        propose_handler._agent.tools["calendar_bridge"].execute.return_value = {
            "events": [
                {
                    "id": "existing-event",
                    "title": "Existing Meeting",
                    "start": "2025-08-16T14:30:00Z",
                    "end": "2025-08-16T15:30:00Z"
                }
            ]
        }
        
        result = await propose_handler.execute({
            "title": "New Meeting",
            "start": "2025-08-16T14:00:00Z",
            "end": "2025-08-16T15:00:00Z"
        })
        
        assert result["requires_approval"] is True
        assert len(result["proposal"]["conflicts"]) == 1
        assert result["proposal"]["conflicts"][0]["title"] == "Existing Meeting"
        assert len(result["proposal"]["suggestions"]) > 0  # Should suggest alternatives
    
    @pytest.mark.asyncio
    async def test_propose_event_invalid_dates(self, propose_handler):
        """Test proposing an event with invalid dates."""
        result = await propose_handler.execute({
            "title": "Invalid Event",
            "start": "2025-08-16T15:00:00Z",
            "end": "2025-08-16T14:00:00Z"  # End before start
        })
        
        assert result["requires_approval"] is False
        assert "error" in result
        assert "End time must be after start time" in result["error"]
    
    @pytest.mark.asyncio
    async def test_approval_requirements_with_attendees(self, propose_handler):
        """Test approval requirements with attendees."""
        propose_handler._agent.tools["calendar_bridge"].execute.return_value = {"events": []}
        
        result = await propose_handler.execute({
            "title": "Team Meeting",
            "start": "2025-08-16T14:00:00Z",
            "end": "2025-08-16T15:00:00Z",
            "attendees": ["alice@example.com", "bob@example.com"]
        })
        
        assert result["requires_approval"] is True
        assert "attendee" in result["approval_reason"].lower()


class TestWriteEventCapabilityHandler:
    """Test Calendar Write Event capability handler."""
    
    @pytest.fixture
    def write_handler(self):
        """Create a Write Event capability handler."""
        handler = WriteEventCapabilityHandler()
        # Mock agent with bridge tool
        handler._agent = Mock()
        handler._agent.tools = {"calendar_bridge": Mock()}
        return handler
    
    def test_write_handler_initialization(self, write_handler):
        """Test write event handler initialization."""
        assert write_handler.capability == "calendar.write_event"
        assert "requires-approval" in write_handler.safety_annotations
        assert "write-operation" in write_handler.safety_annotations
        assert "local-only" in write_handler.safety_annotations
        assert "no-egress" in write_handler.safety_annotations
    
    @pytest.mark.asyncio
    async def test_write_event_approved(self, write_handler):
        """Test writing an approved event."""
        # Mock successful event creation
        write_handler._agent.tools["calendar_bridge"].execute.return_value = {
            "created": True,
            "event": {
                "id": "new-event-1",
                "title": "New Event",
                "start": "2025-08-16T14:00:00Z",
                "end": "2025-08-16T15:00:00Z",
                "calendar": "Calendar"
            }
        }
        
        result = await write_handler.execute({
            "proposal_id": "test-proposal-1",
            "approved": True
        })
        
        assert result["status"] == "created"
        assert result["event"]["title"] == "New Event"
        assert result["event"]["created"] is True
    
    @pytest.mark.asyncio
    async def test_write_event_rejected(self, write_handler):
        """Test handling rejected event creation."""
        result = await write_handler.execute({
            "proposal_id": "test-proposal-1",
            "approved": False
        })
        
        assert result["status"] == "rejected"
        assert result["event"] is None
        assert "not approved" in result["message"]
    
    @pytest.mark.asyncio
    async def test_write_event_missing_proposal(self, write_handler):
        """Test handling missing proposal ID."""
        result = await write_handler.execute({
            "approved": True
        })
        
        assert result["status"] == "error"
        assert result["event"] is None
        assert "Proposal ID is required" in result["message"]
    
    @pytest.mark.asyncio
    async def test_write_event_with_modifications(self, write_handler):
        """Test writing event with user modifications."""
        # Mock successful event creation
        write_handler._agent.tools["calendar_bridge"].execute.return_value = {
            "created": True,
            "event": {
                "id": "modified-event-1",
                "title": "Modified Event Title",
                "start": "2025-08-16T15:00:00Z",
                "end": "2025-08-16T16:00:00Z"
            }
        }
        
        result = await write_handler.execute({
            "proposal_id": "test-proposal-1",
            "approved": True,
            "modifications": {
                "title": "Modified Event Title",
                "start": "2025-08-16T15:00:00Z",
                "end": "2025-08-16T16:00:00Z"
            }
        })
        
        assert result["status"] == "created"
        assert result["event"]["title"] == "Modified Event Title"
    
    @pytest.mark.asyncio
    async def test_write_event_bridge_failure(self, write_handler):
        """Test handling bridge failure during event creation."""
        # Mock bridge failure
        write_handler._agent.tools["calendar_bridge"].execute.return_value = {
            "created": False,
            "error": "Calendar access denied"
        }
        
        result = await write_handler.execute({
            "proposal_id": "test-proposal-1",
            "approved": True
        })
        
        assert result["status"] == "error"
        assert result["event"] is None
        assert "Calendar access denied" in result["message"]


@pytest.mark.integration
class TestEndToEndCalendarAgent:
    """End-to-end integration tests for Calendar Agent."""
    
    @pytest.fixture
    def calendar_agent(self):
        """Create Calendar Agent for end-to-end testing."""
        return CalendarAgent()
    
    @pytest.mark.asyncio
    async def test_complete_event_workflow(self, calendar_agent):
        """Test complete workflow from read → propose → approve → write."""
        await calendar_agent.start()
        
        try:
            # 1. Test reading existing events
            read_handler = calendar_agent.capabilities["calendar.read"]
            read_result = await read_handler.execute({
                "date_range": {
                    "start": "2025-08-16T00:00:00Z",
                    "end": "2025-08-17T00:00:00Z"
                }
            })
            assert "events" in read_result
            
            # 2. Test proposing a new event
            propose_handler = calendar_agent.capabilities["calendar.propose_event"]
            propose_result = await propose_handler.execute({
                "title": "Integration Test Event",
                "start": "2025-08-16T14:00:00Z",
                "end": "2025-08-16T15:00:00Z"
            })
            assert propose_result["requires_approval"] is True
            proposal_id = propose_result["proposal"]["proposal_id"]
            
            # 3. Test approving and writing the event
            write_handler = calendar_agent.capabilities["calendar.write_event"]
            write_result = await write_handler.execute({
                "proposal_id": proposal_id,
                "approved": True
            })
            assert write_result["status"] in ["created", "error"]  # Allow both for mock/live modes
            
        finally:
            await calendar_agent.stop()
    
    @pytest.mark.asyncio
    async def test_agent_health_checks(self, calendar_agent):
        """Test all agent health checks."""
        await calendar_agent.start()
        
        try:
            # Test each health check function
            agent_status = calendar_agent.check_agent_status()
            assert agent_status.status == "healthy"
            
            capability_count = calendar_agent.check_capability_count()
            assert capability_count.status == "healthy"
            
            tool_access = calendar_agent.check_tool_access()
            assert tool_access.status in ["healthy", "degraded"]
            
            bridge_connectivity = calendar_agent.check_bridge_connectivity()
            assert bridge_connectivity.status in ["healthy", "degraded", "unhealthy"]
            
            calendar_access = calendar_agent.check_calendar_access()
            assert calendar_access.status in ["healthy", "degraded", "unhealthy"]
            
        finally:
            await calendar_agent.stop()


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v", "--tb=short"])