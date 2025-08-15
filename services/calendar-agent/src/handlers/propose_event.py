"""
Propose Event capability handler for Calendar events.

This handler provides functionality to propose new calendar events with conflict
detection and approval requirements.
"""

from typing import Dict, Any, List, Optional
from kenny_agent.base_handler import BaseCapabilityHandler
from datetime import datetime, timezone, timedelta
import uuid


class ProposeEventCapabilityHandler(BaseCapabilityHandler):
    """Handler for proposing calendar events."""
    
    def __init__(self):
        """Initialize the propose event capability handler."""
        super().__init__(
            capability="calendar.propose_event",
            description="Generate event proposals with conflict detection and approval requirements",
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "start": {"type": "string", "format": "date-time"},
                    "end": {"type": "string", "format": "date-time"},
                    "all_day": {"type": "boolean", "default": False},
                    "calendar_name": {"type": "string"},
                    "location": {"type": "string"},
                    "description": {"type": "string"},
                    "attendees": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "recurrence": {"type": "string"},
                    "reminder_minutes": {"type": "integer", "minimum": 0}
                },
                "required": ["title", "start", "end"],
                "additionalProperties": False
            },
            output_schema={
                "type": "object",
                "properties": {
                    "proposal": {
                        "type": "object",
                        "properties": {
                            "proposal_id": {"type": "string"},
                            "title": {"type": "string"},
                            "start": {"type": "string", "format": "date-time"},
                            "end": {"type": "string", "format": "date-time"},
                            "all_day": {"type": "boolean"},
                            "calendar": {"type": "string"},
                            "location": {"type": "string"},
                            "description": {"type": "string"},
                            "attendees": {"type": "array"},
                            "conflicts": {"type": "array"},
                            "suggestions": {"type": "array"}
                        },
                        "required": ["proposal_id", "title", "start", "end"]
                    },
                    "requires_approval": {"type": "boolean"},
                    "approval_reason": {"type": "string"}
                },
                "required": ["proposal", "requires_approval"],
                "additionalProperties": False
            },
            safety_annotations=["requires-approval", "local-only", "no-egress"]
        )
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the propose event capability with conflict detection.
        
        Args:
            parameters: Event proposal parameters
            
        Returns:
            Event proposal with conflict analysis and approval requirements
        """
        try:
            # Generate unique proposal ID
            proposal_id = str(uuid.uuid4())
            
            # Extract event parameters
            title = parameters.get("title")
            start = parameters.get("start")
            end = parameters.get("end")
            all_day = parameters.get("all_day", False)
            calendar_name = parameters.get("calendar_name", "Calendar")
            location = parameters.get("location", "")
            description = parameters.get("description", "")
            attendees = parameters.get("attendees", [])
            
            # Validate date range
            try:
                start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                
                if end_dt <= start_dt:
                    return {
                        "proposal": None,
                        "requires_approval": False,
                        "error": "End time must be after start time"
                    }
            except ValueError as e:
                return {
                    "proposal": None,
                    "requires_approval": False,
                    "error": f"Invalid date format: {str(e)}"
                }
            
            # Check for conflicts
            conflicts = await self._detect_conflicts(start, end, calendar_name)
            
            # Generate suggestions if there are conflicts
            suggestions = []
            if conflicts:
                suggestions = await self._generate_suggestions(start, end, conflicts)
            
            # Create event proposal
            proposal = {
                "proposal_id": proposal_id,
                "title": title,
                "start": start,
                "end": end,
                "all_day": all_day,
                "calendar": calendar_name,
                "location": location,
                "description": description,
                "attendees": attendees,
                "conflicts": conflicts,
                "suggestions": suggestions
            }
            
            # Determine approval requirements
            requires_approval, approval_reason = self._determine_approval_requirements(
                parameters, conflicts, attendees
            )
            
            return {
                "proposal": proposal,
                "requires_approval": requires_approval,
                "approval_reason": approval_reason
            }
                
        except Exception as e:
            # Return error with safe fallback
            print(f"Calendar propose event error: {e}")
            return {
                "proposal": None,
                "requires_approval": True,
                "error": f"Proposal generation failed: {str(e)}",
                "approval_reason": "Error occurred during proposal generation"
            }
    
    async def _detect_conflicts(self, start: str, end: str, calendar_name: str) -> List[Dict[str, Any]]:
        """
        Detect conflicts with existing calendar events.
        
        Args:
            start: Event start time
            end: Event end time
            calendar_name: Calendar to check
            
        Returns:
            List of conflicting events
        """
        try:
            # Get the Calendar bridge tool from the agent
            if not hasattr(self, '_agent') or self._agent is None:
                return []  # No conflicts detectable without agent context
            
            calendar_bridge_tool = self._agent.tools.get("calendar_bridge")
            if not calendar_bridge_tool:
                return []  # No conflicts detectable without bridge tool
            
            # Query existing events in the time range
            bridge_result = calendar_bridge_tool.execute({
                "operation": "list_events",
                "calendar_name": calendar_name,
                "start_date": start,
                "end_date": end,
                "limit": 100
            })
            
            conflicts = []
            if bridge_result.get("events") and not bridge_result.get("error"):
                events = bridge_result["events"]
                
                # Check for time overlaps
                start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                
                for event in events:
                    try:
                        event_start = datetime.fromisoformat(event["start"].replace("Z", "+00:00"))
                        event_end = datetime.fromisoformat(event["end"].replace("Z", "+00:00"))
                        
                        # Check for overlap
                        if (start_dt < event_end and end_dt > event_start):
                            conflict = {
                                "id": event.get("id"),
                                "title": event.get("title"),
                                "start": event.get("start"),
                                "end": event.get("end"),
                                "overlap_type": self._determine_overlap_type(
                                    start_dt, end_dt, event_start, event_end
                                )
                            }
                            conflicts.append(conflict)
                    except (ValueError, KeyError):
                        # Skip events with invalid date formats
                        continue
            
            return conflicts
            
        except Exception as e:
            print(f"Conflict detection error: {e}")
            return []  # Return no conflicts on error to allow processing to continue
    
    def _determine_overlap_type(self, new_start: datetime, new_end: datetime, 
                               existing_start: datetime, existing_end: datetime) -> str:
        """Determine the type of overlap between events."""
        if new_start >= existing_start and new_end <= existing_end:
            return "contained_within"
        elif new_start <= existing_start and new_end >= existing_end:
            return "contains"
        elif new_start < existing_end and new_end > existing_end:
            return "overlaps_end"
        elif new_start < existing_start and new_end > existing_start:
            return "overlaps_start"
        else:
            return "partial_overlap"
    
    async def _generate_suggestions(self, start: str, end: str, 
                                  conflicts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate alternative time suggestions to avoid conflicts.
        
        Args:
            start: Original start time
            end: Original end time
            conflicts: List of conflicting events
            
        Returns:
            List of suggested alternative times
        """
        suggestions = []
        
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
            duration = end_dt - start_dt
            
            # Suggest times after all conflicts end
            if conflicts:
                latest_conflict_end = max(
                    datetime.fromisoformat(c["end"].replace("Z", "+00:00")) 
                    for c in conflicts
                )
                
                # Suggest 30 minutes after the latest conflict ends
                suggested_start = latest_conflict_end + timedelta(minutes=30)
                suggested_end = suggested_start + duration
                
                suggestions.append({
                    "start": suggested_start.isoformat().replace("+00:00", "Z"),
                    "end": suggested_end.isoformat().replace("+00:00", "Z"),
                    "reason": "After existing appointments"
                })
                
                # Suggest next day at same time
                next_day_start = start_dt + timedelta(days=1)
                next_day_end = next_day_start + duration
                
                suggestions.append({
                    "start": next_day_start.isoformat().replace("+00:00", "Z"),
                    "end": next_day_end.isoformat().replace("+00:00", "Z"),
                    "reason": "Same time next day"
                })
            
        except Exception as e:
            print(f"Suggestion generation error: {e}")
        
        return suggestions
    
    def _determine_approval_requirements(self, parameters: Dict[str, Any], 
                                       conflicts: List[Dict[str, Any]], 
                                       attendees: List[str]) -> tuple[bool, str]:
        """
        Determine if the event proposal requires approval.
        
        Args:
            parameters: Event parameters
            conflicts: List of conflicts
            attendees: List of attendees
            
        Returns:
            Tuple of (requires_approval, reason)
        """
        # Always require approval for write operations (calendar creation)
        reasons = []
        
        # Always require approval for calendar writes
        reasons.append("Calendar write operations require user approval")
        
        # Additional approval reasons
        if conflicts:
            reasons.append(f"Event conflicts with {len(conflicts)} existing appointment(s)")
        
        if attendees:
            reasons.append(f"Event includes {len(attendees)} attendee(s)")
        
        # Check for business hours (optional additional validation)
        try:
            start_dt = datetime.fromisoformat(parameters["start"].replace("Z", "+00:00"))
            if start_dt.weekday() >= 5:  # Weekend
                reasons.append("Event scheduled for weekend")
            elif start_dt.hour < 8 or start_dt.hour > 18:  # Outside business hours
                reasons.append("Event scheduled outside business hours")
        except:
            pass
        
        return True, "; ".join(reasons)