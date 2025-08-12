from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
import re


class CapabilitySLA(BaseModel):
    """Service level agreement parameters for a capability"""
    latency_ms: Optional[int] = Field(None, ge=1, description="Expected response time in milliseconds")
    rate_limit: Optional[int] = Field(None, ge=1, description="Maximum requests per minute")
    max_tokens: Optional[int] = Field(None, ge=1, description="Maximum token usage per request")
    timeout_seconds: Optional[int] = Field(None, ge=1, le=300, description="Request timeout in seconds")


class CapabilityExample(BaseModel):
    """Example input/output pair for a capability"""
    input: Dict[str, Any] = Field(..., description="Example input for this capability")
    output: Dict[str, Any] = Field(..., description="Example output from this capability")


class Capability(BaseModel):
    """A capability that an agent provides"""
    verb: str = Field(..., description="Action verb for this capability")
    input_schema: Dict[str, Any] = Field(..., description="JSON Schema for capability inputs")
    output_schema: Dict[str, Any] = Field(..., description="JSON Schema for capability outputs")
    safety_annotations: List[str] = Field(
        default=["read-only"],
        description="Safety and permission annotations"
    )
    sla: Optional[CapabilitySLA] = Field(None, description="Service level agreement parameters")
    description: Optional[str] = Field(None, description="Human-readable description of this capability")
    examples: Optional[List[CapabilityExample]] = Field(None, description="Example input/output pairs")

    @field_validator('verb')
    @classmethod
    def validate_verb(cls, v):
        if not re.match(r'^[a-z]+\.[a-z_]+$', v):
            raise ValueError('Verb must match pattern: [a-z]+.[a-z_]+')
        return v

    @field_validator('safety_annotations')
    @classmethod
    def validate_safety_annotations(cls, v):
        valid_annotations = {
            "read-only", "write-requires-approval", "local-only", 
            "no-egress", "pii-sensitive"
        }
        for annotation in v:
            if annotation not in valid_annotations:
                raise ValueError(f'Invalid safety annotation: {annotation}')
        return v


class HealthCheckConfig(BaseModel):
    """Health check configuration for an agent"""
    endpoint: str = Field(default="/health", description="Health check endpoint path")
    interval_seconds: int = Field(default=60, ge=30, description="Health check interval in seconds")
    timeout_seconds: int = Field(default=10, ge=5, le=60, description="Health check timeout in seconds")


class AgentManifest(BaseModel):
    """Complete agent manifest for registration"""
    agent_id: str = Field(..., description="Unique identifier for the agent")
    version: str = Field(default="1.0.0", description="Agent version in semver format")
    display_name: Optional[str] = Field(None, description="Human-readable name for the agent")
    description: Optional[str] = Field(None, description="Brief description of the agent's purpose")
    capabilities: List[Capability] = Field(..., min_length=1, description="List of capabilities this agent provides")
    data_scopes: List[str] = Field(..., description="Data domains this agent can access")
    tool_access: List[str] = Field(..., description="Local tools/endpoints this agent needs access to")
    egress_domains: List[str] = Field(default=[], description="External domains this agent may need to access")
    health_check: Optional[HealthCheckConfig] = Field(None, description="Health check configuration for the agent")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional agent-specific metadata")

    @field_validator('agent_id')
    @classmethod
    def validate_agent_id(cls, v):
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('Agent ID must match pattern: [a-z0-9-]+')
        return v

    @field_validator('version')
    @classmethod
    def validate_version(cls, v):
        if not re.match(r'^\d+\.\d+\.\d+$', v):
            raise ValueError('Version must be in semver format: X.Y.Z')
        return v

    @field_validator('data_scopes')
    @classmethod
    def validate_data_scopes(cls, v):
        for scope in v:
            if not re.match(r'^[a-z]+:[a-z-]+$', scope):
                raise ValueError(f'Data scope must match pattern: [a-z]+:[a-z-]+ (got: {scope})')
        return v


class AgentRegistration(BaseModel):
    """Agent registration request"""
    manifest: AgentManifest
    health_endpoint: str = Field(..., description="Base URL for agent health checks")


class AgentStatus(BaseModel):
    """Current status of a registered agent"""
    agent_id: str
    manifest: AgentManifest
    health_endpoint: str
    is_healthy: bool = False
    last_health_check: Optional[str] = None
    last_seen: str
    error_count: int = 0
    last_error: Optional[str] = None


class CapabilityInfo(BaseModel):
    """Information about a specific capability"""
    verb: str
    agent_id: str
    agent_name: str
    description: Optional[str]
    safety_annotations: List[str]
    sla: Optional[CapabilitySLA]


class HealthCheckResponse(BaseModel):
    """Response from agent health check"""
    status: str
    timestamp: str
    details: Optional[Dict[str, Any]] = None
