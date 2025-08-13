"""
Mail Bridge Tool for macOS Bridge integration.

This tool provides access to mail functionality through the macOS Bridge service.
"""

import httpx
from typing import Dict, Any, Optional, List
from kenny_agent.base_tool import BaseTool


class MailBridgeTool(BaseTool):
    """Tool for interacting with macOS Bridge mail endpoints."""
    
    def __init__(self, bridge_url: str = "http://localhost:5100"):
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
        # Normalize common legacy suffix '/bridge'
        norm = bridge_url.rstrip('/')
        if norm.endswith('/bridge'):
            norm = norm[:-len('/bridge')]
        self.bridge_url = norm
    
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
        page = parameters.get("page", 0)
        
        # Build query parameters
        query_params = {
            "mailbox": mailbox,
            "limit": limit,
            "page": page
        }
        if since:
            query_params["since"] = since
        
        try:
            url = f"{self.bridge_url}/v1/mail/messages"
            print(f"[mail_bridge] GET {url} params={query_params}")
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
                    "mailbox": mailbox,
                    "results": messages,
                    "count": len(messages),
                    "total": total,
                    "page": page,
                    "limit": limit
                }
                
        except httpx.RequestError as e:
            print(f"[mail_bridge] RequestError type={type(e)} detail={e}")
            # Fallback: shell out to curl (works reliably on this host)
            try:
                import json as _json
                import shlex, subprocess as _sp
                fallback_base = self.bridge_url.replace('127.0.0.1', 'localhost')
                url = f"{fallback_base}/v1/mail/messages?mailbox={mailbox}&limit={limit}&page={page}"
                cmd = ["curl", "-sS", "--max-time", "8", url]
                print(f"[mail_bridge] fallback curl: {' '.join(shlex.quote(c) for c in cmd)}")
                res = _sp.run(cmd, stdout=_sp.PIPE, stderr=_sp.PIPE, text=True)
                if res.returncode == 0 and res.stdout.strip():
                    data = _json.loads(res.stdout)
                    messages = data if isinstance(data, list) else data.get("messages", [])
                    return {
                        "operation": "list",
                        "mailbox": mailbox,
                        "results": messages,
                        "count": len(messages),
                        "total": len(messages),
                        "page": page,
                        "limit": limit,
                        "_fallback": "curl"
                    }
                else:
                    print(f"[mail_bridge] fallback curl failed rc={res.returncode} err={res.stderr.strip()}")
            except Exception as fe:
                print(f"[mail_bridge] fallback error: {fe}")

            # Final fallback: direct local call to bridge mail_live (no HTTP)
            try:
                import os as _os, sys as _sys
                here = _os.path.abspath(_os.path.dirname(__file__))
                candidates = []
                # Walk up to project root heuristically and test for bridge/mail_live.py
                cursor = here
                for _ in range(8):
                    bridge_dir = _os.path.join(cursor, 'bridge')
                    if _os.path.exists(_os.path.join(bridge_dir, 'mail_live.py')):
                        candidates.append(bridge_dir)
                        break
                    cursor = _os.path.abspath(_os.path.join(cursor, '..'))
                # Also try known relative from services/mail-agent/src/tools → project root
                candidates.append(_os.path.abspath(_os.path.join(here, '..', '..', '..', '..', '..', 'bridge')))
                found = None
                for c in candidates:
                    if _os.path.exists(_os.path.join(c, 'mail_live.py')):
                        found = c
                        break
                if not found:
                    raise RuntimeError('bridge/mail_live.py not found via heuristic search')
                if found not in _sys.path:
                    _sys.path.insert(0, found)
                from mail_live import fetch_mail_messages as _fetch
                print("[mail_bridge] direct import fallback: bridge.mail_live.fetch_mail_messages")
                messages = _fetch(mailbox=mailbox, since_iso=since, limit=limit, page=page)
                return {
                    "operation": "list",
                    "mailbox": mailbox,
                    "results": messages,
                    "count": len(messages),
                    "total": len(messages),
                    "page": page,
                    "limit": limit,
                    "_fallback": "direct"
                }
            except Exception as de:
                print(f"[mail_bridge] direct import fallback failed: {de}")
            return {
                "operation": "list",
                "error": f"Request failed: {str(e)}",
                "mailbox": mailbox
            }
        except httpx.HTTPStatusError as e:
            print(f"[mail_bridge] HTTPStatusError code={e.response.status_code} body={e.response.text}")
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
