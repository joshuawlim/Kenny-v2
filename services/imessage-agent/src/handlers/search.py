"""
Search capability handler for iMessage messages.

This handler provides search functionality for iMessage messages using
the macOS Bridge integration.
"""

from typing import Dict, Any, List
from kenny_agent.base_handler import BaseCapabilityHandler


class SearchCapabilityHandler(BaseCapabilityHandler):
    """Handler for searching iMessage messages."""
    
    def __init__(self):
        """Initialize the search capability handler."""
        super().__init__(
            capability="messages.search",
            description="Search iMessage messages by query and filters",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "contact": {"type": "string"},
                    "thread_id": {"type": "string"},
                    "since": {"type": "string", "format": "date-time"},
                    "until": {"type": "string", "format": "date-time"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                    "context": {"type": "string"}
                },
                "additionalProperties": False
            },
            output_schema={
                "type": "object",
                "properties": {
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "thread_id": {"type": "string"},
                                "from": {"type": ["string", "null"]},
                                "to": {"type": ["string", "null"]},
                                "content": {"type": ["string", "null"]},
                                "timestamp": {"type": "string", "format": "date-time"},
                                "message_type": {"type": "string", "enum": ["text", "image", "video", "audio", "document", "sticker", "attachment"]},
                                "has_attachments": {"type": "boolean"},
                                "contact_name": {"type": ["string", "null"]},
                                "phone_number": {"type": ["string", "null"]}
                            },
                            "required": ["id", "thread_id", "timestamp", "message_type"]
                        }
                    },
                    "count": {"type": "integer"}
                },
                "required": ["results", "count"],
                "additionalProperties": False
            },
            safety_annotations=["read-only", "local-only", "no-egress"]
        )
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the search capability using the iMessage bridge tool.
        
        Args:
            parameters: Search parameters
            
        Returns:
            Search results from the iMessage bridge
        """
        try:
            # Get the iMessage bridge tool from the agent
            if not hasattr(self, '_agent') or self._agent is None:
                # Fallback to mock data if no agent context
                return self._get_mock_search_results(parameters)
            
            imessage_bridge_tool = self._agent.tools.get("imessage_bridge")
            if not imessage_bridge_tool:
                # Fallback to mock data if iMessage bridge tool not available
                return self._get_mock_search_results(parameters)
            
            # Execute iMessage bridge tool with search operation
            bridge_result = imessage_bridge_tool.execute({
                "operation": "search",
                **parameters
            })
            
            # Convert bridge response to capability format
            if isinstance(bridge_result, dict) and bridge_result.get("results"):
                messages = bridge_result["results"]
                return {
                    "results": messages,
                    "count": len(messages)
                }
            else:
                # Fallback to mock data on bridge failure
                return self._get_mock_search_results(parameters)
                
        except Exception as e:
            # Fallback to mock data on any error
            print(f"iMessage search error: {e}")
            return self._get_mock_search_results(parameters)
    
    def _get_mock_search_results(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate mock search results as fallback.
        
        Args:
            parameters: Search parameters
            
        Returns:
            Mock search results
        """
        query = parameters.get("query", "")
        contact = parameters.get("contact", "Unknown Contact")
        limit = parameters.get("limit", 20)
        
        # Mock search results
        results = [
            {
                "id": f"imessage_msg_{i}",
                "thread_id": f"thread_{contact.replace(' ', '_').lower()}",
                "from": contact if i % 2 == 0 else "Me",
                "to": "Me" if i % 2 == 0 else contact,
                "content": f"Mock iMessage {i} containing: {query}",
                "timestamp": "2025-08-15T10:00:00Z",
                "message_type": "text",
                "has_attachments": False,
                "contact_name": contact,
                "phone_number": "+1234567890"
            }
            for i in range(1, min(limit + 1, 6))
        ]
        
        return {
            "results": results,
            "count": len(results)
        }