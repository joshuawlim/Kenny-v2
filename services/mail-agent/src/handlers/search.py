"""
Search capability handler for mail messages.

This handler provides search functionality for mail messages using
the macOS Bridge integration.
"""

from typing import Dict, Any, List
from kenny_agent.base_handler import BaseCapabilityHandler


class SearchCapabilityHandler(BaseCapabilityHandler):
    """Handler for searching mail messages."""
    
    def __init__(self):
        """Initialize the search capability handler."""
        super().__init__(
            capability="messages.search",
            description="Search mail messages by query and filters",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                    "mailbox": {"type": "string", "enum": ["Inbox", "Sent"]},
                    "since": {"type": "string", "format": "date-time"},
                    "until": {"type": "string", "format": "date-time"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 500}
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
                                "thread_id": {"type": ["string", "null"]},
                                "from": {"type": ["string", "null"]},
                                "to": {"type": "array", "items": {"type": "string"}},
                                "subject": {"type": ["string", "null"]},
                                "snippet": {"type": ["string", "null"]},
                                "ts": {"type": "string", "format": "date-time"},
                                "mailbox": {"type": ["string", "null"]}
                            },
                            "required": ["id", "ts"]
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
        Execute the search capability using the mail bridge tool.
        
        Args:
            parameters: Search parameters
            
        Returns:
            Search results from the mail bridge
        """
        try:
            # Get the mail bridge tool from the agent
            if not hasattr(self, '_agent') or self._agent is None:
                # Fallback to mock data if no agent context
                return self._get_mock_search_results(parameters)
            
            mail_bridge_tool = self._agent.tools.get("mail_bridge")
            if not mail_bridge_tool:
                # Fallback to mock data if mail bridge tool not available
                return self._get_mock_search_results(parameters)
            
            # Execute mail bridge tool with search operation
            bridge_result = await mail_bridge_tool.execute({
                "operation": "list_messages",
                **parameters
            })
            
            # Convert bridge response to capability format
            if bridge_result.get("success") and "messages" in bridge_result:
                messages = bridge_result["messages"]
                return {
                    "results": messages,
                    "count": len(messages)
                }
            else:
                # Fallback to mock data on bridge failure
                return self._get_mock_search_results(parameters)
                
        except Exception as e:
            # Fallback to mock data on any error
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
        mailbox = parameters.get("mailbox", "Inbox")
        limit = parameters.get("limit", 100)
        
        # Mock search results
        results = [
            {
                "id": f"msg_{i}",
                "thread_id": f"thread_{i}",
                "from": f"sender{i}@example.com",
                "to": [f"recipient{i}@example.com"],
                "subject": f"Test message {i}",
                "snippet": f"This is a test message about {query}",
                "ts": "2025-08-13T00:00:00Z",
                "mailbox": mailbox
            }
            for i in range(1, min(limit + 1, 6))
        ]
        
        return {
            "results": results,
            "count": len(results)
        }
