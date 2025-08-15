"""
WhatsApp Bridge Tool for macOS Bridge integration.

This tool provides access to WhatsApp functionality through the macOS Bridge service.
Note: This is a skeleton implementation for Phase 3 foundation. Image processing capabilities
will be added in future phases following ADR-0019 local-only constraints.
"""

import httpx
from typing import Dict, Any, Optional, List
from kenny_agent.base_tool import BaseTool


class WhatsAppBridgeTool(BaseTool):
    """Tool for interacting with macOS Bridge WhatsApp endpoints."""
    
    def __init__(self, bridge_url: str = "http://localhost:5100"):
        """
        Initialize the WhatsApp bridge tool.
        
        Args:
            bridge_url: URL for the macOS Bridge service
        """
        super().__init__(
            name="whatsapp_bridge",
            description="Access WhatsApp functionality through macOS Bridge",
            category="whatsapp",
            input_schema={
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["search", "list", "read"]},
                    "query": {"type": "string"},
                    "chat_id": {"type": "string"},
                    "contact": {"type": "string"},
                    "since": {"type": "string", "format": "date-time"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                    "message_id": {"type": "string"}
                },
                "required": ["operation"]
            }
        )
        # Normalize common legacy suffix '/bridge'
        norm = bridge_url.rstrip('/')
        if norm.endswith('/bridge'):
            norm = norm[:-len('/bridge')]
        self.bridge_url = norm
    
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the WhatsApp bridge operation.
        
        Args:
            parameters: Operation parameters
            
        Returns:
            Result of the operation
        """
        operation = parameters.get("operation")
        
        if operation == "search":
            return self._search_messages(parameters)
        elif operation == "list":
            return self._list_messages(parameters)
        elif operation == "read":
            return self._read_message(parameters)
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    def _search_messages(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Search WhatsApp messages."""
        query = parameters.get("query", "")
        contact = parameters.get("contact")
        chat_id = parameters.get("chat_id")
        limit = parameters.get("limit", 20)
        since = parameters.get("since")
        
        # Build query parameters
        query_params = {
            "query": query,
            "limit": limit
        }
        if contact:
            query_params["contact"] = contact
        if chat_id:
            query_params["chat_id"] = chat_id
        if since:
            query_params["since"] = since
        
        try:
            # Note: This endpoint doesn't exist yet in the bridge
            # This is a skeleton implementation for the foundation
            url = f"{self.bridge_url}/v1/whatsapp/search"
            print(f"[whatsapp_bridge] GET {url} params={query_params}")
            
            with httpx.Client(trust_env=False, http2=False, timeout=httpx.Timeout(connect=2.0, read=30.0, write=5.0, pool=3.0)) as client:
                response = client.get(url, params=query_params, headers={"Connection": "close"}, follow_redirects=False)
                response.raise_for_status()
                
                data = response.json()
                messages = data.get("messages", []) if isinstance(data, dict) else data
                return {
                    "operation": "search",
                    "query": query,
                    "results": messages,
                    "count": len(messages)
                }
                
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            print(f"[whatsapp_bridge] Error: {e}")
            # Fallback to mock data since WhatsApp bridge isn't implemented yet
            return self._get_mock_messages(parameters)
    
    def _list_messages(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """List recent WhatsApp messages."""
        contact = parameters.get("contact")
        chat_id = parameters.get("chat_id")
        limit = parameters.get("limit", 20)
        since = parameters.get("since")
        
        # Build query parameters
        query_params = {"limit": limit}
        if contact:
            query_params["contact"] = contact
        if chat_id:
            query_params["chat_id"] = chat_id
        if since:
            query_params["since"] = since
        
        try:
            # Note: This endpoint doesn't exist yet in the bridge
            # This is a skeleton implementation for the foundation
            url = f"{self.bridge_url}/v1/whatsapp/messages"
            print(f"[whatsapp_bridge] GET {url} params={query_params}")
            
            with httpx.Client(trust_env=False, http2=False, timeout=httpx.Timeout(connect=2.0, read=30.0, write=5.0, pool=3.0)) as client:
                response = client.get(url, params=query_params, headers={"Connection": "close"}, follow_redirects=False)
                response.raise_for_status()
                
                data = response.json()
                messages = data.get("messages", []) if isinstance(data, dict) else data
                return {
                    "operation": "list",
                    "results": messages,
                    "count": len(messages)
                }
                
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            print(f"[whatsapp_bridge] Error: {e}")
            # Fallback to mock data since WhatsApp bridge isn't implemented yet
            return self._get_mock_messages(parameters)
    
    def _read_message(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Read a specific WhatsApp message by ID."""
        message_id = parameters.get("message_id")
        if not message_id:
            raise ValueError("message_id is required for read operation")
        
        try:
            # Note: This endpoint doesn't exist yet in the bridge
            # This is a skeleton implementation for the foundation
            url = f"{self.bridge_url}/v1/whatsapp/message/{message_id}"
            print(f"[whatsapp_bridge] GET {url}")
            
            with httpx.Client(trust_env=False, http2=False, timeout=httpx.Timeout(connect=2.0, read=30.0, write=5.0, pool=3.0)) as client:
                response = client.get(url, headers={"Connection": "close"}, follow_redirects=False)
                response.raise_for_status()
                
                data = response.json()
                return {
                    "operation": "read",
                    "message_id": message_id,
                    "message": data
                }
                
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            print(f"[whatsapp_bridge] Error: {e}")
            # Fallback to mock message
            return {
                "operation": "read",
                "message_id": message_id,
                "message": {
                    "id": message_id,
                    "chat_id": "mock_chat",
                    "from": "Mock Contact",
                    "content": "This is a mock WhatsApp message",
                    "timestamp": "2025-08-15T10:00:00Z",
                    "message_type": "text",
                    "has_media": False
                }
            }
    
    def _get_mock_messages(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock WhatsApp messages for testing foundation."""
        query = parameters.get("query", "")
        contact = parameters.get("contact", "Mock Contact")
        limit = parameters.get("limit", 20)
        
        messages = [
            {
                "id": f"whatsapp_mock_{i}",
                "chat_id": f"chat_{contact.replace(' ', '_').lower()}",
                "from": contact if i % 2 == 0 else "Me",
                "to": "Me" if i % 2 == 0 else contact,
                "content": f"Mock WhatsApp message {i}: {query}" if query else f"Mock WhatsApp message {i}",
                "timestamp": "2025-08-15T10:00:00Z",
                "message_type": "text",
                "has_media": False
            }
            for i in range(1, min(limit + 1, 6))
        ]
        
        return {
            "operation": parameters.get("operation", "search"),
            "results": messages,
            "count": len(messages),
            "_mock": True
        }