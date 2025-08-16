"""
Calendar Bridge Tool for macOS Bridge integration.

This tool provides access to Apple Calendar functionality through the macOS Bridge service.
"""

import httpx
import time
import hashlib
from typing import Dict, Any, Optional, List
from kenny_agent.base_tool import BaseTool


class CalendarBridgeTool(BaseTool):
    """Tool for interacting with macOS Bridge Calendar endpoints."""
    
    def __init__(self, bridge_url: str = "http://localhost:5100"):
        """
        Initialize the Calendar bridge tool.
        
        Args:
            bridge_url: URL for the macOS Bridge service
        """
        super().__init__(
            name="calendar_bridge",
            description="Access Apple Calendar functionality through macOS Bridge",
            category="calendar",
            input_schema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string", 
                        "enum": ["list_calendars", "list_events", "get_event", "create_event", "health"]
                    },
                    "calendar_name": {"type": "string"},
                    "start_date": {"type": "string", "format": "date-time"},
                    "end_date": {"type": "string", "format": "date-time"},
                    "event_id": {"type": "string"},
                    "event_data": {"type": "object"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 500}
                },
                "required": ["operation"]
            }
        )
        # Normalize common legacy suffix '/bridge'
        norm = bridge_url.rstrip('/')
        if norm.endswith('/bridge'):
            norm = norm[:-len('/bridge')]
        self.bridge_url = norm
        
        # Performance optimizations: Simple in-memory cache
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes cache TTL for calendar data
        self._calendar_list_cache_ttl = 3600  # 1 hour cache for calendar list (changes rarely)
    
    def _cache_key(self, operation: str, **params) -> str:
        """Generate cache key for operation and parameters."""
        # Sort params for consistent keys
        sorted_params = sorted(params.items())
        key_data = f"{operation}:{sorted_params}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cached(self, cache_key: str, ttl: int) -> Optional[Dict[str, Any]]:
        """Get cached result if not expired."""
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < ttl:
                return cached_data
            else:
                # Remove expired cache entry
                del self._cache[cache_key]
        return None
    
    def _set_cache(self, cache_key: str, data: Dict[str, Any]):
        """Set cache entry with current timestamp."""
        self._cache[cache_key] = (data, time.time())
        
        # Simple cache cleanup: remove old entries if cache gets too large
        if len(self._cache) > 100:
            current_time = time.time()
            expired_keys = [
                key for key, (_, timestamp) in self._cache.items()
                if current_time - timestamp > self._cache_ttl
            ]
            for key in expired_keys:
                del self._cache[key]
    
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the Calendar bridge operation.
        
        Args:
            parameters: Operation parameters
            
        Returns:
            Result of the operation
        """
        operation = parameters.get("operation")
        
        if operation == "list_calendars":
            return self._list_calendars(parameters)
        elif operation == "list_events":
            return self._list_events(parameters)
        elif operation == "get_event":
            return self._get_event(parameters)
        elif operation == "create_event":
            return self._create_event(parameters)
        elif operation == "health":
            return self._health_check()
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    def _list_calendars(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """List available calendars with caching."""
        cache_key = "list_calendars"
        
        # Check cache first (longer TTL for calendar list since it changes rarely)
        cached_result = self._get_cached(cache_key, self._calendar_list_cache_ttl)
        if cached_result:
            print(f"[calendar_bridge] Cache hit for list_calendars")
            cached_result["cached"] = True
            return cached_result
        
        try:
            url = f"{self.bridge_url}/v1/calendar/calendars"
            print(f"[calendar_bridge] GET {url}")
            
            start_time = time.time()
            with httpx.Client(trust_env=False, timeout=10.0) as client:  # Reduced timeout
                response = client.get(url, headers={"Connection": "close"}, follow_redirects=False)
                response.raise_for_status()
                
                data = response.json()
                request_time = time.time() - start_time
                
                # Accept either {calendars: [...]} or a raw list
                if isinstance(data, list):
                    calendars = data
                else:
                    calendars = data.get("calendars", [])
                
                result = {
                    "operation": "list_calendars",
                    "calendars": calendars,
                    "count": len(calendars),
                    "request_time": round(request_time, 3),
                    "cached": False
                }
                
                # Cache the result
                self._set_cache(cache_key, result)
                print(f"[calendar_bridge] Cached result for list_calendars (took {request_time:.3f}s)")
                
                return result
                
        except httpx.RequestError as e:
            print(f"[calendar_bridge] RequestError type={type(e)} detail={e}")
            return {
                "operation": "list_calendars",
                "error": f"Request failed: {str(e)}",
                "calendars": [],
                "cached": False
            }
        except httpx.HTTPStatusError as e:
            print(f"[calendar_bridge] HTTPStatusError code={e.response.status_code} body={e.response.text}")
            return {
                "operation": "list_calendars",
                "error": f"HTTP error {e.response.status_code}: {e.response.text}",
                "calendars": [],
                "cached": False
            }
    
    def _list_events(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """List events from calendars with caching for performance."""
        calendar_name = parameters.get("calendar_name")
        start_date = parameters.get("start_date")
        end_date = parameters.get("end_date")
        limit = parameters.get("limit", 100)
        
        # Create cache key for this request
        cache_key = self._cache_key("list_events", 
                                   calendar=calendar_name or "", 
                                   start=start_date or "", 
                                   end=end_date or "", 
                                   limit=limit)
        
        # Check cache first
        cached_result = self._get_cached(cache_key, self._cache_ttl)
        if cached_result:
            print(f"[calendar_bridge] Cache hit for list_events: {cache_key}")
            cached_result["cached"] = True
            return cached_result
        
        # Build query parameters
        query_params = {
            "limit": limit
        }
        if calendar_name:
            query_params["calendar"] = calendar_name
        if start_date:
            query_params["start"] = start_date
        if end_date:
            query_params["end"] = end_date
        
        try:
            url = f"{self.bridge_url}/v1/calendar/events"
            print(f"[calendar_bridge] GET {url} params={query_params}")
            
            # Reduced timeout for better responsiveness (was 45s, now 15s)
            start_time = time.time()
            with httpx.Client(trust_env=False, timeout=15.0) as client:
                response = client.get(url, params=query_params, headers={"Connection": "close"}, follow_redirects=False)
                response.raise_for_status()
                
                data = response.json()
                request_time = time.time() - start_time
                
                # Accept either {events: [...]} or a raw list
                if isinstance(data, list):
                    events = data
                    total = len(events)
                else:
                    events = data.get("events", [])
                    total = data.get("total", len(events))
                
                result = {
                    "operation": "list_events",
                    "events": events,
                    "count": len(events),
                    "total": total,
                    "calendar": calendar_name,
                    "date_range": {
                        "start": start_date,
                        "end": end_date
                    },
                    "request_time": round(request_time, 3),
                    "cached": False
                }
                
                # Cache successful results for future requests
                self._set_cache(cache_key, result)
                print(f"[calendar_bridge] Cached result for list_events: {cache_key} (took {request_time:.3f}s)")
                
                return result
                
        except httpx.RequestError as e:
            print(f"[calendar_bridge] RequestError type={type(e)} detail={e}")
            return {
                "operation": "list_events",
                "error": f"Request failed: {str(e)}",
                "events": [],
                "cached": False
            }
        except httpx.HTTPStatusError as e:
            print(f"[calendar_bridge] HTTPStatusError code={e.response.status_code} body={e.response.text}")
            return {
                "operation": "list_events",
                "error": f"HTTP error {e.response.status_code}: {e.response.text}",
                "events": [],
                "cached": False
            }
        except httpx.TimeoutException as e:
            print(f"[calendar_bridge] TimeoutException: {e}")
            return {
                "operation": "list_events",
                "error": f"Request timed out after 15 seconds: {str(e)}",
                "events": [],
                "cached": False
            }
    
    def _get_event(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific event by ID."""
        event_id = parameters.get("event_id")
        if not event_id:
            raise ValueError("event_id is required for get_event operation")
        
        try:
            url = f"{self.bridge_url}/v1/calendar/event/{event_id}"
            print(f"[calendar_bridge] GET {url}")
            
            with httpx.Client(trust_env=False, timeout=30.0) as client:
                response = client.get(url, headers={"Connection": "close"})
                response.raise_for_status()
                
                data = response.json()
                return {
                    "operation": "get_event",
                    "event_id": event_id,
                    "event": data
                }
                
        except httpx.RequestError as e:
            return {
                "operation": "get_event",
                "error": f"Request failed: {str(e)}",
                "event_id": event_id
            }
        except httpx.HTTPStatusError as e:
            return {
                "operation": "get_event",
                "error": f"HTTP error {e.response.status_code}: {e.response.text}",
                "event_id": event_id
            }
    
    def _create_event(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new calendar event."""
        event_data = parameters.get("event_data")
        if not event_data:
            raise ValueError("event_data is required for create_event operation")
        
        try:
            url = f"{self.bridge_url}/v1/calendar/events"
            print(f"[calendar_bridge] POST {url}")
            
            with httpx.Client(trust_env=False, timeout=30.0) as client:
                response = client.post(
                    url,
                    json=event_data,
                    headers={"Connection": "close", "Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                data = response.json()
                return {
                    "operation": "create_event",
                    "event": data,
                    "created": True
                }
                
        except httpx.RequestError as e:
            return {
                "operation": "create_event",
                "error": f"Request failed: {str(e)}",
                "created": False
            }
        except httpx.HTTPStatusError as e:
            return {
                "operation": "create_event",
                "error": f"HTTP error {e.response.status_code}: {e.response.text}",
                "created": False
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