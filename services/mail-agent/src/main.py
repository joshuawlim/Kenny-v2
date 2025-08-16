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

from .intelligent_mail_agent import create_mail_agent

# Initialize the Intelligent Mail Agent (with fallback to basic agent)
mail_agent = create_mail_agent(
    intelligent=os.getenv("KENNY_INTELLIGENT_AGENTS", "true").lower() == "true",
    llm_model=os.getenv("KENNY_LLM_MODEL", "llama3.2:3b")
)

# Create FastAPI app
app = FastAPI(
    title="Intelligent Mail Agent",
    description="AI-powered mail search, read, and reply proposals with natural language understanding",
    version="2.1.0"
)


class CapabilityRequest(BaseModel):
    """Request model for capability execution."""
    input: Dict[str, Any]


class CapabilityResponse(BaseModel):
    """Response model for capability execution."""
    output: Dict[str, Any]


class QueryRequest(BaseModel):
    """Request model for natural language queries."""
    query: str
    context: Dict[str, Any] = {}


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
    health_data = mail_agent.get_health_status()
    # Ensure the response includes the timestamp field expected by the registry
    if "last_updated" in health_data:
        health_data["timestamp"] = health_data["last_updated"]
    return health_data


@app.get("/health/performance")
async def enhanced_health_check():
    """Enhanced health check endpoint with performance metrics."""
    try:
        # Check if this is an intelligent agent with performance metrics
        if hasattr(mail_agent, 'get_performance_metrics'):
            metrics = mail_agent.get_performance_metrics()
            health_data = mail_agent.get_health_status()
            
            return {
                "agent_name": mail_agent.agent_id,
                "agent_type": "intelligent_service" if hasattr(mail_agent, 'llm_processor') else "basic_service",
                "overall_health": health_data,
                "performance_summary": {
                    "current_metrics": {
                        "response_time_ms": metrics.get('avg_response_time', 0) * 1000,
                        "success_rate_percent": 100.0,  # TODO: Track success rate
                        "cache_hit_rate_percent": metrics.get('cache_hit_rate', 0) * 100,
                        "total_queries": metrics.get('total_queries', 0),
                        "llm_interpretation_time_ms": metrics.get('llm_interpretation_time', 0) * 1000,
                        "timestamp": health_data.get('last_updated', health_data.get('timestamp'))
                    },
                    "sla_compliance": {
                        "response_time_sla": {
                            "current_ms": metrics.get('avg_response_time', 0) * 1000,
                            "threshold_ms": 5000,
                            "compliant": metrics.get('avg_response_time', 0) < 5.0
                        },
                        "cache_hit_rate_sla": {
                            "current_percent": metrics.get('cache_hit_rate', 0) * 100,
                            "threshold_percent": 80.0,
                            "compliant": metrics.get('cache_hit_rate', 0) >= 0.8
                        },
                        "overall_compliant": metrics.get('status') in ['optimal', 'acceptable']
                    },
                    "trend_analysis": {"trend": metrics.get('status', 'unknown'), "change_percent": 0.0}
                },
                "alerts": {"recent": [], "total_count": 0, "active_issues": 0},
                "recommendations": [
                    "Agent upgraded to intelligent service with LLM capabilities" if hasattr(mail_agent, 'llm_processor') else "Consider upgrading to intelligent agent"
                ]
            }
        else:
            # Fallback to basic health with mock performance data
            basic_health = mail_agent.get_health_status()
            return {
                "agent_name": "mail-agent",
                "overall_health": basic_health,
                "performance_summary": {
                    "current_metrics": {
                        "response_time_ms": 100.0,
                        "success_rate_percent": 100.0,
                        "throughput_ops_per_min": 1.0,
                        "error_count": 0,
                        "timestamp": "2025-08-15T00:00:00Z"
                    },
                    "sla_compliance": {
                        "response_time_sla": {"current_ms": 100.0, "threshold_ms": 2000, "compliant": True},
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
    for capability_name, handler in mail_agent.capabilities.items():
        if hasattr(handler, 'get_manifest'):
            capability_manifest = handler.get_manifest()
            capabilities.append(capability_manifest)
    
    return {
        "agent_id": mail_agent.agent_id,
        "capabilities": capabilities
    }


@app.post("/query")
async def process_natural_language_query(request: QueryRequest):
    """
    Process natural language queries using intelligent agent capabilities.
    
    Args:
        request: Query request with natural language query and optional context
        
    Returns:
        Structured response with interpretation and results
    """
    try:
        # Check if this is an intelligent agent
        if hasattr(mail_agent, 'handle_query'):
            result = await mail_agent.handle_query(request.query, request.context)
            return result
        else:
            # Fallback for basic agents - try to map to search capability
            try:
                search_result = await mail_agent.execute_capability("search", {"query": request.query})
                return {
                    "success": True,
                    "result": {
                        "interpretation": {
                            "capability": "search",
                            "parameters": {"query": request.query},
                            "confidence": 0.5,
                            "reasoning": "Basic agent fallback to search"
                        },
                        "capability_result": search_result
                    },
                    "confidence": 0.5,
                    "cached": False,
                    "agent_id": mail_agent.agent_id
                }
            except Exception as fallback_error:
                raise HTTPException(
                    status_code=501,
                    detail=f"Natural language processing not available in basic agent mode: {str(fallback_error)}"
                )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Query processing failed: {str(e)}"
        )


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
