"""
iMessage Bridge Tool for macOS Bridge integration.

This tool provides access to iMessage functionality through the macOS Bridge service.
"""

import httpx
from typing import Dict, Any, Optional, List
from kenny_agent.base_tool import BaseTool


class iMessageBridgeTool(BaseTool):
    """Tool for interacting with macOS Bridge iMessage endpoints."""
    
    def __init__(self, bridge_url: str = "http://localhost:5100"):
        """
        Initialize the iMessage bridge tool.
        
        Args:
            bridge_url: URL for the macOS Bridge service
        """
        super().__init__(
            name="imessage_bridge",
            description="Access iMessage functionality through macOS Bridge",
            category="imessage",
            input_schema={
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["list", "read", "search", "health"]},
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 500},
                    "page": {"type": "integer", "minimum": 1},
                    "thread_id": {"type": "string"},
                    "message_id": {"type": "string"},
                    "context": {"type": "string"}
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
        Execute the iMessage bridge operation.
        
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
        elif operation == "search":
            return self._search_messages(parameters)
        elif operation == "health":
            return self._health_check()
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    def _list_messages(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """List recent iMessages."""
        limit = parameters.get("limit", 100)
        page = parameters.get("page", 0)
        
        # Build query parameters
        query_params = {
            "limit": limit,
            "page": page
        }
        
        try:
            url = f"{self.bridge_url}/v1/messages/imessage"
            print(f"[imessage_bridge] GET {url} params={query_params}")
            # Disable env proxy settings; allow longer read timeout for slow JXA
            with httpx.Client(trust_env=False, http2=False, timeout=httpx.Timeout(connect=2.0, read=65.0, write=5.0, pool=3.0)) as client:
                response = client.get(url, params=query_params, headers={"Connection": "close"}, follow_redirects=False)
                response.raise_for_status()
                
                data = response.json()
                # Accept either {messages: [...]} or a raw list
                if isinstance(data, list):
                    messages = data
                    total = len(messages)
                else:
                    messages = data.get("messages", [])
                    total = data.get("total", len(messages))
                
                return {
                    "operation": "list",
                    "results": messages,
                    "count": len(messages),
                    "total": total,
                    "page": page,
                    "limit": limit
                }
                
        except httpx.RequestError as e:
            print(f"[imessage_bridge] RequestError type={type(e)} detail={e}")
            # Fallback: shell out to curl (works reliably on this host)
            try:
                import json as _json
                import shlex, subprocess as _sp
                fallback_base = self.bridge_url.replace('127.0.0.1', 'localhost')
                url = f"{fallback_base}/v1/messages/imessage?limit={limit}&page={page}"
                cmd = ["curl", "-sS", "--max-time", "8", url]
                print(f"[imessage_bridge] fallback curl: {' '.join(shlex.quote(c) for c in cmd)}")
                res = _sp.run(cmd, stdout=_sp.PIPE, stderr=_sp.PIPE, text=True)
                if res.returncode == 0 and res.stdout.strip():
                    data = _json.loads(res.stdout)
                    messages = data if isinstance(data, list) else data.get("messages", [])
                    return {
                        "operation": "list",
                        "results": messages,
                        "count": len(messages),
                        "total": len(messages),
                        "page": page,
                        "limit": limit,
                        "_fallback": "curl"
                    }
                else:
                    print(f"[imessage_bridge] fallback curl failed rc={res.returncode} err={res.stderr.strip()}")
            except Exception as fe:
                print(f"[imessage_bridge] fallback error: {fe}")

            return {
                "operation": "list",
                "error": f"Request failed: {str(e)}"
            }
        except httpx.HTTPStatusError as e:
            print(f"[imessage_bridge] HTTPStatusError code={e.response.status_code} body={e.response.text}")
            return {
                "operation": "list",
                "error": f"HTTP error {e.response.status_code}: {e.response.text}"
            }
    
    def _read_message(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Read a specific message or thread by ID."""
        message_id = parameters.get("message_id")
        thread_id = parameters.get("thread_id")
        
        if not message_id and not thread_id:
            raise ValueError("Either message_id or thread_id is required for read operation")
        
        try:
            if message_id:
                endpoint = f"/v1/messages/imessage/{message_id}"
            else:
                endpoint = f"/v1/messages/imessage/thread/{thread_id}"
            
            with httpx.Client(trust_env=False, timeout=30.0) as client:
                response = client.get(
                    f"{self.bridge_url}{endpoint}",
                    headers={"Connection": "close"}
                )
                response.raise_for_status()
                
                data = response.json()
                return {
                    "operation": "read",
                    "message_id": message_id,
                    "thread_id": thread_id,
                    "result": data
                }
                
        except httpx.RequestError as e:
            return {
                "operation": "read",
                "error": f"Request failed: {str(e)}",
                "message_id": message_id,
                "thread_id": thread_id
            }
        except httpx.HTTPStatusError as e:
            return {
                "operation": "read",
                "error": f"HTTP error {e.response.status_code}: {e.response.text}",
                "message_id": message_id,
                "thread_id": thread_id
            }
    
    def _search_messages(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Search iMessages by query."""
        query = parameters.get("query")
        if not query:
            raise ValueError("query is required for search operation")
        
        limit = parameters.get("limit", 50)
        context = parameters.get("context", "")
        
        # Build query parameters
        query_params = {
            "q": query,
            "limit": limit
        }
        if context:
            query_params["context"] = context
        
        try:
            url = f"{self.bridge_url}/v1/messages/imessage/search"
            print(f"[imessage_bridge] GET {url} params={query_params}")
            with httpx.Client(trust_env=False, http2=False, timeout=httpx.Timeout(connect=2.0, read=45.0, write=5.0, pool=3.0)) as client:
                response = client.get(url, params=query_params, headers={"Connection": "close"}, follow_redirects=False)
                response.raise_for_status()
                
                data = response.json()
                # Accept either {results: [...]} or a raw list
                if isinstance(data, list):
                    results = data
                    total = len(results)
                else:
                    results = data.get("results", data.get("messages", []))
                    total = data.get("total", len(results))
                
                return {
                    "operation": "search",
                    "query": query,
                    "results": results,
                    "count": len(results),
                    "total": total,
                    "limit": limit
                }
                
        except httpx.RequestError as e:
            print(f"[imessage_bridge] RequestError type={type(e)} detail={e}")
            return {
                "operation": "search",
                "query": query,
                "error": f"Request failed: {str(e)}"
            }
        except httpx.HTTPStatusError as e:
            print(f"[imessage_bridge] HTTPStatusError code={e.response.status_code} body={e.response.text}")
            return {
                "operation": "search",
                "query": query,
                "error": f"HTTP error {e.response.status_code}: {e.response.text}"
            }
    
    def _health_check(self) -> Dict[str, Any]:
        """Check bridge connectivity and health."""
        try:
            with httpx.Client(trust_env=False, timeout=10.0) as client:
                response = client.get(
                    f"{self.bridge_url}/health",
                    headers={"Connection": "close"}
                )
                response.raise_for_status()
                
                return {
                    "operation": "health",
                    "status": "ok",
                    "bridge_url": self.bridge_url
                }
                
        except Exception as e:
            return {
                "operation": "health",
                "status": "error",
                "error": str(e),
                "bridge_url": self.bridge_url
            }