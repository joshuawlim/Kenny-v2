"""
Agent Registry Client for the Kenny v2 multi-agent system.

This module provides a client for communicating with the agent registry
service, including agent registration and health updates.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import httpx


class AgentRegistryClient:
    """
    Client for communicating with the agent registry service.
    
    This client handles agent registration, health updates, and
    capability discovery with the central agent registry.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        """
        Initialize the registry client.
        
        Args:
            base_url: Base URL of the agent registry service
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        
        # HTTP client configuration
        self.client_config = {
            "timeout": timeout,
            "headers": {
                "Content-Type": "application/json",
                "User-Agent": "Kenny-Agent-SDK/0.1.0"
            }
        }
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the registry service.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            Exception: If the request fails
        """
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(**self.client_config) as client:
                    if method.upper() == "GET":
                        response = await client.get(url, params=params)
                    elif method.upper() == "POST":
                        response = await client.post(url, json=data, params=params)
                    elif method.upper() == "PUT":
                        response = await client.put(url, json=data, params=params)
                    elif method.upper() == "DELETE":
                        response = await client.delete(url, params=params)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")
                    
                    # Check response status
                    if response.status_code >= 400:
                        error_msg = f"Registry request failed: {response.status_code}"
                        try:
                            error_data = response.json()
                            if "detail" in error_data:
                                error_msg += f" - {error_data['detail']}"
                        except:
                            error_msg += f" - {response.text}"
                        
                        raise Exception(error_msg)
                    
                    # Parse response
                    try:
                        return response.json()
                    except:
                        return {"status": "success", "data": response.text}
                        
            except httpx.TimeoutException:
                if attempt == self.max_retries - 1:
                    raise Exception(f"Request timeout after {self.max_retries} attempts")
                await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
                
            except httpx.RequestError as e:
                if attempt == self.max_retries - 1:
                    raise Exception(f"Request failed: {str(e)}")
                await asyncio.sleep(1 * (attempt + 1))
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(1 * (attempt + 1))
        
        raise Exception("Max retries exceeded")
    
    async def register_agent(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register an agent with the registry.
        
        Args:
            manifest: Agent manifest containing capabilities and metadata
            
        Returns:
            Registration response from the registry
        """
        endpoint = "/agents/register"
        return await self._make_request("POST", endpoint, data=manifest)
    
    async def unregister_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Unregister an agent from the registry.
        
        Args:
            agent_id: ID of the agent to unregister
            
        Returns:
            Unregistration response from the registry
        """
        endpoint = f"/agents/{agent_id}"
        return await self._make_request("DELETE", endpoint)
    
    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Get agent details from the registry.
        
        Args:
            agent_id: ID of the agent to retrieve
            
        Returns:
            Agent details from the registry
        """
        endpoint = f"/agents/{agent_id}"
        return await self._make_request("GET", endpoint)
    
    async def list_agents(self) -> Dict[str, Any]:
        """
        List all registered agents.
        
        Returns:
            List of registered agents
        """
        endpoint = "/agents"
        return await self._make_request("GET", endpoint)
    
    async def get_capabilities(self) -> Dict[str, Any]:
        """
        Get all available capabilities from the registry.
        
        Returns:
            List of available capabilities
        """
        endpoint = "/capabilities"
        return await self._make_request("GET", endpoint)
    
    async def get_capability(self, verb: str) -> Dict[str, Any]:
        """
        Get details for a specific capability.
        
        Args:
            verb: Capability verb to retrieve (e.g., 'messages.search')
            
        Returns:
            Capability details from the registry
        """
        endpoint = f"/capabilities/{verb}"
        return await self._make_request("GET", endpoint)
    
    async def update_health(
        self, 
        agent_id: str, 
        health_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update agent health status in the registry.
        
        Args:
            agent_id: ID of the agent
            health_data: Health status information
            
        Returns:
            Health update response from the registry
        """
        endpoint = f"/agents/{agent_id}/health"
        return await self._make_request("POST", endpoint, data=health_data)
    
    async def heartbeat(self, agent_id: str) -> Dict[str, Any]:
        """
        Send a heartbeat to the registry.
        
        Args:
            agent_id: ID of the agent sending the heartbeat
            
        Returns:
            Heartbeat response from the registry
        """
        endpoint = f"/agents/{agent_id}/heartbeat"
        return await self._make_request("POST", endpoint)
    
    async def search_agents(
        self,
        query: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for agents based on criteria.
        
        Args:
            query: Text search query
            capabilities: List of required capabilities
            status: Agent status filter
            
        Returns:
            Search results from the registry
        """
        params = {}
        if query:
            params["q"] = query
        if capabilities:
            params["capabilities"] = ",".join(capabilities)
        if status:
            params["status"] = status
        
        endpoint = "/agents/search"
        return await self._make_request("GET", endpoint, params=params)
    
    async def check_registry_health(self) -> Dict[str, Any]:
        """
        Check the health of the registry service.
        
        Returns:
            Registry health status
        """
        endpoint = "/health"
        return await self._make_request("GET", endpoint)
    
    async def close(self) -> None:
        """
        Close the registry client and clean up resources.
        
        This method should be called when the client is no longer needed.
        """
        # For now, this is a no-op since we create new clients per request
        # In the future, we might want to implement connection pooling
        pass
    
    def __str__(self) -> str:
        """String representation of the registry client."""
        return f"AgentRegistryClient(base_url='{self.base_url}')"
    
    def __repr__(self) -> str:
        """Detailed string representation of the registry client."""
        return (f"AgentRegistryClient(base_url='{self.base_url}', "
                f"timeout={self.timeout}, max_retries={self.max_retries})")
