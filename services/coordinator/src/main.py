from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Dict, Any
import asyncio
import logging

from .coordinator import Coordinator
from .policy.engine import PolicyEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Kenny v2 Coordinator",
    description="Multi-agent orchestration service with LangGraph",
    version="0.2.0"
)

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
    uvicorn.run(app, host="0.0.0.0", port=8001)
