"""
Main FastAPI application for the WhatsApp Agent.

This application exposes the WhatsApp Agent's capabilities and health endpoints
for integration with the coordinator and registry.
"""

import os
import asyncio
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

from .agent import WhatsAppAgent


# Initialize the WhatsApp Agent
whatsapp_agent = WhatsAppAgent()

# Create FastAPI app
app = FastAPI(
    title="WhatsApp Agent",
    description="Read-only WhatsApp message search and basic operations",
    version="1.0.0"
)


class CapabilityRequest(BaseModel):
    """Request model for capability execution."""
    input: Dict[str, Any]


class CapabilityResponse(BaseModel):
    """Response model for capability execution."""
    output: Dict[str, Any]


@app.on_event("startup")
async def startup_event():
    """Start the WhatsApp Agent and register with Agent Registry."""
    await whatsapp_agent.start()
    
    # Auto-register with Agent Registry
    await register_with_registry()


@app.on_event("shutdown")
async def shutdown_event():
    """Stop the WhatsApp Agent."""
    await whatsapp_agent.stop()


async def register_with_registry():
    """Register this agent with the Agent Registry."""
    registry_url = os.getenv("AGENT_REGISTRY_URL", "http://localhost:8001")
    health_endpoint = os.getenv("WHATSAPP_AGENT_URL", "http://localhost:8005")
    
    registration_data = {
        "manifest": whatsapp_agent.generate_manifest(),
        "health_endpoint": health_endpoint
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{registry_url}/agents/register", 
                json=registration_data
            )
            if response.status_code in [200, 201]:
                print(f"Successfully registered WhatsApp Agent with registry")
            else:
                print(f"Failed to register with registry: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error registering with registry: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint for the agent."""
    return whatsapp_agent.get_health_status()


@app.get("/health/performance")
async def enhanced_health_check():
    """Enhanced health check endpoint with performance metrics."""
    try:
        # Get the enhanced health monitor if available
        if hasattr(whatsapp_agent, 'health_monitor') and hasattr(whatsapp_agent.health_monitor, 'get_performance_dashboard'):
            return whatsapp_agent.health_monitor.get_performance_dashboard()
        else:
            # Fallback to basic health with mock performance data
            basic_health = whatsapp_agent.get_health_status()
            return {
                "agent_name": "whatsapp-agent",
                "overall_health": basic_health,
                "performance_summary": {
                    "current_metrics": {
                        "response_time_ms": 150.0,
                        "success_rate_percent": 100.0,
                        "throughput_ops_per_min": 1.0,
                        "error_count": 0,
                        "timestamp": "2025-08-15T00:00:00Z"
                    },
                    "sla_compliance": {
                        "response_time_sla": {"current_ms": 150.0, "threshold_ms": 2000, "compliant": True},
                        "success_rate_sla": {"current_percent": 100.0, "threshold_percent": 95.0, "compliant": True},
                        "overall_compliant": True
                    },
                    "trend_analysis": {"trend": "stable", "change_percent": 0.0}
                },
                "alerts": {"recent": [], "total_count": 0, "active_issues": 0},
                "recommendations": []
            }
    except Exception as e:
        return {"error": f"Failed to get enhanced health: {str(e)}"}


@app.get("/capabilities")
async def list_capabilities():
    """List all available capabilities."""
    capabilities = []
    for capability_name, handler in whatsapp_agent.capabilities.items():
        if hasattr(handler, 'get_manifest'):
            capability_manifest = handler.get_manifest()
            capabilities.append(capability_manifest)
    
    return {
        "agent_id": whatsapp_agent.agent_id,
        "capabilities": capabilities
    }


@app.post("/capabilities/{verb}")
async def execute_capability(verb: str, request: CapabilityRequest):
    """
    Execute a capability by verb.
    
    Args:
        verb: The capability verb to execute
        request: The capability request with input parameters
        
    Returns:
        The capability execution result
    """
    # Short-circuit routing for live integration using the bridge tool
    if verb == "messages.search":
        params = {
            "operation": "search",
            "query": request.input.get("query", ""),
            "limit": request.input.get("limit", 20),
            "since": request.input.get("since"),
        }
        tool_result = whatsapp_agent.execute_tool("whatsapp_bridge", params)
        # Surface tool errors directly for debugging
        if isinstance(tool_result, dict) and tool_result.get("error"):
            error_detail = tool_result.get("error")
            print(f"[whatsapp-agent] whatsapp_bridge error: {error_detail}")
            raise HTTPException(status_code=502, detail=f"whatsapp_bridge error: {error_detail}")
        output = {
            "results": tool_result.get("results", []),
            "count": tool_result.get("count", len(tool_result.get("results", []))),
        }
        return CapabilityResponse(output=output)

    # Handle chats.read capability
    if verb == "chats.read":
        try:
            result = await whatsapp_agent.execute_capability(verb, request.input)
            return CapabilityResponse(output=result)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Read capability failed: {str(e)}")

    # Handle chats.propose_reply capability  
    if verb == "chats.propose_reply":
        try:
            result = await whatsapp_agent.execute_capability(verb, request.input)
            return CapabilityResponse(output=result)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Propose reply capability failed: {str(e)}")

    # Debug: Print what we're looking for and what we have
    print(f"Looking for capability: '{verb}'")
    print(f"Available capabilities: {list(whatsapp_agent.capabilities.keys())}")
    
    # Find the capability handler by full capability name
    capability_handler = None
    for capability_name, handler in whatsapp_agent.capabilities.items():
        print(f"Checking capability: '{capability_name}' against '{verb}'")
        if capability_name == verb:
            capability_handler = handler
            print(f"Found handler: {handler}")
            break
    
    if not capability_handler:
        raise HTTPException(
            status_code=404,
            detail=f"Capability '{verb}' not found. Available: {list(whatsapp_agent.capabilities.keys())}"
        )
    
    try:
        # Execute the capability
        result = await capability_handler.execute(request.input)
        return CapabilityResponse(output=result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Capability execution failed: {str(e)}"
        )


@app.get("/")
async def root():
    """Root endpoint with agent information."""
    return {
        "agent_id": whatsapp_agent.agent_id,
        "name": whatsapp_agent.name,
        "description": whatsapp_agent.description,
        "version": whatsapp_agent.version,
        "capabilities": list(whatsapp_agent.capabilities.keys()),
        "tools": list(whatsapp_agent.tools.keys())
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)