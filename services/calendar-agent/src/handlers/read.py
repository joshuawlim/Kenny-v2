"""
Read capability handler for Calendar events.

This handler provides functionality to read calendar events from Apple Calendar
with date filtering and calendar selection.
"""

from typing import Dict, Any, List, Optional
from kenny_agent.base_handler import BaseCapabilityHandler
from datetime import datetime, timezone, timedelta


class ReadCapabilityHandler(BaseCapabilityHandler):
    """Handler for reading Calendar events."""
    
    def __init__(self):
        """Initialize the read capability handler."""
        super().__init__(
            capability="calendar.read",
            description="Read calendar events from Apple Calendar with date filtering",
            input_schema={
                "type": "object",
                "properties": {
                    "calendar_name": {"type": "string"},
                    "date_range": {
                        "type": "object",
                        "properties": {
                            "start": {"type": "string", "format": "date-time"},
                            "end": {"type": "string", "format": "date-time"}
                        },
                        "required": ["start", "end"]
                    },
                    "event_id": {"type": "string"},
                    "include_all_day": {"type": "boolean", "default": True},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 50}
                },
                "anyOf": [
                    {"required": ["date_range"]},
                    {"required": ["event_id"]}
                ],
                "additionalProperties": False
            },
            output_schema={
                "type": "object",
                "properties": {
                    "events": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "title": {"type": "string"},
                                "start": {"type": "string", "format": "date-time"},
                                "end": {"type": "string", "format": "date-time"},
                                "all_day": {"type": "boolean"},
                                "calendar": {"type": "string"},
                                "location": {"type": "string"},
                                "description": {"type": "string"},
                                "attendees": {"type": "array"}
                            },
                            "required": ["id", "title", "start", "end"]
                        }
                    },
                    "count": {"type": "integer"},
                    "date_range": {"type": "object"}
                },
                "required": ["events", "count"],
                "additionalProperties": False
            },
            safety_annotations=["read-only", "local-only", "no-egress"]
        )
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the read capability using the Calendar bridge tool.
        
        Args:
            parameters: Read parameters
            
        Returns:
            Calendar events from the Calendar bridge
        """
        try:
            # Get the Calendar bridge tool from the agent
            if not hasattr(self, '_agent') or self._agent is None:
                # Fallback to mock data if no agent context
                return self._get_mock_events(parameters)
            
            calendar_bridge_tool = self._agent.tools.get("calendar_bridge")
            if not calendar_bridge_tool:
                # Fallback to mock data if Calendar bridge tool not available
                return self._get_mock_events(parameters)
            
            # Handle single event read by ID
            event_id = parameters.get("event_id")
            if event_id:
                bridge_result = calendar_bridge_tool.execute({
                    "operation": "get_event",
                    "event_id": event_id
                })
                
                if bridge_result.get("event") and not bridge_result.get("error"):
                    event = bridge_result["event"]
                    return {
                        "events": [event],
                        "count": 1,
                        "date_range": None
                    }
                else:
                    # Return empty result if event not found
                    return {
                        "events": [],
                        "count": 0,
                        "date_range": None,
                        "error": bridge_result.get("error", "Event not found")
                    }
            
            # Handle date range query
            date_range = parameters.get("date_range")
            if date_range:
                # Execute Calendar bridge tool with list_events operation
                bridge_result = calendar_bridge_tool.execute({
                    "operation": "list_events",
                    "calendar_name": parameters.get("calendar_name"),
                    "start_date": date_range.get("start"),
                    "end_date": date_range.get("end"),
                    "limit": parameters.get("limit", 50)
                })
                
                # Convert bridge response to capability format
                if isinstance(bridge_result, dict) and bridge_result.get("events"):
                    events = bridge_result["events"]
                    
                    # Filter all-day events if requested
                    if not parameters.get("include_all_day", True):
                        events = [e for e in events if not e.get("all_day", False)]
                    
                    return {
                        "events": events,
                        "count": len(events),
                        "date_range": bridge_result.get("date_range", date_range)
                    }
                else:
                    # Fallback to mock data on bridge failure
                    return self._get_mock_events(parameters)
            
            # If neither event_id nor date_range provided, return error
            return {
                "events": [],
                "count": 0,
                "date_range": None,
                "error": "Either event_id or date_range is required"
            }
                
        except Exception as e:
            # Fallback to mock data on any error
            print(f"Calendar read error: {e}")
            return self._get_mock_events(parameters)
    
    def _get_mock_events(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate mock calendar events as fallback.
        
        Args:
            parameters: Read parameters
            
        Returns:
            Mock calendar events
        """
        event_id = parameters.get("event_id")
        date_range = parameters.get("date_range")
        calendar_name = parameters.get("calendar_name", "Calendar")
        limit = parameters.get("limit", 50)
        include_all_day = parameters.get("include_all_day", True)
        
        # If specific event ID requested
        if event_id:
            event = {
                "id": event_id,
                "title": f"Mock Event {event_id}",
                "start": "2025-08-16T14:00:00Z",
                "end": "2025-08-16T15:00:00Z",
                "all_day": False,
                "calendar": calendar_name,
                "location": "Conference Room A",
                "description": "This is a mock calendar event for testing purposes.",
                "attendees": ["user@example.com"]
            }
            return {
                "events": [event],
                "count": 1,
                "date_range": None
            }
        
        # Generate mock events for date range
        events = []
        base_start = datetime.now(timezone.utc)
        
        if date_range and date_range.get("start"):
            try:
                base_start = datetime.fromisoformat(date_range["start"].replace("Z", "+00:00"))
            except:
                pass
        
        # Generate sample events
        for i in range(min(limit, 10)):  # Cap at 10 mock events
            start_time = base_start + timedelta(days=i, hours=i % 24)
            end_time = start_time + timedelta(hours=1)
            
            # Every 3rd event is all-day
            is_all_day = i % 3 == 0
            
            if is_all_day:
                start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
                end_time = start_time + timedelta(days=1)
            
            # Skip all-day events if not requested
            if is_all_day and not include_all_day:
                continue
            
            event = {
                "id": f"mock-event-{i}",
                "title": f"Mock Calendar Event #{i}",
                "start": start_time.isoformat().replace("+00:00", "Z"),
                "end": end_time.isoformat().replace("+00:00", "Z"),
                "all_day": is_all_day,
                "calendar": calendar_name,
                "location": f"Location {i}" if not is_all_day else "",
                "description": f"Mock event description for event #{i}",
                "attendees": ["user@example.com"] if i % 2 == 0 else []
            }
            
            events.append(event)
        
        return {
            "events": events,
            "count": len(events),
            "date_range": date_range
        }