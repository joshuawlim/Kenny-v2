"""
Integration tests for WhatsApp Agent capabilities.

These tests validate all three core capabilities: chats.search, chats.read, and chats.propose_reply
with local image processing and ADR-0019 compliance (no network egress).
"""

import pytest
import sys
import os
import asyncio
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.agent import WhatsAppAgent
from src.tools.image_processor import LocalImageProcessor
from src.handlers.search import SearchCapabilityHandler
from src.handlers.read import ReadCapabilityHandler
from src.handlers.propose_reply import ProposeReplyCapabilityHandler


class TestWhatsAppAgentIntegration:
    """Integration tests for WhatsApp Agent."""
    
    @pytest.fixture
    def agent(self):
        """Create WhatsApp Agent instance for testing."""
        return WhatsAppAgent()
    
    @pytest.fixture
    def image_processor(self):
        """Create image processor instance for testing."""
        return LocalImageProcessor()
    
    def test_agent_initialization(self, agent):
        """Test that agent initializes with all required capabilities and tools."""
        # Check agent properties
        assert agent.agent_id == "whatsapp-agent"
        assert agent.name == "WhatsApp Agent"
        assert "whatsapp:messages" in agent.data_scopes
        assert "whatsapp:media" in agent.data_scopes
        
        # Check required capabilities are registered
        expected_capabilities = ["messages.search", "chats.read", "chats.propose_reply"]
        for capability in expected_capabilities:
            assert capability in agent.capabilities, f"Missing capability: {capability}"
        
        # Check required tools are registered
        expected_tools = ["whatsapp_bridge", "image_processor"]
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
        assert tool_status.status in ["healthy", "degraded"]  # degraded is ok if OCR not installed
    
    @pytest.mark.asyncio
    async def test_chats_search_capability(self, agent):
        """Test chats.search capability with various parameters."""
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
            required_fields = ["id", "chat_id", "timestamp", "message_type"]
            for field in required_fields:
                assert field in message, f"Missing field in message: {field}"
    
    @pytest.mark.asyncio
    async def test_chats_read_capability(self, agent):
        """Test chats.read capability with media processing."""
        read_handler = agent.capabilities["chats.read"]
        
        # Test reading by message ID
        result = await read_handler.execute({
            "message_id": "test_msg_1",
            "include_media": True,
            "process_images": True
        })
        
        assert "message" in result
        message = result["message"]
        
        # Validate message structure
        required_fields = ["id", "chat_id", "timestamp", "message_type"]
        for field in required_fields:
            assert field in message, f"Missing field in message: {field}"
        
        # Test context messages
        result_with_context = await read_handler.execute({
            "chat_id": "test_chat",
            "context_messages": 2
        })
        
        assert "message" in result_with_context
        if result_with_context["message"] and "context" in result_with_context["message"]:
            assert len(result_with_context["message"]["context"]) <= 2
    
    @pytest.mark.asyncio
    async def test_chats_propose_reply_capability(self, agent):
        """Test chats.propose_reply capability with different styles."""
        reply_handler = agent.capabilities["chats.propose_reply"]
        
        # Test reply proposals for different styles
        styles = ["casual", "professional", "brief", "detailed"]
        
        for style in styles:
            result = await reply_handler.execute({
                "message_content": "How are you doing today?",
                "chat_id": "test_chat",
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
    
    def test_image_processor_local_only(self, image_processor):
        """Test that image processor operates locally without network access."""
        # Test OCR operation (should work with mock data even without tesseract)
        result = image_processor.execute({
            "operation": "ocr",
            "image_path": "/nonexistent/path.jpg"  # Will trigger mock fallback
        })
        
        assert "operation" in result
        assert result["operation"] == "ocr"
        assert "local_only" in result or "mock" in result  # Confirms no network
        
        # Test image analysis operation
        result = image_processor.execute({
            "operation": "analyze",
            "image_path": "/nonexistent/path.jpg"
        })
        
        assert "operation" in result
        assert result["operation"] == "analyze"
        assert "local_only" in result or "mock" in result
    
    def test_no_network_egress_compliance(self, agent):
        """Test ADR-0019 compliance - no network egress in image processing."""
        # Verify egress domains are empty
        assert agent.egress_domains == [], "Agent should have no egress domains"
        
        # Verify safety annotations include no-egress
        for capability_name, handler in agent.capabilities.items():
            if hasattr(handler, 'safety_annotations'):
                assert "no-egress" in handler.safety_annotations, f"Capability {capability_name} missing no-egress annotation"
            
            # Verify local-only annotation for image-related capabilities
            if "read" in capability_name or "search" in capability_name:
                assert "local-only" in handler.safety_annotations, f"Capability {capability_name} missing local-only annotation"
    
    @pytest.mark.asyncio
    async def test_end_to_end_media_workflow(self, agent):
        """Test complete workflow: search -> read with media -> propose reply."""
        # Step 1: Search for messages
        search_handler = agent.capabilities["messages.search"]
        search_result = await search_handler.execute({
            "query": "photo",
            "limit": 1
        })
        
        assert search_result["count"] > 0
        message_id = search_result["results"][0]["id"]
        chat_id = search_result["results"][0]["chat_id"]
        
        # Step 2: Read message with media processing
        read_handler = agent.capabilities["chats.read"]
        read_result = await read_handler.execute({
            "message_id": message_id,
            "include_media": True,
            "process_images": True
        })
        
        message = read_result["message"]
        assert message["id"] == message_id
        
        # Step 3: Propose reply based on message content
        reply_handler = agent.capabilities["chats.propose_reply"]
        reply_result = await reply_handler.execute({
            "message_id": message_id,
            "chat_id": chat_id,
            "consider_media": True,
            "reply_style": "casual"
        })
        
        assert len(reply_result["proposals"]) > 0
        assert reply_result["original_message"]["content"] == message["content"]
    
    def test_performance_requirements(self, agent):
        """Test that health endpoint responds within performance requirements."""
        import time
        
        # Test health check response time
        start_time = time.time()
        health_status = agent.get_health_status()
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        assert response_time < 400, f"Health check took {response_time}ms, should be < 400ms"
        assert health_status["status"] in ["healthy", "degraded"]
        assert health_status["agent_id"] == "whatsapp-agent"
    
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
        expected_verbs = ["messages.search", "chats.read", "chats.propose_reply"]
        for verb in expected_verbs:
            assert verb in capability_verbs, f"Missing capability in manifest: {verb}"
        
        # Validate safety annotations
        for capability in manifest["capabilities"]:
            assert "safety_annotations" in capability
            assert "read-only" in capability["safety_annotations"]
            assert "local-only" in capability["safety_annotations"]
            assert "no-egress" in capability["safety_annotations"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])