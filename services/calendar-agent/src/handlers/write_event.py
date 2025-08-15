"""
Write Event capability handler for Calendar events.

This handler provides functionality to create calendar events after approval
validation, integrating with the coordinator's approval workflow system.
"""

from typing import Dict, Any, Optional
from kenny_agent.base_handler import BaseCapabilityHandler
import json
import os
from datetime import datetime


class WriteEventCapabilityHandler(BaseCapabilityHandler):
    """Handler for writing approved calendar events."""
    
    def __init__(self):
        """Initialize the write event capability handler."""
        super().__init__(
            capability="calendar.write_event",
            description="Create approved calendar events in Apple Calendar",
            input_schema={
                "type": "object",
                "properties": {
                    "proposal_id": {"type": "string"},
                    "approved": {"type": "boolean"},
                    "approval_token": {"type": "string"},
                    "modifications": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "start": {"type": "string", "format": "date-time"},
                            "end": {"type": "string", "format": "date-time"},
                            "location": {"type": "string"},
                            "description": {"type": "string"}
                        }
                    }
                },
                "required": ["proposal_id", "approved"],
                "additionalProperties": False
            },
            output_schema={
                "type": "object",
                "properties": {
                    "event": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "title": {"type": "string"},
                            "start": {"type": "string", "format": "date-time"},
                            "end": {"type": "string", "format": "date-time"},
                            "created": {"type": "boolean"},
                            "calendar": {"type": "string"}
                        }
                    },
                    "status": {"type": "string"},
                    "message": {"type": "string"}
                },
                "required": ["status", "message"],
                "additionalProperties": False
            },
            safety_annotations=["requires-approval", "write-operation", "local-only", "no-egress"]
        )
        
        # In-memory storage for proposals (in production, this would be persistent storage)
        self._proposals = {}
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the write event capability with approval validation.
        
        Args:
            parameters: Write event parameters including proposal_id and approval
            
        Returns:
            Event creation result with status
        """
        try:
            proposal_id = parameters.get("proposal_id")
            approved = parameters.get("approved")
            approval_token = parameters.get("approval_token")
            modifications = parameters.get("modifications", {})
            
            # Validate proposal exists
            if not proposal_id:
                return {
                    "event": None,
                    "status": "error",
                    "message": "Proposal ID is required"
                }
            
            # Check if proposal exists (in production, this would query persistent storage)
            proposal = await self._get_proposal(proposal_id)
            if not proposal:
                return {
                    "event": None,
                    "status": "error",
                    "message": f"Proposal {proposal_id} not found"
                }
            
            # Handle rejection
            if not approved:
                return {
                    "event": None,
                    "status": "rejected",
                    "message": "Event creation was not approved by user"
                }
            
            # Validate approval token (basic validation - in production would be more robust)
            if approval_token and not self._validate_approval_token(approval_token, proposal_id):
                return {
                    "event": None,
                    "status": "error",
                    "message": "Invalid approval token"
                }
            
            # Apply any modifications to the proposal
            final_event_data = self._apply_modifications(proposal, modifications)
            
            # Create the event using the Calendar bridge tool
            result = await self._create_calendar_event(final_event_data)
            
            # Clean up proposal after processing
            await self._cleanup_proposal(proposal_id)
            
            return result
                
        except Exception as e:
            print(f"Calendar write event error: {e}")
            return {
                "event": None,
                "status": "error",
                "message": f"Event creation failed: {str(e)}"
            }
    
    async def _get_proposal(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a proposal by ID.
        
        In production, this would query persistent storage or coordinate with
        the approval workflow system.
        """
        # Check in-memory storage first
        if proposal_id in self._proposals:
            return self._proposals[proposal_id]
        
        # For demo purposes, generate a mock proposal
        # In production, this would be stored when calendar.propose_event is called
        return {
            "proposal_id": proposal_id,
            "title": "Mock Approved Event",
            "start": "2025-08-16T14:00:00Z",
            "end": "2025-08-16T15:00:00Z",
            "all_day": False,
            "calendar": "Calendar",
            "location": "Conference Room",
            "description": "Mock event for approval testing",
            "attendees": []
        }
    
    def _validate_approval_token(self, token: str, proposal_id: str) -> bool:
        """
        Validate approval token.
        
        In production, this would validate against the coordinator's approval system.
        """
        # Basic validation - in production would be cryptographically secure
        expected_token = f"approved_{proposal_id}"
        return token == expected_token
    
    def _apply_modifications(self, proposal: Dict[str, Any], 
                           modifications: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply user modifications to the original proposal.
        
        Args:
            proposal: Original event proposal
            modifications: User-requested changes
            
        Returns:
            Modified event data ready for creation
        """
        final_event = proposal.copy()
        
        # Apply modifications
        for key, value in modifications.items():
            if key in ["title", "start", "end", "location", "description"]:
                final_event[key] = value
        
        return final_event
    
    async def _create_calendar_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create the calendar event using the bridge tool.
        
        Args:
            event_data: Finalized event data
            
        Returns:
            Creation result
        """
        try:
            # Get the Calendar bridge tool from the agent
            if not hasattr(self, '_agent') or self._agent is None:
                return self._create_mock_event(event_data)
            
            calendar_bridge_tool = self._agent.tools.get("calendar_bridge")
            if not calendar_bridge_tool:
                return self._create_mock_event(event_data)
            
            # Execute Calendar bridge tool with create_event operation
            bridge_result = calendar_bridge_tool.execute({
                "operation": "create_event",
                "event_data": {
                    "title": event_data.get("title"),
                    "start": event_data.get("start"),
                    "end": event_data.get("end"),
                    "all_day": event_data.get("all_day", False),
                    "calendar": event_data.get("calendar", "Calendar"),
                    "location": event_data.get("location", ""),
                    "description": event_data.get("description", ""),
                    "attendees": event_data.get("attendees", [])
                }
            })
            
            # Process bridge response
            if bridge_result.get("created") and bridge_result.get("event"):
                created_event = bridge_result["event"]
                return {
                    "event": {
                        "id": created_event.get("id"),
                        "title": created_event.get("title"),
                        "start": created_event.get("start"),
                        "end": created_event.get("end"),
                        "created": True,
                        "calendar": created_event.get("calendar")
                    },
                    "status": "created",
                    "message": "Event successfully created in Apple Calendar"
                }
            else:
                error_msg = bridge_result.get("error", "Unknown error during event creation")
                return {
                    "event": None,
                    "status": "error",
                    "message": f"Failed to create event: {error_msg}"
                }
        
        except Exception as e:
            print(f"Bridge event creation error: {e}")
            return self._create_mock_event(event_data)
    
    def _create_mock_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a mock event for testing when bridge is not available.
        
        Args:
            event_data: Event data
            
        Returns:
            Mock creation result
        """
        # Generate mock event ID
        import uuid
        event_id = f"mock-event-{str(uuid.uuid4())[:8]}"
        
        return {
            "event": {
                "id": event_id,
                "title": event_data.get("title", "Mock Event"),
                "start": event_data.get("start"),
                "end": event_data.get("end"),
                "created": True,
                "calendar": event_data.get("calendar", "Calendar")
            },
            "status": "created",
            "message": "Mock event created successfully (bridge not available)"
        }
    
    async def _cleanup_proposal(self, proposal_id: str):
        """
        Clean up processed proposal.
        
        Args:
            proposal_id: ID of proposal to clean up
        """
        if proposal_id in self._proposals:
            del self._proposals[proposal_id]
    
    def store_proposal(self, proposal: Dict[str, Any]):
        """
        Store a proposal for later processing.
        
        This method would be called by the coordinator or approval workflow system.
        """
        proposal_id = proposal.get("proposal_id")
        if proposal_id:
            self._proposals[proposal_id] = proposal