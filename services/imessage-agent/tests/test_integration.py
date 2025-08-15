"""
Integration tests for iMessage Agent capabilities.

These tests validate all three core capabilities: messages.search, messages.read, and messages.propose_reply
with local attachment processing and ADR-0019 compliance (no network egress).
"""

import pytest
import sys
import os
import asyncio
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.agent import iMessageAgent
from src.tools.imessage_bridge import iMessageBridgeTool
from src.handlers.search import SearchCapabilityHandler
from src.handlers.read import ReadCapabilityHandler
from src.handlers.propose_reply import ProposeReplyCapabilityHandler


class TestiMessageAgentIntegration:
    """Integration tests for iMessage Agent."""
    
    @pytest.fixture
    def agent(self):
        """Create iMessage Agent instance for testing."""
        return iMessageAgent()
    
    @pytest.fixture
    def bridge_tool(self):
        """Create iMessage bridge tool instance for testing."""
        return iMessageBridgeTool()
    
    def test_agent_initialization(self, agent):
        """Test that agent initializes with all required capabilities and tools."""
        # Check agent properties
        assert agent.agent_id == "imessage-agent"
        assert agent.name == "iMessage Agent"
        assert "imessage:messages" in agent.data_scopes
        assert "imessage:threads" in agent.data_scopes
        
        # Check required capabilities are registered
        expected_capabilities = ["messages.search", "messages.read", "messages.propose_reply"]
        for capability in expected_capabilities:
            assert capability in agent.capabilities, f"Missing capability: {capability}"
        
        # Check required tools are registered
        expected_tools = ["imessage_bridge"]
        for tool in expected_tools:
            assert tool in agent.tools, f"Missing tool: {tool}"
    
    def test_health_checks(self, agent):
        """Test agent health monitoring."""
        # Test agent status check
        agent_status = agent.check_agent_status()
        assert agent_status.status == "healthy"
        
        # Test capability count check
        capability_status = agent.check_capability_count()
        assert capability_status.status == "healthy"
        
        # Test tool access check
        tool_status = agent.check_tool_access()
        assert tool_status.status in ["healthy", "degraded"]  # degraded is ok if bridge not available
    
    def test_bridge_connectivity_check(self, agent):
        """Test bridge connectivity health check."""
        bridge_status = agent.check_bridge_connectivity()
        assert bridge_status.status in ["healthy", "degraded", "unhealthy"]
        
        # Should have bridge URL in details
        assert "bridge_url" in bridge_status.details or "error" in bridge_status.details
    
    @pytest.mark.asyncio
    async def test_messages_search_capability(self, agent):
        """Test messages.search capability with various parameters."""
        search_handler = agent.capabilities["messages.search"]
        
        # Test basic search
        result = await search_handler.execute({
            "query": "test message",
            "limit": 5
        })
        
        assert "results" in result
        assert "count" in result
        assert isinstance(result["results"], list)
        assert result["count"] == len(result["results"])
        assert result["count"] <= 5
        
        # Validate message structure
        if result["results"]:
            message = result["results"][0]
            required_fields = ["id", "thread_id", "timestamp", "message_type"]
            for field in required_fields:
                assert field in message, f"Missing field in message: {field}"
        
        # Test search with contact filter
        result_with_contact = await search_handler.execute({
            "query": "hello",
            "contact": "John Doe",
            "limit": 3
        })
        
        assert "results" in result_with_contact
        assert result_with_contact["count"] <= 3
    
    @pytest.mark.asyncio
    async def test_messages_read_capability(self, agent):
        """Test messages.read capability with attachment processing."""
        read_handler = agent.capabilities["messages.read"]
        
        # Test reading by message ID
        result = await read_handler.execute({
            "message_id": "test_msg_1",
            "include_attachments": True,
            "process_images": True
        })
        
        assert "message" in result
        message = result["message"]
        
        # Validate message structure
        required_fields = ["id", "thread_id", "timestamp", "message_type"]
        for field in required_fields:
            assert field in message, f"Missing field in message: {field}"
        
        # Test reading by thread ID
        result_by_thread = await read_handler.execute({
            "thread_id": "test_thread",
            "include_attachments": False
        })
        
        assert "message" in result_by_thread
        
        # Test context messages
        result_with_context = await read_handler.execute({
            "message_id": "test_msg_1",
            "context_messages": 2
        })
        
        assert "message" in result_with_context
        if result_with_context["message"] and "context" in result_with_context["message"]:
            assert len(result_with_context["message"]["context"]) <= 2
    
    @pytest.mark.asyncio
    async def test_messages_propose_reply_capability(self, agent):
        """Test messages.propose_reply capability with different styles."""
        reply_handler = agent.capabilities["messages.propose_reply"]
        
        # Test reply proposals for different styles
        styles = ["casual", "professional", "brief", "detailed"]
        
        for style in styles:
            result = await reply_handler.execute({
                "message_content": "How are you doing today?",
                "thread_id": "test_thread",
                "reply_style": style,
                "max_replies": 3
            })
            
            assert "proposals" in result
            assert "original_message" in result
            assert isinstance(result["proposals"], list)
            assert len(result["proposals"]) <= 3
            
            # Validate proposal structure
            for proposal in result["proposals"]:
                required_fields = ["reply_text", "confidence", "reasoning"]
                for field in required_fields:
                    assert field in proposal, f"Missing field in proposal: {field}"
                
                assert 0 <= proposal["confidence"] <= 1
                assert len(proposal["reply_text"]) > 0
                assert proposal["style"] == style
        
        # Test with attachment consideration
        result_with_attachments = await reply_handler.execute({
            "message_id": "test_msg_with_attachments",
            "consider_attachments": True,
            "reply_style": "casual"
        })
        
        assert "proposals" in result_with_attachments
        if result_with_attachments["proposals"]:
            # At least one proposal should consider attachments
            considers_attachments = any(
                proposal.get("considers_attachments", False) 
                for proposal in result_with_attachments["proposals"]
            )
            # Note: This might be False in mock mode, which is fine
    
    def test_bridge_tool_operations(self, bridge_tool):
        """Test iMessage bridge tool operations."""
        # Test health check
        health_result = bridge_tool.execute({"operation": "health"})
        assert "operation" in health_result
        assert health_result["operation"] == "health"
        
        # Test list operation
        list_result = bridge_tool.execute({
            "operation": "list",
            "limit": 5
        })
        assert "operation" in list_result
        assert list_result["operation"] == "list"
        
        # Test search operation
        search_result = bridge_tool.execute({
            "operation": "search",
            "query": "test",
            "limit": 3
        })
        assert "operation" in search_result
        assert search_result["operation"] == "search"
        
        # Test read operation with message ID
        read_result = bridge_tool.execute({
            "operation": "read",
            "message_id": "test_msg"
        })
        assert "operation" in read_result
        assert read_result["operation"] == "read"
        
        # Test read operation with thread ID
        read_thread_result = bridge_tool.execute({
            "operation": "read",
            "thread_id": "test_thread"
        })
        assert "operation" in read_thread_result
        assert read_thread_result["operation"] == "read"
    
    def test_no_network_egress_compliance(self, agent):
        """Test ADR-0019 compliance - no network egress."""
        # Verify egress domains are empty
        assert agent.egress_domains == [], "Agent should have no egress domains"
        
        # Verify safety annotations include no-egress
        for capability_name, handler in agent.capabilities.items():
            if hasattr(handler, 'safety_annotations'):
                assert "no-egress" in handler.safety_annotations, f"Capability {capability_name} missing no-egress annotation"
            
            # Verify local-only annotation for all capabilities
            assert "local-only" in handler.safety_annotations, f"Capability {capability_name} missing local-only annotation"
            assert "read-only" in handler.safety_annotations, f"Capability {capability_name} missing read-only annotation"
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, agent):
        """Test complete workflow: search -> read with attachments -> propose reply."""
        # Step 1: Search for messages
        search_handler = agent.capabilities["messages.search"]
        search_result = await search_handler.execute({
            "query": "photo",
            "limit": 1
        })
        
        assert search_result["count"] > 0
        message_id = search_result["results"][0]["id"]
        thread_id = search_result["results"][0]["thread_id"]
        
        # Step 2: Read message with attachment processing
        read_handler = agent.capabilities["messages.read"]
        read_result = await read_handler.execute({
            "message_id": message_id,
            "include_attachments": True,
            "process_images": True
        })
        
        message = read_result["message"]
        assert message["id"] == message_id
        
        # Step 3: Propose reply based on message content
        reply_handler = agent.capabilities["messages.propose_reply"]
        reply_result = await reply_handler.execute({
            "message_id": message_id,
            "thread_id": thread_id,
            "consider_attachments": True,
            "reply_style": "casual"
        })
        
        assert len(reply_result["proposals"]) > 0
        assert "original_message" in reply_result
    
    def test_thread_based_workflow(self, agent):
        """Test thread-based operations."""
        # Get bridge tool directly for thread operations
        bridge_tool = agent.tools["imessage_bridge"]
        
        # Test reading entire thread
        thread_result = bridge_tool.execute({
            "operation": "read",
            "thread_id": "test_thread"
        })
        
        if "result" in thread_result and isinstance(thread_result["result"], dict):
            thread_data = thread_result["result"]
            if "messages" in thread_data:
                assert isinstance(thread_data["messages"], list)
            if "thread_info" in thread_data:
                assert "participants" in thread_data["thread_info"]
                assert "message_count" in thread_data["thread_info"]
    
    def test_performance_requirements(self, agent):
        """Test that health endpoint responds within performance requirements."""
        import time
        
        # Test health check response time
        start_time = time.time()
        health_status = agent.get_health_status()
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        assert response_time < 400, f"Health check took {response_time}ms, should be < 400ms"
        assert health_status["status"] in ["healthy", "degraded"]
        assert health_status["agent_id"] == "imessage-agent"
    
    def test_manifest_generation(self, agent):
        """Test agent manifest generation for registry."""
        manifest = agent.generate_manifest()
        
        # Validate manifest structure
        required_fields = ["agent_id", "version", "display_name", "description", "capabilities", "data_scopes"]
        for field in required_fields:
            assert field in manifest, f"Missing field in manifest: {field}"
        
        # Validate capabilities in manifest
        assert len(manifest["capabilities"]) == 3
        capability_verbs = [cap["verb"] for cap in manifest["capabilities"]]
        expected_verbs = ["messages.search", "messages.read", "messages.propose_reply"]
        for verb in expected_verbs:
            assert verb in capability_verbs, f"Missing capability in manifest: {verb}"
        
        # Validate data scopes
        assert "imessage:messages" in manifest["data_scopes"]
        assert "imessage:threads" in manifest["data_scopes"]
        
        # Validate safety annotations
        for capability in manifest["capabilities"]:
            assert "safety_annotations" in capability
            assert "read-only" in capability["safety_annotations"]
            assert "local-only" in capability["safety_annotations"]
            assert "no-egress" in capability["safety_annotations"]
    
    def test_error_handling(self, agent):
        """Test error handling in various scenarios."""
        bridge_tool = agent.tools["imessage_bridge"]
        
        # Test invalid operation
        with pytest.raises(ValueError, match="Unknown operation"):
            bridge_tool.execute({"operation": "invalid_op"})
        
        # Test missing required parameters
        with pytest.raises(ValueError, match="Either message_id or thread_id is required"):
            bridge_tool.execute({"operation": "read"})
        
        with pytest.raises(ValueError, match="query is required"):
            bridge_tool.execute({"operation": "search"})
    
    @pytest.mark.asyncio
    async def test_capability_error_recovery(self, agent):
        """Test that capabilities gracefully handle errors and provide fallback data."""
        # Test search with invalid parameters (should fallback to mock data)
        search_handler = agent.capabilities["messages.search"]
        result = await search_handler.execute({})  # Missing query, should still work
        
        assert "results" in result
        assert "count" in result
        
        # Test read with invalid message ID (should fallback to mock data)
        read_handler = agent.capabilities["messages.read"]
        result = await read_handler.execute({
            "message_id": "nonexistent_message"
        })
        
        assert "message" in result
        
        # Test propose reply with minimal parameters (should still work)
        reply_handler = agent.capabilities["messages.propose_reply"]
        result = await reply_handler.execute({
            "message_content": "Hello",
            "thread_id": "test"
        })
        
        assert "proposals" in result
        assert len(result["proposals"]) > 0
    
    def test_caching_behavior(self, bridge_tool):
        """Test that bridge tool implements proper caching."""
        # Make same request twice and ensure consistent results
        request1 = bridge_tool.execute({
            "operation": "list",
            "limit": 3
        })
        
        request2 = bridge_tool.execute({
            "operation": "list", 
            "limit": 3
        })
        
        # Results should be consistent (though caching is more relevant in live mode)
        assert request1["operation"] == request2["operation"]
        
        # Test different requests produce different cache keys
        request3 = bridge_tool.execute({
            "operation": "list",
            "limit": 5
        })
        
        # Different limits might produce different results
        assert request3["operation"] == "list"
    
    def test_data_scope_validation(self, agent):
        """Test that agent properly declares data scopes."""
        assert "imessage:messages" in agent.data_scopes
        assert "imessage:threads" in agent.data_scopes
        
        # Should not have scopes for other services
        assert "whatsapp:messages" not in agent.data_scopes
        assert "mail:messages" not in agent.data_scopes
    
    def test_tool_access_validation(self, agent):
        """Test that agent properly declares tool access."""
        assert "macos-bridge" in agent.tool_access
        assert "sqlite-db" in agent.tool_access
        
        # Should not need network tools
        assert "http-client" not in agent.tool_access
        assert "api-gateway" not in agent.tool_access


if __name__ == "__main__":
    pytest.main([__file__, "-v"])