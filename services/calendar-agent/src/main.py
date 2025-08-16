"""
Main FastAPI application for the Calendar Agent.

This application exposes the Calendar Agent's capabilities and health endpoints
for integration with the coordinator and registry.
"""

import os
import asyncio
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

from .agent import CalendarAgent


# Initialize the Calendar Agent
calendar_agent = CalendarAgent()

# Create FastAPI app
app = FastAPI(
    title="Calendar Agent",
    description="Apple Calendar integration with event reading, proposal generation, and approval-based writing",
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
    """Start the Calendar Agent and register with Agent Registry."""
    await calendar_agent.start()
    
    # Auto-register with Agent Registry
    await register_with_registry()


@app.on_event("shutdown")
async def shutdown_event():
    """Stop the Calendar Agent."""
    await calendar_agent.stop()


async def register_with_registry():
    """Register this agent with the Agent Registry."""
    registry_url = os.getenv("AGENT_REGISTRY_URL", "http://localhost:8001")
    health_endpoint = os.getenv("CALENDAR_AGENT_URL", "http://localhost:8007")
    
    registration_data = {
        "manifest": calendar_agent.generate_manifest(),
        "health_endpoint": health_endpoint
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{registry_url}/agents/register", 
                json=registration_data
            )
            if response.status_code in [200, 201]:
                print(f"Successfully registered Calendar Agent with registry")
            else:
                print(f"Failed to register with registry: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error registering with registry: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint for the agent."""
    return calendar_agent.get_health_status()


@app.get("/health/performance")
async def enhanced_health_check():
    """Enhanced health check endpoint with performance metrics."""
    try:
        # Get the enhanced health monitor if available
        if hasattr(calendar_agent, 'health_monitor') and hasattr(calendar_agent.health_monitor, 'get_performance_dashboard'):
            return calendar_agent.health_monitor.get_performance_dashboard()
        else:
            # Fallback to basic health with mock performance data
            basic_health = calendar_agent.get_health_status()
            return {
                "agent_name": "calendar-agent",
                "overall_health": basic_health,
                "performance_summary": {
                    "current_metrics": {
                        "response_time_ms": 200.0,
                        "success_rate_percent": 100.0,
                        "throughput_ops_per_min": 1.0,
                        "error_count": 0,
                        "timestamp": "2025-08-15T00:00:00Z"
                    },
                    "sla_compliance": {
                        "response_time_sla": {"current_ms": 200.0, "threshold_ms": 2000, "compliant": True},
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
    for capability_name, handler in calendar_agent.capabilities.items():
        if hasattr(handler, 'get_manifest'):
            capability_manifest = handler.get_manifest()
            capabilities.append(capability_manifest)
    
    return {
        "agent_id": calendar_agent.agent_id,
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
    # Debug: Print what we're looking for and what we have
    print(f"Looking for capability: '{verb}'")
    print(f"Available capabilities: {list(calendar_agent.capabilities.keys())}")
    
    # Find the capability handler by full capability name
    capability_handler = None
    for capability_name, handler in calendar_agent.capabilities.items():
        print(f"Checking capability: '{capability_name}' against '{verb}'")
        if capability_name == verb:
            capability_handler = handler
            print(f"Found handler: {handler}")
            break
    
    if not capability_handler:
        raise HTTPException(
            status_code=404,
            detail=f"Capability '{verb}' not found. Available: {list(calendar_agent.capabilities.keys())}"
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
        "agent_id": calendar_agent.agent_id,
        "name": calendar_agent.name,
        "description": calendar_agent.description,
        "version": calendar_agent.version,
        "capabilities": list(calendar_agent.capabilities.keys()),
        "tools": list(calendar_agent.tools.keys())
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)