import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from registry import AgentRegistry
from schemas import (
    AgentRegistration, AgentStatus, CapabilityInfo, 
    HealthCheckResponse, AgentManifest
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global registry instance
registry: AgentRegistry = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global registry
    
    # Startup
    logger.info("Starting Agent Registry Service")
    registry = AgentRegistry()
    logger.info("Agent Registry Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Agent Registry Service")
    if registry:
        # Stop all health monitoring tasks
        for agent_id in list(registry.agents.keys()):
            await registry.unregister_agent(agent_id)
    logger.info("Agent Registry Service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Kenny Agent Registry",
    description="Central service for agent registration and capability discovery",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict to local domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> HealthCheckResponse:
    """Health check endpoint for the registry service"""
    if registry is None:
        return HealthCheckResponse(
            status="starting",
            timestamp="unknown"
        )
    
    try:
        system_health = await registry.get_system_health()
        return HealthCheckResponse(
            status="healthy",
            timestamp=system_health["timestamp"]
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheckResponse(
            status="unhealthy",
            timestamp="unknown"
        )


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Kenny Agent Registry",
        "version": "1.0.0",
        "status": "operational" if registry else "starting",
        "endpoints": {
            "health": "/health",
            "agents": "/agents",
            "capabilities": "/capabilities",
            "system_health": "/system/health",
            "performance_dashboard": "/system/health/dashboard"
        }
    }


@app.post("/agents/register", response_model=AgentStatus, status_code=status.HTTP_201_CREATED)
async def register_agent(registration: AgentRegistration) -> AgentStatus:
    """Register a new agent with the registry"""
    if registry is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registry service is starting up"
        )
    
    try:
        agent_status = await registry.register_agent(registration)
        logger.info(f"Agent {registration.manifest.agent_id} registered successfully")
        return agent_status
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to register agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during agent registration"
        )


@app.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_agent(agent_id: str):
    """Unregister an agent from the registry"""
    if registry is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registry service is starting up"
        )
    
    try:
        success = await registry.unregister_agent(agent_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )
        logger.info(f"Agent {agent_id} unregistered successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unregister agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during agent unregistration"
        )


@app.get("/agents", response_model=list[AgentStatus])
async def list_agents():
    """List all registered agents"""
    if registry is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registry service is starting up"
        )
    
    try:
        agents = await registry.list_agents()
        return agents
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while listing agents"
        )


@app.get("/agents/{agent_id}", response_model=AgentStatus)
async def get_agent(agent_id: str) -> AgentStatus:
    """Get details of a specific agent"""
    if registry is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registry service is starting up"
        )
    
    try:
        agent = await registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )
        return agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving agent"
        )


@app.get("/capabilities", response_model=dict[str, list[CapabilityInfo]])
async def get_capabilities():
    """Get all available capabilities indexed by verb"""
    if registry is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registry service is starting up"
        )
    
    try:
        capabilities = await registry.get_capabilities()
        return capabilities
    except Exception as e:
        logger.error(f"Failed to get capabilities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving capabilities"
        )


@app.get("/capabilities/{verb}", response_model=list[CapabilityInfo])
async def get_capability(verb: str):
    """Get all agents that provide a specific capability"""
    if registry is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registry service is starting up"
        )
    
    try:
        capabilities = await registry.get_capability(verb)
        return capabilities
    except Exception as e:
        logger.error(f"Failed to get capability {verb}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving capability"
        )


@app.get("/capabilities/{verb}/find")
async def find_agents_for_capability(
    verb: str, 
    data_scope: str = None
) -> list[CapabilityInfo]:
    """Find agents that can handle a specific capability and optionally data scope"""
    if registry is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registry service is starting up"
        )
    
    try:
        capabilities = await registry.find_agents_for_capability(verb, data_scope)
        return capabilities
    except Exception as e:
        logger.error(f"Failed to find agents for capability {verb}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while finding agents for capability"
        )


@app.get("/system/health")
async def get_system_health():
    """Get overall system health status"""
    if registry is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registry service is starting up"
        )
    
    try:
        health = await registry.get_system_health()
        return health
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving system health"
        )


@app.get("/system/health/dashboard")
async def get_enhanced_health_dashboard():
    """Get comprehensive health dashboard with performance metrics from all agents"""
    if registry is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registry service is starting up"
        )
    
    try:
        dashboard = await registry.get_enhanced_health_dashboard()
        return dashboard
    except Exception as e:
        logger.error(f"Failed to get enhanced health dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving health dashboard"
        )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
