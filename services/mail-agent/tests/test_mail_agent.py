"""
Tests for the Mail Agent.

This test suite verifies that the Mail Agent works correctly with
all its capabilities and tools.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from typing import Dict, Any

# Import the classes we'll test
from src.agent import MailAgent
from src.handlers.search import SearchCapabilityHandler
from src.handlers.read import ReadCapabilityHandler
from src.handlers.propose_reply import ProposeReplyCapabilityHandler
from src.tools.mail_bridge import MailBridgeTool


class TestMailAgent:
    """Test the Mail Agent functionality."""
    
    def test_agent_creation(self):
        """Test that the Mail Agent can be created."""
        agent = MailAgent()
        assert agent.agent_id == "mail-agent"
        assert agent.name == "Mail Agent"
        assert agent.description == "Read-only mail search/read and reply proposals"
        assert "mail:inbox" in agent.data_scopes
        assert "mail:sent" in agent.data_scopes
        assert "macos-bridge" in agent.tool_access
        assert "sqlite-db" in agent.tool_access
        assert "ollama" in agent.tool_access
        assert agent.egress_domains == []
    
    def test_capability_registration(self):
        """Test that all expected capabilities are registered."""
        agent = MailAgent()
        expected_capabilities = ["messages.search", "messages.read", "messages.propose_reply"]
        
        for capability in expected_capabilities:
            assert capability in agent.capabilities
            assert hasattr(agent.capabilities[capability], 'execute')
    
    def test_tool_registration(self):
        """Test that the mail bridge tool is registered."""
        agent = MailAgent()
        assert "mail_bridge" in agent.tools
        assert isinstance(agent.tools["mail_bridge"], MailBridgeTool)
    
    def test_manifest_generation(self):
        """Test that the agent manifest is generated correctly."""
        agent = MailAgent()
        manifest = agent.generate_manifest()
        
        # Verify required fields
        assert manifest["agent_id"] == "mail-agent"
        assert manifest["version"] == "1.0.0"
        assert manifest["display_name"] == "Mail Agent"
        assert manifest["description"] == "Read-only mail search/read and reply proposals"
        assert manifest["data_scopes"] == ["mail:inbox", "mail:sent"]
        assert manifest["tool_access"] == ["macos-bridge", "sqlite-db", "ollama"]
        assert manifest["egress_domains"] == []
        assert "health_check" in manifest
        
        # Verify capabilities
        assert len(manifest["capabilities"]) == 3
        capability_verbs = [cap["verb"] for cap in manifest["capabilities"]]
        assert "messages.search" in capability_verbs
        assert "messages.read" in capability_verbs
        assert "messages.propose_reply" in capability_verbs


class TestSearchCapabilityHandler:
    """Test the search capability handler."""
    
    def test_handler_creation(self):
        """Test that the search handler can be created."""
        handler = SearchCapabilityHandler()
        assert handler.capability == "messages.search"
        assert handler.verb == "messages"
        assert handler.noun == "search"
        assert "read-only" in handler.safety_annotations
        assert "local-only" in handler.safety_annotations
        assert "no-egress" in handler.safety_annotations
    
    def test_manifest_generation(self):
        """Test that the search handler generates correct manifest."""
        handler = SearchCapabilityHandler()
        manifest = handler.get_manifest()
        
        assert manifest["verb"] == "messages.search"
        assert "input_schema" in manifest
        assert "output_schema" in manifest
        assert "safety_annotations" in manifest
        assert "description" in manifest
    
    @pytest.mark.asyncio
    async def test_execute_search(self):
        """Test that the search capability executes correctly."""
        handler = SearchCapabilityHandler()
        parameters = {"query": "test", "mailbox": "Inbox", "limit": 5}
        
        result = await handler.execute(parameters)
        
        assert "results" in result
        assert "count" in result
        assert isinstance(result["results"], list)
        assert isinstance(result["count"], int)
        assert result["count"] > 0


class TestReadCapabilityHandler:
    """Test the read capability handler."""
    
    def test_handler_creation(self):
        """Test that the read handler can be created."""
        handler = ReadCapabilityHandler()
        assert handler.capability == "messages.read"
        assert handler.verb == "messages"
        assert handler.noun == "read"
        assert "read-only" in handler.safety_annotations
    
    @pytest.mark.asyncio
    async def test_execute_read(self):
        """Test that the read capability executes correctly."""
        handler = ReadCapabilityHandler()
        parameters = {"id": "test_message_123"}
        
        result = await handler.execute(parameters)
        
        assert result["id"] == "test_message_123"
        assert "headers" in result
        assert "body_text" in result
        assert "body_html" in result
    
    @pytest.mark.asyncio
    async def test_execute_read_missing_id(self):
        """Test that the read capability requires message ID."""
        handler = ReadCapabilityHandler()
        parameters = {}
        
        with pytest.raises(ValueError, match="Message ID is required"):
            await handler.execute(parameters)


class TestProposeReplyCapabilityHandler:
    """Test the propose reply capability handler."""
    
    def test_handler_creation(self):
        """Test that the propose reply handler can be created."""
        handler = ProposeReplyCapabilityHandler()
        assert handler.capability == "messages.propose_reply"
        assert handler.verb == "messages"
        assert handler.noun == "propose_reply"
        assert "read-only" in handler.safety_annotations
    
    @pytest.mark.asyncio
    async def test_execute_propose_reply(self):
        """Test that the propose reply capability executes correctly."""
        handler = ProposeReplyCapabilityHandler()
        parameters = {"id": "test_message_123", "context": "project discussion"}
        
        result = await handler.execute(parameters)
        
        assert "suggestions" in result
        assert isinstance(result["suggestions"], list)
        assert len(result["suggestions"]) > 0
        assert all(isinstance(s, str) for s in result["suggestions"])
    
    @pytest.mark.asyncio
    async def test_execute_propose_reply_missing_id(self):
        """Test that the propose reply capability requires message ID."""
        handler = ProposeReplyCapabilityHandler()
        parameters = {"context": "project discussion"}
        
        with pytest.raises(ValueError, match="Message ID is required"):
            await handler.execute(parameters)


class TestMailBridgeTool:
    """Test the mail bridge tool."""
    
    def test_tool_creation(self):
        """Test that the mail bridge tool can be created."""
        tool = MailBridgeTool()
        assert tool.name == "mail_bridge"
        assert tool.category == "mail"
        assert "operation" in tool.input_schema["properties"]
    
    def test_tool_execution_list(self):
        """Test that the tool can execute list operation."""
        tool = MailBridgeTool()
        parameters = {"operation": "list", "mailbox": "Inbox", "limit": 10}
        
        # Mock the HTTP client to avoid actual network calls
        with patch('httpx.Client') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "messages": [
                    {"id": "msg1", "subject": "Test", "from": "test@example.com"}
                ],
                "total": 1
            }
            mock_response.raise_for_status.return_value = None
            
            mock_client_instance = Mock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__enter__.return_value = mock_client_instance
            
            result = tool.execute(parameters)
            
            assert result["operation"] == "list"
            assert result["mailbox"] == "Inbox"
            assert "results" in result
            assert "count" in result
    
    def test_tool_execution_read(self):
        """Test that the tool can execute read operation."""
        tool = MailBridgeTool()
        parameters = {"operation": "read", "message_id": "msg123"}
        
        # Mock the HTTP client
        with patch('httpx.Client') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "id": "msg123",
                "subject": "Test Message",
                "body": "Test content"
            }
            mock_response.raise_for_status.return_value = None
            
            mock_client_instance = Mock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__enter__.return_value = mock_client_instance
            
            result = tool.execute(parameters)
            
            assert result["operation"] == "read"
            assert result["message_id"] == "msg123"
            assert "message" in result
    
    def test_tool_execution_unknown_operation(self):
        """Test that the tool rejects unknown operations."""
        tool = MailBridgeTool()
        parameters = {"operation": "unknown"}
        
        with pytest.raises(ValueError, match="Unknown operation: unknown"):
            tool.execute(parameters)


class TestIntegration:
    """Integration tests for the Mail Agent."""
    
    @pytest.mark.asyncio
    async def test_agent_startup(self):
        """Test that the agent can start up correctly."""
        agent = MailAgent()
        await agent.start()
        
        # Verify agent is in healthy state
        health_status = agent.get_health_status()
        assert health_status["status"] == "healthy"
        assert "started successfully" in health_status["message"]
        
        await agent.stop()
    
    def test_agent_manifest_registry_compliance(self):
        """Test that the agent manifest complies with registry schema."""
        agent = MailAgent()
        manifest = agent.generate_manifest()
        
        # Verify all required fields from registry schema
        required_fields = [
            "agent_id", "version", "display_name", "description",
            "capabilities", "data_scopes", "tool_access", "egress_domains", "health_check"
        ]
        
        for field in required_fields:
            assert field in manifest, f"Missing required field: {field}"
        
        # Verify capability structure
        for capability in manifest["capabilities"]:
            required_capability_fields = [
                "verb", "input_schema", "output_schema", "safety_annotations", "description"
            ]
            for field in required_capability_fields:
                assert field in capability, f"Missing capability field: {field}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
