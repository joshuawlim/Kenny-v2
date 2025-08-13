"""
Mail Bridge Tool for macOS Bridge integration.

This tool provides access to mail functionality through the macOS Bridge service.
"""

import httpx
from typing import Dict, Any, Optional, List
from kenny_agent.base_tool import BaseTool


class MailBridgeTool(BaseTool):
    """Tool for interacting with macOS Bridge mail endpoints."""
    
    def __init__(self, bridge_url: str = "http://kenny.local/bridge"):
        """
        Initialize the mail bridge tool.
        
        Args:
            bridge_url: URL for the macOS Bridge service
        """
        super().__init__(
            name="mail_bridge",
            description="Access mail functionality through macOS Bridge",
            category="mail",
            input_schema={
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["list", "read"]},
                    "mailbox": {"type": "string", "enum": ["Inbox", "Sent"]},
                    "since": {"type": "string", "format": "date-time"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 500},
                    "page": {"type": "integer", "minimum": 1},
                    "message_id": {"type": "string"}
                },
                "required": ["operation"]
            }
        )
        self.bridge_url = bridge_url.rstrip('/')
    
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the mail bridge operation.
        
        Args:
            parameters: Operation parameters
            
        Returns:
            Result of the operation
        """
        operation = parameters.get("operation")
        
        if operation == "list":
            return self._list_messages(parameters)
        elif operation == "read":
            return self._read_message(parameters)
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    def _list_messages(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """List messages from a mailbox."""
        mailbox = parameters.get("mailbox", "Inbox")
        since = parameters.get("since")
        limit = parameters.get("limit", 100)
        page = parameters.get("page", 1)
        
        # Build query parameters
        query_params = {
            "mailbox": mailbox,
            "limit": limit,
            "page": page
        }
        if since:
            query_params["since"] = since
        
        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{self.bridge_url}/v1/mail/messages",
                    params=query_params,
                    timeout=30.0
                )
                response.raise_for_status()
                
                data = response.json()
                return {
                    "operation": "list",
                    "mailbox": mailbox,
                    "results": data.get("messages", []),
                    "count": len(data.get("messages", [])),
                    "total": data.get("total", 0),
                    "page": page,
                    "limit": limit
                }
                
        except httpx.RequestError as e:
            return {
                "operation": "list",
                "error": f"Request failed: {str(e)}",
                "mailbox": mailbox
            }
        except httpx.HTTPStatusError as e:
            return {
                "operation": "list",
                "error": f"HTTP error {e.response.status_code}: {e.response.text}",
                "mailbox": mailbox
            }
    
    def _read_message(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Read a specific message by ID."""
        message_id = parameters.get("message_id")
        if not message_id:
            raise ValueError("message_id is required for read operation")
        
        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{self.bridge_url}/v1/mail/message/{message_id}",
                    timeout=30.0
                )
                response.raise_for_status()
                
                data = response.json()
                return {
                    "operation": "read",
                    "message_id": message_id,
                    "message": data
                }
                
        except httpx.RequestError as e:
            return {
                "operation": "read",
                "error": f"Request failed: {str(e)}",
                "message_id": message_id
            }
        except httpx.HTTPStatusError as e:
            return {
                "operation": "read",
                "error": f"HTTP error {e.response.status_code}: {e.response.text}",
                "message_id": message_id
            }
