from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
from typing import Dict, Any, AsyncGenerator
import asyncio
import logging
import json
import httpx

from .coordinator import Coordinator
from .policy.engine import PolicyEngine

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import tracing from agent SDK
try:
    from kenny_agent import init_tracing, TracingMiddleware, AsyncSpanContext, SpanType
    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False
    logger.warning("Tracing not available - install agent SDK for full observability")


app = FastAPI(
    title="Kenny v2 Coordinator",
    description="Multi-agent orchestration service with LangGraph",
    version="0.2.0"
)

# Initialize tracing if available
tracer = None
if TRACING_AVAILABLE:
    tracer = init_tracing("coordinator")
    
    # Add tracing middleware
    app.add_middleware(TracingMiddleware, tracer=tracer)
    
    # Add span exporter to send traces to registry
    async def send_trace_to_registry(span):
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                await client.post(
                    "http://localhost:8001/traces/collect",
                    json=span.to_dict(),
                    headers={"Content-Type": "application/json"}
                )
        except Exception as e:
            logger.debug(f"Failed to send trace to registry: {e}")
    
    tracer.add_span_exporter(send_trace_to_registry)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize coordinator and policy engine
coordinator = Coordinator()
policy_engine = PolicyEngine()
policy_engine.load_default_rules()

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "coordinator",
        "version": "0.2.0"
    }

@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint"""
    return {"message": "Kenny v2 Coordinator Service"}

@app.get("/coordinator/graph")
async def get_graph_info() -> Dict[str, Any]:
    """Get coordinator graph information"""
    return coordinator.get_graph_info()

@app.get("/agents")
async def get_available_agents() -> Dict[str, Any]:
    """Get available agents from registry"""
    try:
        agents = await coordinator.agent_client.get_available_agents()
        return {
            "status": "success",
            "agents": agents,
            "count": len(agents)
        }
    except Exception as e:
        logger.error(f"Error getting agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/capabilities")
async def get_all_capabilities() -> Dict[str, Any]:
    """Get all available capabilities from all agents"""
    try:
        agents = await coordinator.agent_client.get_available_agents()
        all_capabilities = []
        
        for agent in agents:
            agent_id = agent.get("agent_id")
            if agent_id:
                capabilities = await coordinator.agent_client.get_agent_capabilities(agent_id)
                all_capabilities.extend(capabilities)
        
        return {
            "status": "success", 
            "capabilities": all_capabilities,
            "count": len(all_capabilities)
        }
    except Exception as e:
        logger.error(f"Error getting capabilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/coordinator/process")
async def process_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Process a user request through the coordinator"""
    if TRACING_AVAILABLE and tracer:
        async with AsyncSpanContext(tracer, "coordinator.process_request", SpanType.COORDINATOR_NODE) as span:
            try:
                user_input = request.get("user_input", "")
                context = request.get("context", {})
                
                span.set_attribute("request.user_input", user_input[:100])  # Truncate for privacy
                span.set_attribute("request.context_keys", list(context.keys()))
                
                if not user_input:
                    raise HTTPException(status_code=400, detail="user_input is required")
                
                # Process through coordinator
                result_state = await coordinator.process_request(user_input, context)
                
                # Add result attributes to span
                span.set_attribute("response.intent", result_state["context"].get("intent"))
                span.set_attribute("response.agent_count", len(result_state["results"]))
                span.set_attribute("response.error_count", len(result_state["errors"]))
                span.set_attribute("response.execution_path", result_state["execution_path"])
                
                return {
                    "status": "success",
                    "input": user_input,
                    "result": {
                        "intent": result_state["context"].get("intent"),
                        "plan": result_state["context"].get("plan"),
                        "execution_path": result_state["execution_path"],
                        "results": result_state["results"],
                        "errors": result_state["errors"]
                    }
                }
            except Exception as e:
                span.set_error(e)
                logger.error(f"Error processing request: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    else:
        # Fallback without tracing
        try:
            user_input = request.get("user_input", "")
            context = request.get("context", {})
            
            if not user_input:
                raise HTTPException(status_code=400, detail="user_input is required")
            
            # Process through coordinator
            result_state = await coordinator.process_request(user_input, context)
            
            return {
                "status": "success",
                "input": user_input,
                "result": {
                    "intent": result_state["context"].get("intent"),
                    "plan": result_state["context"].get("plan"),
                    "execution_path": result_state["execution_path"],
                    "results": result_state["results"],
                    "errors": result_state["errors"]
                }
            }
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/coordinator/process-stream")
async def process_request_stream(request: Dict[str, Any]) -> StreamingResponse:
    """Process a user request with progressive streaming results"""
    user_input = request.get("user_input", "")
    context = request.get("context", {})
    
    if not user_input:
        raise HTTPException(status_code=400, detail="user_input is required")
    
    async def generate_progressive_response() -> AsyncGenerator[str, None]:
        """Generate Server-Sent Events stream of progressive results"""
        try:
            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'message': 'Starting request processing', 'timestamp': asyncio.get_event_loop().time()})}\n\n"
            
            # Stream results from coordinator
            async for update in coordinator.process_request_progressive(user_input, context):
                yield f"data: {json.dumps(update)}\n\n"
                
        except Exception as e:
            error_msg = {
                "type": "error", 
                "message": str(e), 
                "timestamp": asyncio.get_event_loop().time()
            }
            yield f"data: {json.dumps(error_msg)}\n\n"
        finally:
            # Send completion signal
            completion_msg = {
                "type": "complete", 
                "message": "Request processing finished", 
                "timestamp": asyncio.get_event_loop().time()
            }
            yield f"data: {json.dumps(completion_msg)}\n\n"
    
    return StreamingResponse(
        generate_progressive_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.get("/policy/rules")
async def get_policy_rules() -> Dict[str, Any]:
    """Get all policy rules"""
    return {
        "rules": policy_engine.get_rules(),
        "total_count": len(policy_engine.get_rules())
    }

@app.post("/policy/evaluate")
async def evaluate_policy(context: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate policy for a given context"""
    try:
        result = policy_engine.evaluate_policy(context)
        return result
    except Exception as e:
        logger.error(f"Error evaluating policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/policy/rules")
async def add_policy_rule(rule: Dict[str, Any]) -> Dict[str, Any]:
    """Add a new policy rule"""
    try:
        from .policy.engine import PolicyAction
        
        name = rule.get("name")
        action_str = rule.get("action")
        conditions = rule.get("conditions", {})
        priority = rule.get("priority", 100)
        
        if not name or not action_str:
            raise HTTPException(status_code=400, detail="name and action are required")
        
        try:
            action = PolicyAction(action_str)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid action: {action_str}")
        
        rule_id = policy_engine.add_rule(name, action, conditions, priority)
        
        return {
            "status": "success",
            "rule_id": rule_id,
            "message": f"Policy rule '{name}' added successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding policy rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
