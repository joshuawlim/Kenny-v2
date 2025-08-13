import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

# Import the classes we'll implement
from kenny_agent.base_agent import BaseAgent
from kenny_agent.base_handler import BaseCapabilityHandler
from kenny_agent.base_tool import BaseTool
from kenny_agent.health import HealthStatus, HealthCheck
from kenny_agent.registry import AgentRegistryClient


class TestBaseAgent:
    """Test the base agent class functionality"""
    
    def test_agent_inheritance(self):
        """Test that agents can inherit from BaseAgent"""
        class TestAgent(BaseAgent):
            def __init__(self):
                super().__init__(
                    agent_id="test-agent",
                    name="Test Agent",
                    description="A test agent"
                )
            
            async def start(self):
                pass
            
            async def stop(self):
                pass
        
        agent = TestAgent()
        assert agent.agent_id == "test-agent"
        assert agent.name == "Test Agent"
        assert agent.description == "A test agent"
    
    def test_agent_capability_registration(self):
        """Test that capability handlers can be registered"""
        class TestAgent(BaseAgent):
            def __init__(self):
                super().__init__(
                    agent_id="test-agent",
                    name="Test Agent",
                    description="A test agent"
                )
            
            async def start(self):
                pass
            
            async def stop(self):
                pass
        
        agent = TestAgent()
        
        # Mock capability handler
        mock_handler = Mock(spec=BaseCapabilityHandler)
        mock_handler.capability = "test.capability"
        
        agent.register_capability(mock_handler)
        assert "test.capability" in agent.capabilities
        assert agent.capabilities["test.capability"] == mock_handler
    
    def test_agent_capability_execution(self):
        """Test that registered capabilities can be executed"""
        class TestAgent(BaseAgent):
            def __init__(self):
                super().__init__(
                    agent_id="test-agent",
                    name="Test Agent",
                    description="A test agent"
                )
            
            async def start(self):
                pass
            
            async def stop(self):
                pass
        
        agent = TestAgent()
        
        # Mock capability handler with async execute method
        mock_handler = Mock(spec=BaseCapabilityHandler)
        mock_handler.capability = "test.capability"
        mock_handler.execute = AsyncMock(return_value={"result": "success"})
        
        agent.register_capability(mock_handler)
        
        # Test execution
        result = asyncio.run(agent.execute_capability("test.capability", {"param": "value"}))
        assert result == {"result": "success"}
        mock_handler.execute.assert_called_once_with({"param": "value"})
    
    def test_agent_unknown_capability(self):
        """Test that unknown capabilities raise appropriate errors"""
        class TestAgent(BaseAgent):
            def __init__(self):
                super().__init__(
                    agent_id="test-agent",
                    name="Test Agent",
                    description="A test agent"
                )
            
            async def start(self):
                pass
            
            async def stop(self):
                pass
        
        agent = TestAgent()
        
        with pytest.raises(ValueError, match="Unknown capability: unknown.capability"):
            asyncio.run(agent.execute_capability("unknown.capability", {}))
    
    def test_agent_manifest_generation(self):
        """Test that agent manifest is generated correctly"""
        class TestAgent(BaseAgent):
            def __init__(self):
                super().__init__(
                    agent_id="test-agent",
                    name="Test Agent",
                    description="A test agent"
                )
            
            async def start(self):
                pass
            
            async def stop(self):
                pass
        
        agent = TestAgent()
        
        # Register a capability
        mock_handler = Mock(spec=BaseCapabilityHandler)
        mock_handler.capability = "test.capability"
        mock_handler.get_manifest = Mock(return_value={
            "verb": "test",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "safety_annotations": ["read-only"],
            "description": "Test capability"
        })
        
        agent.register_capability(mock_handler)
        
        manifest = agent.generate_manifest()
        assert manifest["agent_id"] == "test-agent"
        assert manifest["display_name"] == "Test Agent"
        assert manifest["description"] == "A test agent"
        assert len(manifest["capabilities"]) == 1
        assert manifest["capabilities"][0]["verb"] == "test"
        assert "data_scopes" in manifest
        assert "tool_access" in manifest
        assert "egress_domains" in manifest
        assert "health_check" in manifest

    def test_manifest_registry_schema_alignment(self):
        """Test that generated manifest aligns with registry schema requirements"""
        class TestAgent(BaseAgent):
            def __init__(self):
                super().__init__(
                    agent_id="test-agent",
                    name="Test Agent",
                    description="A test agent",
                    data_scopes=["mail:inbox", "mail:sent"],
                    tool_access=["macos-bridge", "sqlite-db"],
                    egress_domains=[],
                    health_check={"endpoint": "/health", "interval_seconds": 60, "timeout_seconds": 10}
                )
            
            async def start(self):
                pass
            
            async def stop(self):
                pass
        
        agent = TestAgent()
        
        # Register a capability with proper schema
        mock_handler = Mock(spec=BaseCapabilityHandler)
        mock_handler.capability = "messages.search"
        mock_handler.get_manifest = Mock(return_value={
            "verb": "messages.search",
            "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}},
            "output_schema": {"type": "object", "properties": {"results": {"type": "array"}}},
            "safety_annotations": ["read-only", "local-only"],
            "description": "Search mail messages"
        })
        
        agent.register_capability(mock_handler)
        
        manifest = agent.generate_manifest()
        
        # Verify required fields from registry schema
        assert manifest["agent_id"] == "test-agent"
        assert manifest["version"] == "1.0.0"
        assert manifest["display_name"] == "Test Agent"
        assert manifest["description"] == "A test agent"
        assert manifest["data_scopes"] == ["mail:inbox", "mail:sent"]
        assert manifest["tool_access"] == ["macos-bridge", "sqlite-db"]
        assert manifest["egress_domains"] == []
        assert manifest["health_check"]["endpoint"] == "/health"
        
        # Verify capability structure
        assert len(manifest["capabilities"]) == 1
        capability = manifest["capabilities"][0]
        assert capability["verb"] == "messages.search"
        assert "input_schema" in capability
        assert "output_schema" in capability
        assert "safety_annotations" in capability
        assert "description" in capability


class TestBaseCapabilityHandler:
    """Test the base capability handler functionality"""
    
    def test_handler_creation(self):
        """Test that capability handlers can be created"""
        class TestHandler(BaseCapabilityHandler):
            async def execute(self, parameters):
                return {"result": "test"}
        
        handler = TestHandler(
            capability="test.capability",
            description="Test capability description"
        )
        
        assert handler.capability == "test.capability"
        assert handler.description == "Test capability description"
    
    def test_handler_execute_abstract(self):
        """Test that base handler execute method is abstract"""
        # This test verifies that the abstract base class cannot be instantiated
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseCapabilityHandler(
                capability="test.capability",
                description="Test capability description"
            )
    
    def test_handler_manifest_generation(self):
        """Test that handler manifest is generated correctly"""
        class TestHandler(BaseCapabilityHandler):
            async def execute(self, parameters):
                return {"result": "test"}
        
        handler = TestHandler(
            capability="test.capability",
            description="Test capability description"
        )
        
        manifest = handler.get_manifest()
        assert manifest["verb"] == "test"
        assert manifest["description"] == "Test capability description"


class TestBaseTool:
    """Test the base tool functionality"""
    
    def test_tool_creation(self):
        """Test that tools can be created"""
        class TestTool(BaseTool):
            def execute(self, parameters):
                return {"result": "test"}
        
        tool = TestTool(
            name="test_tool",
            description="Test tool description"
        )
        
        assert tool.name == "test_tool"
        assert tool.description == "Test tool description"
    
    def test_tool_execute_abstract(self):
        """Test that base tool execute method is abstract"""
        # This test verifies that the abstract base class cannot be instantiated
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseTool(
                name="test_tool",
                description="Test tool description"
            )


class TestHealthCheck:
    """Test health check functionality"""
    
    def test_health_status_creation(self):
        """Test that health status can be created"""
        status = HealthStatus(
            status="healthy",
            message="All systems operational",
            details={"cpu": "normal", "memory": "normal"}
        )
        
        assert status.status == "healthy"
        assert status.message == "All systems operational"
        assert status.details["cpu"] == "normal"
    
    def test_health_check_execution(self):
        """Test that health checks can be executed"""
        def mock_health_check():
            return HealthStatus(
                status="healthy",
                message="Check passed",
                details={}
            )
        
        health_check = HealthCheck(
            name="test_check",
            check_function=mock_health_check
        )
        
        result = health_check.execute()
        assert result.status == "healthy"
        assert result.message == "Check passed"


class TestAgentRegistryClient:
    """Test agent registry client functionality"""
    
    @pytest.mark.asyncio
    async def test_registry_client_creation(self):
        """Test that registry client can be created"""
        client = AgentRegistryClient(base_url="http://localhost:8000")
        assert client.base_url == "http://localhost:8000"
    
    @pytest.mark.asyncio
    async def test_registry_client_register_agent(self):
        """Test that agents can be registered with registry"""
        with patch('httpx.AsyncClient') as mock_client_class:
            # Mock the async context manager
            mock_client = Mock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "registered"}
            mock_client.post = AsyncMock(return_value=mock_response)
            
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
            
            client = AgentRegistryClient(base_url="http://localhost:8000")
            manifest = {
                "agent_id": "test-agent",
                "name": "Test Agent",
                "capabilities": []
            }
            
            result = await client.register_agent(manifest)
            assert result["status"] == "registered"
            mock_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_registry_client_health_check(self):
        """Test that agents can be registered with registry"""
        with patch('httpx.AsyncClient') as mock_client_class:
            # Mock the async context manager
            mock_client = Mock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "healthy"}
            mock_client.post = AsyncMock(return_value=mock_response)
            
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
            
            client = AgentRegistryClient(base_url="http://localhost:8000")
            result = await client.update_health("test-agent", {"status": "healthy"})
            assert result["status"] == "healthy"
            mock_client.post.assert_called_once()


class TestIntegration:
    """Test integration between components"""
    
    def test_agent_with_capabilities_and_tools(self):
        """Test that agents can use both capabilities and tools"""
        class TestAgent(BaseAgent):
            def __init__(self):
                super().__init__(
                    agent_id="test-agent",
                    name="Test Agent",
                    description="A test agent"
                )
            
            async def start(self):
                pass
            
            async def stop(self):
                pass
        
        agent = TestAgent()
        
        # Register capability
        mock_handler = Mock(spec=BaseCapabilityHandler)
        mock_handler.capability = "test.capability"
        mock_handler.execute = AsyncMock(return_value={"result": "capability_success"})
        
        # Register tool
        mock_tool = Mock(spec=BaseTool)
        mock_tool.name = "test_tool"
        mock_tool.execute = Mock(return_value={"result": "tool_success"})
        
        agent.register_capability(mock_handler)
        agent.register_tool(mock_tool)
        
        assert "test.capability" in agent.capabilities
        assert "test_tool" in agent.tools
