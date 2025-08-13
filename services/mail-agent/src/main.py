"""
Main FastAPI application for the Mail Agent.

This application exposes the Mail Agent's capabilities and health endpoints
for integration with the coordinator and registry.
"""

import os
import asyncio
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .agent import MailAgent


# Initialize the Mail Agent
mail_agent = MailAgent()

# Create FastAPI app
app = FastAPI(
    title="Mail Agent",
    description="Read-only mail search/read and reply proposals",
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
    """Start the Mail Agent on startup."""
    await mail_agent.start()


@app.on_event("shutdown")
async def shutdown_event():
    """Stop the Mail Agent on shutdown."""
    await mail_agent.stop()


@app.get("/health")
async def health_check():
    """Health check endpoint for the agent."""
    return mail_agent.get_health_status()


@app.get("/capabilities")
async def list_capabilities():
    """List all available capabilities."""
    capabilities = []
    for capability_name, handler in mail_agent.capabilities.items():
        if hasattr(handler, 'get_manifest'):
            capability_manifest = handler.get_manifest()
            capabilities.append(capability_manifest)
    
    return {
        "agent_id": mail_agent.agent_id,
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
    # Find the capability handler by verb
    capability_handler = None
    for handler in mail_agent.capabilities.values():
        if hasattr(handler, 'verb') and handler.verb == verb:
            capability_handler = handler
            break
    
    if not capability_handler:
        raise HTTPException(
            status_code=404,
            detail=f"Capability '{verb}' not found"
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
        "agent_id": mail_agent.agent_id,
        "name": mail_agent.name,
        "description": mail_agent.description,
        "version": mail_agent.version,
        "capabilities": list(mail_agent.capabilities.keys()),
        "tools": list(mail_agent.tools.keys())
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
