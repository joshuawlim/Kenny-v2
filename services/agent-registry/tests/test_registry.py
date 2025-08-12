import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import app
from registry import AgentRegistry
from schemas import (
    AgentManifest, Capability, AgentRegistration, 
    CapabilitySLA, HealthCheckConfig
)

client = TestClient(app)


@pytest.fixture
def sample_manifest():
    """Sample agent manifest for testing"""
    return AgentManifest(
        agent_id="test-mail-agent",
        version="1.0.0",
        display_name="Test Mail Agent",
        description="A test mail agent for testing",
        capabilities=[
            Capability(
                verb="messages.search",
                input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"results": {"type": "array"}}},
                description="Search mail messages",
                safety_annotations=["read-only", "local-only"]
            )
        ],
        data_scopes=["mail:inbox", "mail:sent"],
        tool_access=["macos-bridge", "sqlite-db"],
        egress_domains=[],
        health_check=HealthCheckConfig(
            endpoint="/health",
            interval_seconds=60,
            timeout_seconds=10
        )
    )


@pytest.fixture
def sample_registration(sample_manifest):
    """Sample agent registration for testing"""
    return AgentRegistration(
        manifest=sample_manifest,
        health_endpoint="http://localhost:8001"
    )


class TestAgentRegistry:
    """Test the core AgentRegistry class"""
    
    @pytest.mark.asyncio
    async def test_register_agent(self, sample_registration):
        """Test agent registration"""
        registry = AgentRegistry()
        
        # Register agent
        agent_status = await registry.register_agent(sample_registration)
        
        assert agent_status.agent_id == "test-mail-agent"
        assert agent_status.manifest == sample_registration.manifest
        assert agent_status.health_endpoint == "http://localhost:8001"
        assert agent_status.is_healthy is False
        assert agent_status.error_count == 0
        
        # Verify agent is stored
        stored_agent = await registry.get_agent("test-mail-agent")
        assert stored_agent is not None
        assert stored_agent.agent_id == "test-mail-agent"
    
    @pytest.mark.asyncio
    async def test_duplicate_registration(self, sample_registration):
        """Test duplicate agent registration fails"""
        registry = AgentRegistry()
        
        # Register first time
        await registry.register_agent(sample_registration)
        
        # Try to register again
        with pytest.raises(ValueError, match="already registered"):
            await registry.register_agent(sample_registration)
    
    @pytest.mark.asyncio
    async def test_unregister_agent(self, sample_registration):
        """Test agent unregistration"""
        registry = AgentRegistry()
        
        # Register agent
        await registry.register_agent(sample_registration)
        
        # Verify agent is registered
        assert await registry.get_agent("test-mail-agent") is not None
        
        # Unregister agent
        success = await registry.unregister_agent("test-mail-agent")
        assert success is True
        
        # Verify agent is removed
        assert await registry.get_agent("test-mail-agent") is None
    
    @pytest.mark.asyncio
    async def test_capability_indexing(self, sample_registration):
        """Test capability indexing during registration"""
        registry = AgentRegistry()
        
        # Register agent
        await registry.register_agent(sample_registration)
        
        # Verify capability is indexed
        capabilities = await registry.get_capabilities()
        assert "messages.search" in capabilities
        
        capability_list = capabilities["messages.search"]
        assert len(capability_list) == 1
        
        capability = capability_list[0]
        assert capability.verb == "messages.search"
        assert capability.agent_id == "test-mail-agent"
        assert capability.agent_name == "Test Mail Agent"
    
    @pytest.mark.asyncio
    async def test_find_agents_for_capability(self, sample_registration):
        """Test finding agents for specific capabilities"""
        registry = AgentRegistry()
        
        # Register agent
        await registry.register_agent(sample_registration)
        
        # Find agents for capability
        capabilities = await registry.find_agents_for_capability("messages.search")
        assert len(capabilities) == 1
        assert capabilities[0].agent_id == "test-mail-agent"
        
        # Find agents for capability with data scope
        capabilities = await registry.find_agents_for_capability("messages.search", "mail:inbox")
        assert len(capabilities) == 1
        
        # Find agents for capability with non-matching data scope
        capabilities = await registry.find_agents_for_capability("messages.search", "calendar:events")
        assert len(capabilities) == 0
    
    @pytest.mark.asyncio
    async def test_egress_domain_validation(self):
        """Test egress domain validation"""
        registry = AgentRegistry()
        
        # Valid local domains
        valid_manifest = AgentManifest(
            agent_id="test-agent",
            capabilities=[Capability(
                verb="test.action",
                input_schema={"type": "object"},
                output_schema={"type": "object"}
            )],
            data_scopes=["test:data"],
            tool_access=["test-tool"],
            egress_domains=["localhost", "127.0.0.1"]
        )
        
        registration = AgentRegistration(
            manifest=valid_manifest,
            health_endpoint="http://localhost:8001"
        )
        
        # Should not raise exception
        await registry.register_agent(registration)
        
        # Invalid external domain
        invalid_manifest = AgentManifest(
            agent_id="test-agent-2",
            capabilities=[Capability(
                verb="test.action",
                input_schema={"type": "object"},
                output_schema={"type": "object"}
            )],
            data_scopes=["test:data"],
            tool_access=["test-tool"],
            egress_domains=["https://external-api.com"]
        )
        
        registration = AgentRegistration(
            manifest=invalid_manifest,
            health_endpoint="http://localhost:8001"
        )
        
        # Should raise exception
        with pytest.raises(ValueError, match="not in allowlist"):
            await registry.register_agent(registration)


class TestAPIEndpoints:
    """Test the FastAPI endpoints"""
    
    def test_root_endpoint(self):
        """Test root endpoint returns service information"""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["service"] == "Kenny Agent Registry"
        assert data["version"] == "1.0.0"
        assert data["status"] == "starting"  # Registry not initialized in test
        assert "endpoints" in data
    
    def test_health_endpoint(self):
        """Test health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "starting"  # Registry not initialized in test
        assert "timestamp" in data
    
    def test_register_agent_service_unavailable(self):
        """Test agent registration when service is starting up"""
        response = client.post(
            "/agents/register",
            json={
                "manifest": {
                    "agent_id": "test-agent",
                    "capabilities": [{
                        "verb": "test.action",
                        "input_schema": {"type": "object"},
                        "output_schema": {"type": "object"}
                    }],
                    "data_scopes": ["test:data"],
                    "tool_access": ["tool"]
                },
                "health_endpoint": "http://localhost:8001"
            }
        )
        assert response.status_code == 503  # Service unavailable
    
    def test_list_agents_service_unavailable(self):
        """Test listing agents when service is starting up"""
        response = client.get("/agents")
        assert response.status_code == 503  # Service unavailable
    
    def test_get_agent_service_unavailable(self):
        """Test getting agent when service is starting up"""
        response = client.get("/agents/test-agent")
        assert response.status_code == 503  # Service unavailable
    
    def test_get_nonexistent_agent_service_unavailable(self):
        """Test getting non-existent agent when service is starting up"""
        response = client.get("/agents/nonexistent-agent")
        assert response.status_code == 503  # Service unavailable
    
    def test_get_capabilities_service_unavailable(self):
        """Test getting capabilities when service is starting up"""
        response = client.get("/capabilities")
        assert response.status_code == 503  # Service unavailable
    
    def test_get_specific_capability_service_unavailable(self):
        """Test getting specific capability when service is starting up"""
        response = client.get("/capabilities/test.action")
        assert response.status_code == 503  # Service unavailable
    
    def test_find_agents_for_capability_service_unavailable(self):
        """Test finding agents for capability when service is starting up"""
        response = client.get("/capabilities/test.action/find?data_scope=test:data")
        assert response.status_code == 503  # Service unavailable
    
    def test_system_health_service_unavailable(self):
        """Test system health when service is starting up"""
        response = client.get("/system/health")
        assert response.status_code == 503  # Service unavailable
    
    def test_unregister_agent_service_unavailable(self):
        """Test agent unregistration when service is starting up"""
        response = client.delete("/agents/test-agent")
        assert response.status_code == 503  # Service unavailable


class TestValidation:
    """Test input validation and error handling"""
    
    def test_invalid_agent_id_format(self):
        """Test agent ID validation"""
        invalid_registration = {
            "manifest": {
                "agent_id": "INVALID_AGENT_ID",  # Invalid format
                "capabilities": [{
                    "verb": "test.action",
                    "input_schema": {"type": "object"},
                    "output_schema": {"type": "object"}
                }],
                "data_scopes": ["test:data"],
                "tool_access": ["tool"]
            },
            "health_endpoint": "http://localhost:8001"
        }
        
        response = client.post("/agents/register", json=invalid_registration)
        assert response.status_code == 422  # Validation error
    
    def test_invalid_version_format(self):
        """Test version validation"""
        invalid_registration = {
            "manifest": {
                "agent_id": "test-agent",
                "version": "invalid-version",  # Invalid format
                "capabilities": [{
                    "verb": "test.action",
                    "input_schema": {"type": "object"},
                    "output_schema": {"type": "object"}
                }],
                "data_scopes": ["test:data"],
                "tool_access": ["tool"]
            },
            "health_endpoint": "http://localhost:8001"
        }
        
        response = client.post("/agents/register", json=invalid_registration)
        assert response.status_code == 422  # Validation error
    
    def test_invalid_data_scope_format(self):
        """Test data scope validation"""
        invalid_registration = {
            "manifest": {
                "agent_id": "test-agent",
                "capabilities": [{
                    "verb": "test.action",
                    "input_schema": {"type": "object"},
                    "output_schema": {"type": "object"}
                }],
                "data_scopes": ["invalid:scope:format"],  # Invalid format
                "tool_access": ["tool"]
            },
            "health_endpoint": "http://localhost:8001"
        }
        
        response = client.post("/agents/register", json=invalid_registration)
        assert response.status_code == 422  # Validation error
    
    def test_invalid_capability_verb_format(self):
        """Test capability verb validation"""
        invalid_registration = {
            "manifest": {
                "agent_id": "test-agent",
                "capabilities": [{
                    "verb": "INVALID_VERB",  # Invalid format
                    "input_schema": {"type": "object"},
                    "output_schema": {"type": "object"}
                }],
                "data_scopes": ["test:data"],
                "tool_access": ["tool"]
            },
            "health_endpoint": "http://localhost:8001"
        }
        
        response = client.post("/agents/register", json=invalid_registration)
        assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    pytest.main([__file__])
