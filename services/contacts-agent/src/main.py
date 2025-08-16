"""
Main FastAPI application for the Contacts Agent.

This application provides the HTTP interface for the contacts agent,
including capability endpoints and health monitoring.
"""

import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any

# Add the agent-sdk to the path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "agent-sdk"))

from .kenny_agent.agent import ContactsAgent


# Global agent instance
contacts_agent: ContactsAgent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the application lifecycle."""
    global contacts_agent
    
    # Startup
    print("[contacts-agent] Starting up...")
    
    try:
        # Initialize and start the agent
        contacts_agent = ContactsAgent()
        success = await contacts_agent.start()
        
        if not success:
            print("[contacts-agent] Failed to start agent")
            raise RuntimeError("Failed to start contacts agent")
        
        print("[contacts-agent] Agent started successfully")
        yield
        
    except Exception as e:
        print(f"[contacts-agent] Startup error: {e}")
        raise
    finally:
        # Shutdown
        print("[contacts-agent] Shutting down...")
        
        if contacts_agent:
            await contacts_agent.stop()
        
        print("[contacts-agent] Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Contacts Agent",
    description="Contact management and enrichment agent for Kenny v2",
    version="1.0.0",
    lifespan=lifespan
)


# Request/Response models
class CapabilityRequest(BaseModel):
    input: Dict[str, Any]


class CapabilityResponse(BaseModel):
    output: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if not contacts_agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        # Get health status from agent
        health_status = contacts_agent.get_health_status()
        # Ensure the response includes the timestamp field expected by the registry
        if "last_updated" in health_status:
            health_status["timestamp"] = health_status["last_updated"]
        return health_status
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "unhealthy", "error": str(e)}
        )


# Capability endpoints
@app.post("/capabilities/contacts.resolve", response_model=CapabilityResponse)
async def resolve_contacts(request: CapabilityRequest):
    """Execute the contacts.resolve capability."""
    if not contacts_agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        result = await contacts_agent.execute_capability("contacts.resolve", request.input)
        return CapabilityResponse(
            output=result,
            metadata={
                "capability": "contacts.resolve",
                "agent_id": contacts_agent.agent_id,
                "timestamp": contacts_agent.last_updated.isoformat()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Capability execution failed: {str(e)}")


@app.post("/capabilities/contacts.enrich", response_model=CapabilityResponse)
async def enrich_contacts(request: CapabilityRequest):
    """Execute the contacts.enrich capability."""
    if not contacts_agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        result = await contacts_agent.execute_capability("contacts.enrich", request.input)
        return CapabilityResponse(
            output=result,
            metadata={
                "capability": "contacts.enrich",
                "agent_id": contacts_agent.agent_id,
                "timestamp": contacts_agent.last_updated.isoformat()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Capability execution failed: {str(e)}")


@app.post("/capabilities/contacts.merge", response_model=CapabilityResponse)
async def merge_contacts(request: CapabilityRequest):
    """Execute the contacts.merge capability."""
    if not contacts_agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        result = await contacts_agent.execute_capability("contacts.merge", request.input)
        return CapabilityResponse(
            output=result,
            metadata={
                "capability": "contacts.merge",
                "agent_id": contacts_agent.agent_id,
                "timestamp": contacts_agent.last_updated.isoformat()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Capability execution failed: {str(e)}")


# Agent info endpoint
@app.get("/agent/info")
async def agent_info():
    """Get agent information and manifest."""
    if not contacts_agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        manifest = contacts_agent.generate_manifest()
        return {
            "agent_id": contacts_agent.agent_id,
            "name": contacts_agent.name,
            "description": contacts_agent.description,
            "version": contacts_agent.version,
            "capabilities": list(contacts_agent.capabilities.keys()),
            "manifest": manifest
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent info: {str(e)}")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with basic information."""
    return {
        "service": "Contacts Agent",
        "version": "1.0.0",
        "status": "operational" if contacts_agent else "initializing",
        "capabilities": [
            "contacts.resolve",
            "contacts.enrich", 
            "contacts.merge"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or use default
    port = int(os.getenv("CONTACTS_AGENT_PORT", "8003"))
    
    print(f"[contacts-agent] Starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
