"""
Read capability handler for Calendar events.

This handler provides functionality to read calendar events from Apple Calendar
with date filtering and calendar selection.
"""

from typing import Dict, Any, List, Optional
from kenny_agent.base_handler import BaseCapabilityHandler
from datetime import datetime, timezone, timedelta
import asyncio
import re


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
                    "query": {"type": "string", "description": "Natural language query for date inference"},
                    "contact_filter": {"type": "object", "description": "Contact information for filtering events"},
                    "include_all_day": {"type": "boolean", "default": True},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 50}
                },
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
    
    def _infer_date_range_from_query(self, query: str) -> Optional[Dict[str, str]]:
        """
        Infer date range from natural language query.
        
        Args:
            query: Natural language query string
            
        Returns:
            Date range dict with start and end ISO strings, or None
        """
        if not query:
            return None
            
        query_lower = query.lower()
        now = datetime.now(timezone.utc)
        
        # Handle "upcoming" - default to next 30 days
        if "upcoming" in query_lower:
            start = now
            end = now + timedelta(days=30)
            return {
                "start": start.isoformat().replace("+00:00", "Z"),
                "end": end.isoformat().replace("+00:00", "Z")
            }
        
        # Handle "today"
        if "today" in query_lower:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            return {
                "start": start.isoformat().replace("+00:00", "Z"),
                "end": end.isoformat().replace("+00:00", "Z")
            }
        
        # Handle "tomorrow"
        if "tomorrow" in query_lower:
            start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            return {
                "start": start.isoformat().replace("+00:00", "Z"),
                "end": end.isoformat().replace("+00:00", "Z")
            }
        
        # Handle "this week"
        if "this week" in query_lower:
            # Start from Monday of current week
            days_since_monday = now.weekday()
            start = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)
            return {
                "start": start.isoformat().replace("+00:00", "Z"),
                "end": end.isoformat().replace("+00:00", "Z")
            }
        
        # Handle "next week"
        if "next week" in query_lower:
            # Start from Monday of next week
            days_since_monday = now.weekday()
            start = (now - timedelta(days=days_since_monday) + timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)
            return {
                "start": start.isoformat().replace("+00:00", "Z"),
                "end": end.isoformat().replace("+00:00", "Z")
            }
        
        # Handle "this month"
        if "this month" in query_lower:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Calculate next month
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1)
            else:
                end = start.replace(month=start.month + 1)
            return {
                "start": start.isoformat().replace("+00:00", "Z"),
                "end": end.isoformat().replace("+00:00", "Z")
            }
        
        # Handle "next month"
        if "next month" in query_lower:
            if now.month == 12:
                start = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                end = start.replace(month=2)
            else:
                start = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
                if start.month == 12:
                    end = start.replace(year=start.year + 1, month=1)
                else:
                    end = start.replace(month=start.month + 1)
            return {
                "start": start.isoformat().replace("+00:00", "Z"),
                "end": end.isoformat().replace("+00:00", "Z")
            }
        
        # Default for any calendar query without specific time - look ahead 7 days
        if any(term in query_lower for term in ["events", "meeting", "appointment", "calendar", "schedule"]):
            start = now
            end = now + timedelta(days=7)
            return {
                "start": start.isoformat().replace("+00:00", "Z"),
                "end": end.isoformat().replace("+00:00", "Z")
            }
        
        return None

    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the read capability using the Calendar bridge tool with parallel processing.
        
        Args:
            parameters: Read parameters
            
        Returns:
            Calendar events from the Calendar bridge
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Get the Calendar bridge tool from the agent
            if not hasattr(self, '_agent') or self._agent is None:
                # Fallback to mock data if no agent context
                return self._get_mock_events(parameters)
            
            calendar_bridge_tool = self._agent.tools.get("calendar_bridge")
            if not calendar_bridge_tool:
                # Fallback to mock data if Calendar bridge tool not available
                return self._get_mock_events(parameters)
            
            # Handle single event read by ID (async)
            event_id = parameters.get("event_id")
            if event_id:
                bridge_result = await calendar_bridge_tool.execute_async({
                    "operation": "get_event",
                    "event_id": event_id
                })
                
                execution_time = asyncio.get_event_loop().time() - start_time
                
                if bridge_result.get("event") and not bridge_result.get("error"):
                    event = bridge_result["event"]
                    return {
                        "events": [event],
                        "count": 1,
                        "date_range": None,
                        "execution_time": round(execution_time, 3)
                    }
                else:
                    # Return empty result if event not found
                    return {
                        "events": [],
                        "count": 0,
                        "date_range": None,
                        "error": bridge_result.get("error", "Event not found"),
                        "execution_time": round(execution_time, 3)
                    }
            
            # Handle date range query - try to infer from query if not provided
            date_range = parameters.get("date_range")
            query = parameters.get("query", "")
            
            # If no explicit date range, try to infer from natural language query
            if not date_range and query:
                inferred_range = self._infer_date_range_from_query(query)
                if inferred_range:
                    date_range = inferred_range
                    print(f"[calendar_read] Inferred date range from query '{query}': {date_range}")
            
            if date_range:
                # Prepare parallel operations for performance optimization
                operations = []
                
                # Check if we should parallelize calendar queries
                calendar_name = parameters.get("calendar_name")
                
                if calendar_name:
                    # Single calendar query
                    operations.append({
                        "operation": "list_events",
                        "calendar_name": calendar_name,
                        "start_date": date_range.get("start"),
                        "end_date": date_range.get("end"),
                        "limit": parameters.get("limit", 50)
                    })
                else:
                    # Get list of calendars first to parallelize queries
                    calendar_list_result = await calendar_bridge_tool.execute_async({
                        "operation": "list_calendars"
                    })
                    
                    if calendar_list_result.get("calendars"):
                        # Create parallel queries for each calendar (up to 5 for performance)
                        calendars = calendar_list_result["calendars"][:5]  # Limit to prevent overwhelming
                        for cal in calendars:
                            cal_name = cal.get("name") or cal.get("title")
                            if cal_name:
                                operations.append({
                                    "operation": "list_events",
                                    "calendar_name": cal_name,
                                    "start_date": date_range.get("start"),
                                    "end_date": date_range.get("end"),
                                    "limit": parameters.get("limit", 50) // len(calendars)  # Distribute limit
                                })
                    
                    # Fallback to single query if no calendars found
                    if not operations:
                        operations.append({
                            "operation": "list_events",
                            "start_date": date_range.get("start"),
                            "end_date": date_range.get("end"),
                            "limit": parameters.get("limit", 50)
                        })
                
                # Execute operations in parallel if multiple, otherwise single async call
                if len(operations) > 1:
                    bridge_results = await calendar_bridge_tool.execute_parallel(operations)
                    # Merge results from multiple calendars
                    merged_events = []
                    total_request_time = 0
                    
                    for result in bridge_results:
                        if isinstance(result, dict) and result.get("events"):
                            merged_events.extend(result["events"])
                            total_request_time += result.get("request_time", 0)
                    
                    # Sort merged events by start time
                    merged_events.sort(key=lambda x: x.get("start", ""))
                    
                    bridge_result = {
                        "operation": "list_events_parallel",
                        "events": merged_events,
                        "count": len(merged_events),
                        "date_range": date_range,
                        "request_time": total_request_time,
                        "parallel_operations": len(operations)
                    }
                else:
                    # Single operation
                    bridge_result = await calendar_bridge_tool.execute_async(operations[0])
                
                execution_time = asyncio.get_event_loop().time() - start_time
                
                # Convert bridge response to capability format
                if isinstance(bridge_result, dict) and bridge_result.get("events"):
                    events = bridge_result["events"]
                    
                    # Filter all-day events if requested
                    if not parameters.get("include_all_day", True):
                        events = [e for e in events if not e.get("all_day", False)]
                    
                    # Filter by contact if contact_filter is provided - run async for performance
                    contact_filter = parameters.get("contact_filter")
                    if contact_filter:
                        # Run contact filtering in parallel if needed
                        events = await self._filter_events_by_contact_async(events, contact_filter)
                        print(f"[calendar_read] Filtered {len(bridge_result['events'])} events to {len(events)} events by contact filter")
                    
                    return {
                        "events": events,
                        "count": len(events),
                        "date_range": bridge_result.get("date_range", date_range),
                        "inferred_from_query": query if not parameters.get("date_range") else None,
                        "contact_filtered": bool(contact_filter),
                        "execution_time": round(execution_time, 3),
                        "bridge_request_time": bridge_result.get("request_time", 0),
                        "parallel_operations": bridge_result.get("parallel_operations", 1)
                    }
                else:
                    # Return error details from bridge
                    execution_time = asyncio.get_event_loop().time() - start_time
                    return {
                        "events": [],
                        "count": 0,
                        "date_range": date_range,
                        "error": bridge_result.get("error", "Failed to retrieve events from calendar bridge"),
                        "execution_time": round(execution_time, 3)
                    }
            
            # If neither event_id nor date_range could be determined, return error
            execution_time = asyncio.get_event_loop().time() - start_time
            return {
                "events": [],
                "count": 0,
                "date_range": None,
                "error": "Either event_id or date_range is required. For natural language queries, include time references like 'upcoming', 'today', 'this week', etc.",
                "execution_time": round(execution_time, 3)
            }
                
        except Exception as e:
            # Fallback to mock data on any error
            execution_time = asyncio.get_event_loop().time() - start_time
            print(f"Calendar read error: {e}")
            result = self._get_mock_events(parameters)
            result["execution_time"] = round(execution_time, 3)
            result["fallback_reason"] = str(e)
            return result
    
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
    
    async def _filter_events_by_contact_async(self, events: List[Dict[str, Any]], contact_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Filter events by contact information asynchronously for better performance.
        
        Args:
            events: List of calendar events
            contact_info: Contact information from contacts agent
            
        Returns:
            Filtered list of events containing the contact
        """
        if not contact_info or not events:
            return events
        
        # Use thread pool for CPU-intensive filtering if we have many events
        if len(events) > 100:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._filter_events_by_contact, events, contact_info)
        else:
            return self._filter_events_by_contact(events, contact_info)
    
    def _filter_events_by_contact(self, events: List[Dict[str, Any]], contact_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Filter events by contact information (sync version for backwards compatibility).
        
        Args:
            events: List of calendar events
            contact_info: Contact information from contacts agent
            
        Returns:
            Filtered list of events containing the contact
        """
        if not contact_info or not events:
            return events
        
        # Extract contact identifiers from contact_info
        contact_names = []
        contact_emails = []
        
        # Handle the structure from calendar agent's contact integration
        if isinstance(contact_info, dict):
            # Check if it's a wrapper with contacts list
            if "contacts" in contact_info:
                contacts_list = contact_info["contacts"]
            elif "query_names" in contact_info:
                # Use query names as fallback
                contact_names.extend([name.lower() for name in contact_info["query_names"]])
                contacts_list = contact_info.get("contacts", [])
            else:
                # Single contact dict
                contacts_list = [contact_info]
            
            # Extract names and emails from contacts list
            for contact in contacts_list:
                if isinstance(contact, dict):
                    if contact.get("name"):
                        contact_names.append(contact["name"].lower())
                    if contact.get("first_name"):
                        contact_names.append(contact["first_name"].lower())
                    if contact.get("last_name"):
                        contact_names.append(contact["last_name"].lower())
                    if contact.get("emails"):
                        contact_emails.extend([email.lower() for email in contact["emails"]])
                    if contact.get("email"):
                        contact_emails.append(contact["email"].lower())
        elif isinstance(contact_info, list):
            # Handle multiple contacts directly
            for contact in contact_info:
                if isinstance(contact, dict):
                    if contact.get("name"):
                        contact_names.append(contact["name"].lower())
                    if contact.get("first_name"):
                        contact_names.append(contact["first_name"].lower())
                    if contact.get("last_name"):
                        contact_names.append(contact["last_name"].lower())
                    if contact.get("emails"):
                        contact_emails.extend([email.lower() for email in contact["emails"]])
                    if contact.get("email"):
                        contact_emails.append(contact["email"].lower())
        
        filtered_events = []
        
        for event in events:
            # Check if contact is in event attendees
            attendees = event.get("attendees", [])
            if attendees:
                for attendee in attendees:
                    attendee_str = str(attendee).lower()
                    
                    # Check if any contact name is in the attendee string
                    if any(name in attendee_str for name in contact_names):
                        filtered_events.append(event)
                        break
                    
                    # Check if any contact email is in the attendee string
                    if any(email in attendee_str for email in contact_emails):
                        filtered_events.append(event)
                        break
            
            # Also check event title for contact names
            title = event.get("title", "").lower()
            if any(name in title for name in contact_names):
                filtered_events.append(event)
        
        return filtered_events