from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from enum import Enum

class RoutingType(str, Enum):
    DIRECT = "direct"
    COORDINATOR = "coordinator"
    EXPRESS = "express"

class QueryRequest(BaseModel):
    """Request for unified query endpoint"""
    query: str = Field(..., description="User query or command")
    context: Optional[Dict[str, Any]] = Field(default={}, description="Additional context")
    user_id: Optional[str] = Field(default=None, description="User identifier")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    stream: bool = Field(default=False, description="Enable streaming response")

class QueryResponse(BaseModel):
    """Response from unified query endpoint"""
    request_id: str = Field(..., description="Unique request identifier")
    intent: str = Field(..., description="Classified intent")
    routing: RoutingType = Field(..., description="Routing decision")
    agent_id: Optional[str] = Field(default=None, description="Agent used for direct routing")
    result: Dict[str, Any] = Field(..., description="Query result")
    execution_path: Optional[List[str]] = Field(default=[], description="Execution path for coordinator routing")
    duration_ms: int = Field(..., description="Processing duration in milliseconds")
    stream_url: Optional[str] = Field(default=None, description="WebSocket URL for streaming")

class AgentRequest(BaseModel):
    """Request for direct agent capability invocation"""
    parameters: Dict[str, Any] = Field(default={}, description="Capability parameters")

class RoutingDecision(BaseModel):
    """Intent classification and routing decision"""
    route: RoutingType = Field(..., description="Routing type")
    intent: str = Field(..., description="Classified intent")
    confidence: float = Field(..., description="Classification confidence")
    agent_id: Optional[str] = Field(default=None, description="Target agent for direct routing")
    capability: Optional[str] = Field(default=None, description="Target capability for direct routing")
    parameters: Dict[str, Any] = Field(default={}, description="Extracted parameters")
    duration_ms: int = Field(default=0, description="Classification duration")

class AgentInfo(BaseModel):
    """Agent information from registry"""
    agent_id: str
    display_name: Optional[str] = None
    status: str
    is_healthy: bool
    capabilities: List[str]
    last_seen: str

class CapabilityInfo(BaseModel):
    """Capability information"""
    verb: str
    agent_id: str
    agent_name: str
    description: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    safety_annotations: List[str] = []

class SystemHealth(BaseModel):
    """System health summary"""
    status: str
    total_agents: int
    healthy_agents: int
    unhealthy_agents: int
    total_capabilities: int
    timestamp: str