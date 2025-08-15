from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
from typing import Dict, Any, List, Optional
import asyncio
import logging
import json

from gateway import KennyGateway
from routing import IntentClassifier
from schemas import QueryRequest, QueryResponse, AgentRequest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Kenny v2 Gateway",
    description="User-facing API gateway for multi-agent orchestration",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize gateway components
gateway = KennyGateway()
intent_classifier = IntentClassifier()

@app.on_event("startup")
async def startup_event():
    """Initialize gateway on startup"""
    await gateway.initialize()
    logger.info("Kenny v2 Gateway started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup gateway on shutdown"""
    await gateway.cleanup()
    logger.info("Kenny v2 Gateway shutdown completed")

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Gateway health check with agent summary"""
    try:
        system_health = await gateway.get_system_health()
        return {
            "status": "healthy",
            "service": "gateway",
            "version": "1.0.0",
            "timestamp": asyncio.get_event_loop().time(),
            "system": system_health
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Gateway unhealthy")

@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint"""
    return {"message": "Kenny v2 Gateway - Your Personal Assistant API"}

@app.get("/capabilities")
async def get_all_capabilities() -> Dict[str, Any]:
    """Get all available capabilities across agents"""
    try:
        capabilities = await gateway.get_all_capabilities()
        return {
            "status": "success",
            "capabilities": capabilities,
            "total_count": len(capabilities)
        }
    except Exception as e:
        logger.error(f"Error getting capabilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agents")
async def get_agents() -> Dict[str, Any]:
    """Get agent registry status"""
    try:
        agents = await gateway.get_agents()
        return {
            "status": "success", 
            "agents": agents,
            "total_count": len(agents)
        }
    except Exception as e:
        logger.error(f"Error getting agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def unified_query(request: QueryRequest) -> QueryResponse:
    """Unified query endpoint with intelligent routing"""
    try:
        # Classify intent to determine routing
        routing_decision = await intent_classifier.classify_intent(request.query)
        
        if routing_decision.route == "direct":
            # Direct agent routing
            result = await gateway.call_agent_direct(
                agent_id=routing_decision.agent_id,
                capability=routing_decision.capability,
                parameters=routing_decision.parameters
            )
            
            return QueryResponse(
                request_id=f"req_{asyncio.get_event_loop().time()}",
                intent=routing_decision.intent,
                routing="direct",
                agent_id=routing_decision.agent_id,
                result=result,
                duration_ms=routing_decision.duration_ms
            )
        
        elif routing_decision.route == "coordinator":
            # Multi-agent orchestration
            result = await gateway.orchestrate_request(
                query=request.query,
                context=request.context
            )
            
            return QueryResponse(
                request_id=result["request_id"],
                intent=routing_decision.intent,
                routing="coordinator",
                result=result["result"],
                execution_path=result.get("execution_path", []),
                duration_ms=result.get("duration_ms", 0)
            )
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown routing: {routing_decision.route}")
            
    except Exception as e:
        logger.error(f"Query processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agent/{agent_id}/capabilities")
async def get_agent_capabilities(agent_id: str) -> Dict[str, Any]:
    """Get capabilities for a specific agent"""
    try:
        capabilities = await gateway.get_agent_capabilities(agent_id)
        return {
            "status": "success",
            "agent_id": agent_id,
            "capabilities": capabilities
        }
    except Exception as e:
        logger.error(f"Error getting agent capabilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/{agent_id}/{capability}")
async def call_agent_capability(
    agent_id: str, 
    capability: str, 
    request: AgentRequest
) -> Dict[str, Any]:
    """Direct agent capability invocation"""
    try:
        start_time = asyncio.get_event_loop().time()
        
        result = await gateway.call_agent_direct(
            agent_id=agent_id,
            capability=capability,
            parameters=request.parameters
        )
        
        duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        return {
            "status": "success",
            "agent_id": agent_id,
            "capability": capability,
            "result": result,
            "duration_ms": duration_ms
        }
    except Exception as e:
        logger.error(f"Direct agent call failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time interactions"""
    await websocket.accept()
    
    try:
        while True:
            # Receive query from client
            data = await websocket.receive_text()
            request_data = json.loads(data)
            
            query = request_data.get("query", "")
            context = request_data.get("context", {})
            
            if not query:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Query is required"
                }))
                continue
            
            # Send initial response
            await websocket.send_text(json.dumps({
                "type": "status",
                "message": "Processing query...",
                "timestamp": asyncio.get_event_loop().time()
            }))
            
            # Classify intent
            routing_decision = await intent_classifier.classify_intent(query)
            
            await websocket.send_text(json.dumps({
                "type": "intent",
                "intent": routing_decision.intent,
                "routing": routing_decision.route,
                "confidence": routing_decision.confidence
            }))
            
            if routing_decision.route == "coordinator":
                # Stream coordinator results
                async for update in gateway.orchestrate_request_stream(query, context):
                    await websocket.send_text(json.dumps(update))
            else:
                # Direct agent call
                result = await gateway.call_agent_direct(
                    agent_id=routing_decision.agent_id,
                    capability=routing_decision.capability,
                    parameters=routing_decision.parameters
                )
                
                await websocket.send_text(json.dumps({
                    "type": "result",
                    "agent_id": routing_decision.agent_id,
                    "result": result,
                    "timestamp": asyncio.get_event_loop().time()
                }))
            
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": str(e)
        }))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)