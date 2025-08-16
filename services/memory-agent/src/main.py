"""
Memory Agent FastAPI application.

Main entry point for the Memory Agent service providing memory storage,
retrieval, and semantic search capabilities.
"""

import os
import sys
from pathlib import Path

# Add the agent-sdk to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "agent-sdk"))

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import logging
import asyncio

from .kenny_agent.agent import MemoryAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Kenny Memory Agent",
    description="Memory storage, retrieval, and semantic search agent for Kenny v2",
    version="1.0.0"
)

# Global agent instance
memory_agent: Optional[MemoryAgent] = None


# Pydantic models for API requests
class CapabilityRequest(BaseModel):
    """Base model for capability requests."""
    input: Dict[str, Any] = Field(..., description="Input parameters for the capability")


class MemoryRetrieveRequest(BaseModel):
    """Request model for memory.retrieve capability."""
    input: Dict[str, Any] = Field(
        ..., 
        description="Search parameters",
        example={
            "query": "project meeting notes",
            "limit": 10,
            "similarity_threshold": 0.7,
            "data_scopes": ["mail", "calendar"]
        }
    )


class MemoryEmbedRequest(BaseModel):
    """Request model for memory.embed capability."""
    input: Dict[str, Any] = Field(
        ...,
        description="Embedding parameters",
        example={
            "texts": ["Hello world", "Machine learning"],
            "model": "nomic-embed-text",
            "normalize": True
        }
    )


class MemoryStoreRequest(BaseModel):
    """Request model for memory.store capability."""
    input: Dict[str, Any] = Field(
        ...,
        description="Storage parameters",
        example={
            "content": "Meeting notes from project discussion",
            "metadata": {
                "source": "calendar",
                "data_scope": "calendar:events",
                "tags": ["meeting", "project"],
                "importance": 0.8
            },
            "auto_embed": True
        }
    )


@app.on_event("startup")
async def startup_event():
    """Initialize the memory agent on startup."""
    global memory_agent
    
    try:
        logger.info("Starting Memory Agent...")
        memory_agent = MemoryAgent()
        
        success = await memory_agent.start()
        if not success:
            logger.error("Failed to start Memory Agent")
            raise RuntimeError("Memory Agent startup failed")
        
        logger.info("Memory Agent started successfully")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup the memory agent on shutdown."""
    global memory_agent
    
    if memory_agent:
        logger.info("Stopping Memory Agent...")
        await memory_agent.stop()
        logger.info("Memory Agent stopped")


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Kenny Memory Agent",
        "version": "1.0.0",
        "status": "running" if memory_agent and memory_agent.is_running else "stopped",
        "capabilities": [
            "memory.retrieve",
            "memory.embed", 
            "memory.store"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if not memory_agent:
        raise HTTPException(status_code=503, detail="Memory Agent not initialized")
    
    # Get health status from agent
    health_status = memory_agent.get_health_status()
    
    if health_status.get("status") == "healthy":
        return health_status
    else:
        raise HTTPException(status_code=503, detail=health_status)


@app.get("/capabilities")
async def list_capabilities():
    """List all available capabilities."""
    if not memory_agent:
        raise HTTPException(status_code=503, detail="Memory Agent not initialized")
    
    return {
        "capabilities": memory_agent.get_capabilities()
    }


@app.get("/capabilities/{capability_name}")
async def get_capability_info(capability_name: str):
    """Get detailed information about a specific capability."""
    if not memory_agent:
        raise HTTPException(status_code=503, detail="Memory Agent not initialized")
    
    capability_info = memory_agent.get_capability_info(capability_name)
    if not capability_info:
        raise HTTPException(status_code=404, detail=f"Capability '{capability_name}' not found")
    
    return capability_info


@app.post("/capabilities/memory.retrieve")
async def memory_retrieve(request: MemoryRetrieveRequest):
    """Execute memory.retrieve capability - semantic search across stored memories."""
    if not memory_agent:
        raise HTTPException(status_code=503, detail="Memory Agent not initialized")
    
    try:
        result = await memory_agent.execute_capability("memory.retrieve", request.input)
        return result
    except Exception as e:
        logger.error(f"Error in memory.retrieve: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/capabilities/memory.embed")
async def memory_embed(request: MemoryEmbedRequest):
    """Execute memory.embed capability - generate embeddings for text."""
    if not memory_agent:
        raise HTTPException(status_code=503, detail="Memory Agent not initialized")
    
    try:
        result = await memory_agent.execute_capability("memory.embed", request.input)
        return result
    except Exception as e:
        logger.error(f"Error in memory.embed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/capabilities/memory.store")
async def memory_store(request: MemoryStoreRequest):
    """Execute memory.store capability - store new memories with metadata."""
    if not memory_agent:
        raise HTTPException(status_code=503, detail="Memory Agent not initialized")
    
    try:
        result = await memory_agent.execute_capability("memory.store", request.input)
        return result
    except Exception as e:
        logger.error(f"Error in memory.store: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Get memory agent statistics."""
    if not memory_agent:
        raise HTTPException(status_code=503, detail="Memory Agent not initialized")
    
    try:
        # Get stats from ChromaDB tool
        chroma_tool = memory_agent.tools.get("chroma_client")
        stats = {}
        
        if chroma_tool:
            stats = chroma_tool.get_collection_stats()
        
        # Add agent-level stats
        stats.update({
            "agent_status": "running" if memory_agent.is_running else "stopped",
            "capabilities_count": len(memory_agent.capabilities),
            "tools_count": len(memory_agent.tools)
        })
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment variable
    port = int(os.environ.get("MEMORY_AGENT_PORT", 8004))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )