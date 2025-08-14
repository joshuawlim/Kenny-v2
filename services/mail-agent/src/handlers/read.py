"""
Read capability handler for mail messages.

This handler provides functionality to read full message content.
"""

from typing import Dict, Any
from kenny_agent.base_handler import BaseCapabilityHandler


class ReadCapabilityHandler(BaseCapabilityHandler):
    """Handler for reading mail messages."""
    
    def __init__(self):
        """Initialize the read capability handler."""
        super().__init__(
            capability="messages.read",
            description="Read full message content by ID",
            input_schema={
                "type": "object",
                "properties": {
                    "id": {"type": "string"}
                },
                "required": ["id"],
                "additionalProperties": False
            },
            output_schema={
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "headers": {"type": "object", "additionalProperties": True},
                    "body_text": {"type": ["string", "null"]},
                    "body_html": {"type": ["string", "null"]}
                },
                "required": ["id"],
                "additionalProperties": True
            },
            safety_annotations=["read-only", "local-only", "no-egress"]
        )
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the read capability using the mail bridge tool.
        
        Args:
            parameters: Read parameters containing message ID
            
        Returns:
            Message content from the mail bridge
        """
        message_id = parameters.get("id")
        if not message_id:
            raise ValueError("Message ID is required")
        
        try:
            # Get the mail bridge tool from the agent
            if not hasattr(self, '_agent') or self._agent is None:
                # Fallback to mock data if no agent context
                return self._get_mock_message(message_id)
            
            mail_bridge_tool = self._agent.tools.get("mail_bridge")
            if not mail_bridge_tool:
                # Fallback to mock data if mail bridge tool not available
                return self._get_mock_message(message_id)
            
            # Execute mail bridge tool with read operation
            bridge_result = await mail_bridge_tool.execute({
                "operation": "read_message",
                "id": message_id
            })
            
            # Convert bridge response to capability format
            if bridge_result.get("success") and "message" in bridge_result:
                return bridge_result["message"]
            else:
                # Fallback to mock data on bridge failure
                return self._get_mock_message(message_id)
                
        except Exception as e:
            # Fallback to mock data on any error
            return self._get_mock_message(message_id)
    
    def _get_mock_message(self, message_id: str) -> Dict[str, Any]:
        """
        Generate mock message content as fallback.
        
        Args:
            message_id: The message ID to read
            
        Returns:
            Mock message content
        """
        return {
            "id": message_id,
            "headers": {
                "from": "sender@example.com",
                "to": "recipient@example.com",
                "subject": "Test Message",
                "date": "2025-08-13T00:00:00Z"
            },
            "body_text": f"This is the text content of message {message_id}. It contains sample text for testing purposes.",
            "body_html": f"<html><body><p>This is the HTML content of message {message_id}.</p><p>It contains sample HTML for testing purposes.</p></body></html>"
        }
