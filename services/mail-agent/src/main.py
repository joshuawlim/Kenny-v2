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
    # Short-circuit routing for live integration using the bridge tool
    if verb == "messages.search":
        params = {
            "operation": "list",
            "mailbox": request.input.get("mailbox", "Inbox"),
            "since": request.input.get("since"),
            "limit": request.input.get("limit", 100),
            "page": request.input.get("page", 0),
        }
        tool_result = mail_agent.execute_tool("mail_bridge", params)
        # Surface tool errors directly for debugging
        if isinstance(tool_result, dict) and tool_result.get("error"):
            error_detail = tool_result.get("error")
            print(f"[mail-agent] mail_bridge error: {error_detail}")
            raise HTTPException(status_code=502, detail=f"mail_bridge error: {error_detail}")
        output = {
            "results": tool_result.get("results", []),
            "count": tool_result.get("count", len(tool_result.get("results", []))),
        }
        return CapabilityResponse(output=output)

    # Debug: Print what we're looking for and what we have
    print(f"Looking for capability: '{verb}'")
    print(f"Available capabilities: {list(mail_agent.capabilities.keys())}")
    
    # Find the capability handler by full capability name
    capability_handler = None
    for capability_name, handler in mail_agent.capabilities.items():
        print(f"Checking capability: '{capability_name}' against '{verb}'")
        if capability_name == verb:
            capability_handler = handler
            print(f"Found handler: {handler}")
            break
    
    if not capability_handler:
        raise HTTPException(
            status_code=404,
            detail=f"Capability '{verb}' not found. Available: {list(mail_agent.capabilities.keys())}"
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
